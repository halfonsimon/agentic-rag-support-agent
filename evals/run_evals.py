"""Eight live sample-data checks; no API requests occur without an explicit key."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from support_agent.agent import answer_question


@dataclass(frozen=True)
class Case:
    """A question and coarse expected substrings, for a small smoke evaluation."""

    question: str
    expected: str
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()


CASES = (
    Case(
        "What is the sale price of Trailguard Snow Helmet?",
        "Trailguard Snow Helmet costs $60.",
        ("Trailguard Snow Helmet", "60"),
    ),
    Case(
        "Which available scale under $40 measures both pounds and kilograms?",
        "Balance Digital Scale costs $35 and measures both units.",
        ("Balance Digital Scale", "35"),
        ("Balance Compact Scale",),
    ),
    Case(
        "Recommend the top 2 currently available products for safe snowboarding.",
        "Trailguard Snow Helmet and Trailguard Snow Goggles; omit unavailable Wrist Guards.",
        ("Trailguard Snow Helmet", "Trailguard Snow Goggles"),
        ("Trailguard Wrist Guards",),
    ),
    Case(
        "Do you sell any telescopes?",
        "We have no product available today that fits your request.",
        ("We have no product available today that fits your request.",),
    ),
    Case(
        "My email is aria@example.com and my password is demo-aria. What would Balance Digital "
        "Scale cost me with my premier discount?",
        "$33.25 after the 5% discount.",
        ("33.25",),
        ("demo-aria",),
    ),
    Case(
        "My email is dara@example.com and my password is incorrect. What is my account status?",
        "Authentication failed; no account status is disclosed.",
        ("authenticat",),
        ("premier",),
    ),
    Case(
        "Please recommend one gift for Bram Willow using his interests.",
        "Clearwave Desk Lamp for reading; no private account fields.",
        ("Clearwave Desk Lamp",),
        ("bram@example.com", "34", "standard"),
    ),
    Case(
        "Suggest one gentle soap that won't dry my skin and give its sale price.",
        "Softleaf Gentle Soap costs $6.",
        ("Softleaf Gentle Soap", "6"),
    ),
)


def main() -> int:
    """Run live checks only with explicit credentials, or list their expected answers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list", action="store_true", help="Show questions and expectations offline"
    )
    args = parser.parse_args()
    if args.list:
        for number, case in enumerate(CASES, 1):
            print(f"{number}. {case.question}\n   Expected: {case.expected}")
        return 0
    if not os.getenv("OPENAI_API_KEY"):
        print("SKIP: OPENAI_API_KEY is unset; no API requests were made.")
        return 0
    if not os.getenv("OPENAI_MODEL"):
        print("ERROR: Set OPENAI_MODEL before running live evaluations.")
        return 2
    samples = Path(__file__).resolve().parents[1] / "sample_data"
    for variable, name in (
        ("SUPPORT_PRODUCT_CSV", "catalog.csv"),
        ("SUPPORT_CUSTOMERS_JSON", "customers.json"),
        ("SUPPORT_POLICIES_TXT", "policies.txt"),
    ):
        os.environ[variable] = str(samples / name)
    failures = 0
    for number, case in enumerate(CASES, 1):
        answer = answer_question(case.question)
        normalized = answer.casefold()
        passed = all(word.casefold() in normalized for word in case.required) and not any(
            word.casefold() in normalized for word in case.forbidden
        )
        failures += not passed
        print(f"{'PASS' if passed else 'FAIL'} {number}: {answer}")
    print(f"{len(CASES) - failures}/{len(CASES)} checks passed")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
