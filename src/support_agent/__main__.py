"""Command-line entry point for a single independent support question."""

from __future__ import annotations

import argparse

from .agent import answer_question


def main() -> None:
    """Read one question and print the agent's answer."""
    parser = argparse.ArgumentParser(description="Ask the support agent a question")
    parser.add_argument("question")
    args = parser.parse_args()
    try:
        print(answer_question(args.question))
    except ValueError as exc:
        parser.exit(2, f"Configuration error: {exc}\n")


if __name__ == "__main__":
    main()
