"""Configuration reads environment variables; credentials have no defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"
SAMPLE_DATA = _REPO_SAMPLES if _REPO_SAMPLES.is_dir() else Path(__file__).parent / "sample_data"


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded on demand, so importing needs no credentials."""

    api_key: str
    model: str
    endpoint: str | None
    product_csv: Path
    customers_json: Path
    policies_txt: Path
    embed_model: str

    @classmethod
    def from_env(cls) -> Settings:
        """Read configuration, defaulting only local data and the embedding model."""
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", ""),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or None,
            product_csv=Path(os.getenv("SUPPORT_PRODUCT_CSV") or SAMPLE_DATA / "catalog.csv"),
            customers_json=Path(
                os.getenv("SUPPORT_CUSTOMERS_JSON") or SAMPLE_DATA / "customers.json"
            ),
            policies_txt=Path(os.getenv("SUPPORT_POLICIES_TXT") or SAMPLE_DATA / "policies.txt"),
            embed_model=os.getenv("SUPPORT_EMBED_MODEL") or "all-MiniLM-L6-v2",
        )

    def create_client(self) -> Any:
        """Create a client only with an explicitly supplied key and model."""
        if not self.api_key or not self.model:
            raise ValueError("Set OPENAI_API_KEY and OPENAI_MODEL before calling the model")
        from openai import OpenAI

        kwargs: dict[str, Any] = {"api_key": self.api_key, "max_retries": 0, "timeout": 30.0}
        if self.endpoint:
            kwargs["base_url"] = self.endpoint
        return OpenAI(**kwargs)
