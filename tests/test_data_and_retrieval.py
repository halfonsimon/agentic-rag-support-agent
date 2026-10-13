"""Lazy loading and retrieval contracts without downloading an embedding model."""

import json
from pathlib import Path

from support_agent import data
from support_agent.config import Settings
from support_agent.tools import products


def test_missing_policy_file_uses_sample_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPPORT_POLICIES_TXT", str(tmp_path / "missing.txt"))
    assert "Fictional store" in data._get_policies_text()


def test_settings_have_no_credential_defaults():
    settings = Settings.from_env()
    assert settings.api_key == "" and settings.model == "" and settings.endpoint is None


def test_search_is_lazy_and_reuses_index(monkeypatch):
    builds = []

    class Collection:
        def add(self, **kwargs):
            self.rows = kwargs

        def count(self):
            return 10

        def query(self, **kwargs):
            assert kwargs["n_results"] <= 10
            return {
                "ids": [[self.rows["ids"][0]]],
                "metadatas": [[self.rows["metadatas"][0]]],
                "distances": [[0.125]],
            }

    collection = Collection()

    class Chroma:
        def get_or_create_collection(self, **kwargs):
            builds.append(kwargs)
            return collection

    monkeypatch.setattr(products, "_new_chroma_client", lambda: Chroma())
    monkeypatch.setattr(products, "_embedding_function", lambda: "fake-embeddings")
    assert products._chroma_collection is None and data._products_df is None
    result = json.loads(products.search_products("snowboarding", k=20))
    assert result["results"][0]["product_name"] == "Trailguard Snow Helmet"
    assert result["results"][0]["description"].startswith("Insulated")
    assert result["results"][0]["distance"] == 0.125
    products.search_products("snowboarding")
    assert len(builds) == 1


def test_root_and_packaged_samples_are_identical():
    root = Path(__file__).resolve().parents[1]
    for name in ("catalog.csv", "customers.json", "policies.txt"):
        assert (root / "sample_data" / name).read_bytes() == (
            root / "src/support_agent/sample_data" / name
        ).read_bytes()
