"""Keep all unit tests on fictional data and away from environment credentials."""

from pathlib import Path

import pytest

from support_agent import data
from support_agent.tools import products


@pytest.fixture(autouse=True)
def isolated_sample_data(monkeypatch):
    root = Path(__file__).resolve().parents[1] / "sample_data"
    for name, file in (
        ("SUPPORT_PRODUCT_CSV", "catalog.csv"),
        ("SUPPORT_CUSTOMERS_JSON", "customers.json"),
        ("SUPPORT_POLICIES_TXT", "policies.txt"),
    ):
        monkeypatch.setenv(name, str(root / file))
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "AZURE_OPENAI_ENDPOINT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(data, "_products_df", None)
    monkeypatch.setattr(data, "_cust_collection", None)
    monkeypatch.setattr(data, "_policies_text", None)
    monkeypatch.setattr(products, "_chroma_collection", None)
