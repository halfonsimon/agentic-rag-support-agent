"""Behavior tests exercise real sample records without embeddings or model APIs."""

import json

import pytest

from support_agent.tools import (
    authenticate,
    calculator,
    filter_products,
    get_customer,
    read_policies,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", 14),
        ("60 * 0.95", 57),
        ("round(35 * .95, 2)", 33.25),
        ("abs(-3) + min(4, 5) + max(6, 7)", 14),
        ("2 ** 3 + 10 // 3 + 10 % 3", 12),
    ],
)
def test_calculator_valid(expression, expected):
    assert json.loads(calculator(expression))["result"] == expected


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo unsafe')",
        "x + 1",
        "(1).__class__",
        "True + 1",
        "[1, 2]",
        "sum([1, 2])",
        "round(1.23, ndigits=1)",
        "1 / 0",
        "2 ** 101",
        "2 ** (2 ** 100)",
        "9" * 1001,
        "+".join(["1"] * 60),
        "1e200 * 1e200",
    ],
)
def test_calculator_rejects(expression):
    assert "error" in json.loads(calculator(expression))


def test_exact_filter_combines_attributes_and_prices():
    result = json.loads(
        filter_products(
            category="sports", brand="TRAILGUARD", available=True, max_price=60, on_sale=True
        )
    )
    assert result["count"] == 2
    assert [p["product_name"] for p in result["results"]] == [
        "Trailguard Snow Helmet",
        "Trailguard Snow Goggles",
    ]
    assert all(p["sale_price"] <= 60 and p["available"] for p in result["results"])


def test_filter_substrings_are_literal_and_limits_preserve_count():
    assert json.loads(filter_products(name_contains=".*"))["count"] == 0
    result = json.loads(filter_products(limit=1))
    assert result["count"] == 10 and result["returned"] == 1


def test_filter_non_discounted_unavailable_and_empty_results():
    assert json.loads(filter_products(available=False))["results"][0]["product_name"] == (
        "Trailguard Wrist Guards"
    )
    result = json.loads(filter_products(on_sale=False))
    assert {p["product_name"] for p in result["results"]} == {
        "Balance Compact Scale",
        "Clearwave Desk Lamp",
    }
    assert json.loads(filter_products(max_price=1))["count"] == 0


def test_authenticate_never_returns_credentials_or_extra_fields():
    good = json.loads(authenticate("ARIA@EXAMPLE.COM", "demo-aria"))
    assert good["authenticated"] is True and good["status"] == "premier"
    assert set(good) == {
        "first_name",
        "last_name",
        "age",
        "email",
        "status",
        "product-interests",
        "authenticated",
    }
    serialized = json.dumps(good)
    assert "demo-aria" not in serialized and "pw" not in good
    assert "internal_note" not in good and "year_to_date_spend" not in good
    assert json.loads(authenticate("aria@example.com", "incorrect")) == {"authenticated": False}
    assert json.loads(authenticate("missing@example.com", "incorrect")) == {"authenticated": False}


@pytest.mark.parametrize("lookup", [{"name": "Aria Meadow"}, {"email": "aria@example.com"}])
def test_customer_lookup_hides_private_fields(lookup):
    result = json.loads(get_customer(**lookup))
    assert result["count"] == 1
    assert result["matches"] == [
        {
            "first_name": "Aria",
            "last_name": "Meadow",
            "product-interests": ["hiking", "snowboarding"],
        }
    ]
    for field in ("email", "age", "status", "pw", "internal_note", "year_to_date_spend"):
        assert field not in result["matches"][0]


def test_lookup_missing_and_regex_input():
    assert "error" in json.loads(get_customer())
    assert json.loads(get_customer(name=".*"))["count"] == 0
    assert json.loads(get_customer(name="Meadow"))["count"] == 1


def test_policies_are_loaded_from_sample_file():
    assert "5%" in json.loads(read_policies())["policies"]
