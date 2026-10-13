"""A raw tool-calling loop with shared request and tool budgets."""

from __future__ import annotations

import inspect
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .config import Settings
from .prompts import SYSTEM_PROMPT, TOOLS
from .tools import TOOL_IMPLS


@dataclass(frozen=True)
class Limits:
    """Caps include retry requests, rather than only successful model responses."""

    model_calls: int = 15
    tool_calls: int = 15
    content_filter_retries: int = 3
    rate_limit_attempts: int = 4

    def __post_init__(self) -> None:
        if self.model_calls < 1 or self.tool_calls < 0:
            raise ValueError("model_calls must be positive and tool_calls nonnegative")
        if self.content_filter_retries < 0 or self.rate_limit_attempts < 1:
            raise ValueError("retry limits must be nonnegative with at least one attempt")


class _BudgetExhausted(Exception):
    pass


@dataclass
class _RequestBudget:
    remaining: int

    def consume(self) -> None:
        """Count one model attempt, or stop when the shared budget is exhausted."""
        if self.remaining <= 0:
            raise _BudgetExhausted
        self.remaining -= 1


def _is_content_filter(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        getattr(exc, "code", None) == "content_filter"
        or "content_filter" in text
        or "content management policy" in text
        or "responsibleaipolicy" in text.replace(" ", "")
    )


def _is_rate_limit(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) == 429 or "rate limit" in str(exc).lower()


def _create(
    client: Any, messages: list[Any], model: str, limits: Limits, budget: _RequestBudget
) -> Any:
    delay = 2.0
    for attempt in range(limits.rate_limit_attempts):
        budget.consume()
        try:
            return client.chat.completions.create(
                model=model, messages=messages, temperature=0, tools=TOOLS, tool_choice="auto"
            )
        except Exception as exc:
            if (
                _is_rate_limit(exc)
                and attempt < limits.rate_limit_attempts - 1
                and budget.remaining > 0
            ):
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("no model request attempted")


def _dispatch_tool(name: str, args: dict[str, Any], tools: Mapping[str, Callable[..., Any]]) -> str:
    fn = tools.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        accepted = set(inspect.signature(fn).parameters)
        result = fn(**{k: v for k, v in args.items() if k in accepted})
        return result if isinstance(result, str) else json.dumps(result)
    except Exception as exc:
        # Exceptions may contain credentials supplied as arguments; never echo their text.
        return json.dumps({"error": f"tool '{name}' failed: {type(exc).__name__}"})


def answer_question(
    question: str,
    *,
    client: Any = None,
    model: str | None = None,
    limits: Limits | None = None,
    tools: Mapping[str, Callable[..., Any]] | None = None,
) -> str:
    """Answer using six tools; injected clients and tools allow fully offline testing."""
    settings = Settings.from_env()
    if client is None:
        client = settings.create_client()
    model = model or settings.model
    if not model:
        raise ValueError("Set OPENAI_MODEL or supply model explicitly")
    limits = limits or Limits()
    implementations = TOOL_IMPLS if tools is None else tools
    budget = _RequestBudget(limits.model_calls)
    messages: list[Any] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": str(question)},
    ]
    tool_calls_made = 0
    cf_retries = 0
    last_text = ""
    while budget.remaining > 0:
        try:
            completion = _create(client, messages, model, limits, budget)
        except _BudgetExhausted:
            break
        except Exception as exc:
            if _is_content_filter(exc) and cf_retries < limits.content_filter_retries:
                cf_retries += 1
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous step was blocked by an automated content filter. Re-approach "
                            "the question using neutral wording and the available tools, and continue. If "
                            "it cannot be handled safely, give a brief, safe response."
                        ),
                    }
                )
                continue
            return last_text or "I'm sorry, I couldn't complete this request due to a system error."
        message = completion.choices[0].message
        if getattr(message, "content", None):
            last_text = message.content
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            return message.content or last_text or ""
        messages.append(message)
        for call in tool_calls:
            if tool_calls_made >= limits.tool_calls:
                result = json.dumps(
                    {
                        "error": "tool-call budget exhausted; answer using the information already gathered"
                    }
                )
            else:
                tool_calls_made += 1
                try:
                    parsed = json.loads(call.function.arguments or "{}")
                    if not isinstance(parsed, dict):
                        parsed = {}
                except (TypeError, ValueError):
                    parsed = {}
                result = _dispatch_tool(call.function.name, parsed, implementations)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return last_text or "I couldn't complete this request within the step limit."
