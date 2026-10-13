"""Scripted clients verify loop budgets, error recovery and tool-response ordering."""

import json
from types import SimpleNamespace as NS

import pytest

from support_agent.agent import Limits, answer_question


def tool_call(name="calculator", arguments='{"expression":"2+2"}', call_id="call-1"):
    return NS(id=call_id, function=NS(name=name, arguments=arguments))


def response(*calls, text=None):
    return NS(choices=[NS(message=NS(content=text, tool_calls=list(calls)))])


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_stops_at_strict_model_step_limit():
    client = FakeClient([response(tool_call(call_id=f"c{i}")) for i in range(3)])
    result = answer_question(
        "Keep calculating", client=client, model="fake", limits=Limits(model_calls=3)
    )
    assert "step limit" in result
    assert len(client.calls) == 3
    assert all("tools" in call for call in client.calls)  # No extra final request.


def test_tool_limit_does_not_execute_extra_tools():
    invoked = []

    def record(expression):
        invoked.append(expression)
        return json.dumps({"result": 4})

    client = FakeClient(
        [response(tool_call(call_id="a"), tool_call(call_id="b")), response(text="Done")]
    )
    assert (
        answer_question(
            "Compute",
            client=client,
            model="fake",
            limits=Limits(tool_calls=1),
            tools={"calculator": record},
        )
        == "Done"
    )
    assert invoked == ["2+2"]
    replies = [
        m for m in client.calls[1]["messages"] if isinstance(m, dict) and m["role"] == "tool"
    ]
    assert [m["tool_call_id"] for m in replies] == ["a", "b"]
    assert "budget exhausted" in replies[1]["content"]


def test_tool_error_is_returned_to_model_and_loop_recovers():
    def broken():
        raise RuntimeError("sensitive argument should not be echoed")

    client = FakeClient(
        [
            response(tool_call("read_policies", "{}")),
            response(text="The policy tool is unavailable."),
        ]
    )
    result = answer_question(
        "Policies?", client=client, model="fake", tools={"read_policies": broken}
    )
    assert result == "The policy tool is unavailable."
    reply = client.calls[1]["messages"][-1]
    assert reply["role"] == "tool" and reply["tool_call_id"] == "call-1"
    assert "RuntimeError" in json.loads(reply["content"])["error"]
    assert "sensitive argument" not in reply["content"]


@pytest.mark.parametrize(
    "name,args", [("unknown", "{}"), ("calculator", "not json"), ("calculator", "[]")]
)
def test_unknown_tools_and_bad_arguments_are_model_visible_errors(name, args):
    client = FakeClient([response(tool_call(name, args)), response(text="Recovered")])
    assert answer_question("Try", client=client, model="fake") == "Recovered"
    assert "error" in json.loads(client.calls[1]["messages"][-1]["content"])


def test_rate_limit_retries_share_model_budget(monkeypatch):
    sleeps = []
    monkeypatch.setattr("support_agent.agent.time.sleep", sleeps.append)
    exc = RuntimeError("rate limit")
    client = FakeClient([exc, exc, response(text="Recovered")])
    assert (
        answer_question("Try", client=client, model="fake", limits=Limits(model_calls=3))
        == "Recovered"
    )
    assert len(client.calls) == 3 and sleeps == [2.0, 4.0]


def test_rate_limit_does_not_exceed_budget(monkeypatch):
    monkeypatch.setattr("support_agent.agent.time.sleep", lambda _: None)
    client = FakeClient([RuntimeError("rate limit")] * 2)
    answer_question("Try", client=client, model="fake", limits=Limits(model_calls=2))
    assert len(client.calls) == 2


def test_content_filter_retry_is_bounded():
    client = FakeClient([RuntimeError("content_filter")] * 3)
    answer_question(
        "Try", client=client, model="fake", limits=Limits(model_calls=10, content_filter_retries=2)
    )
    assert len(client.calls) == 3
    assert "neutral wording" in client.calls[1]["messages"][-1]["content"]


def test_final_answer_and_empty_tool_map():
    client = FakeClient([response(text="Hello")])
    assert answer_question("Hello", client=client, model="fake", tools={}) == "Hello"


def test_missing_configuration_fails_without_network():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        answer_question("Hello")
