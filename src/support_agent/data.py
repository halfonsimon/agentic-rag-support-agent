"""Lazy local catalog, customer and policy loaders."""

from __future__ import annotations

import json
import re
from typing import Any

from .config import Settings

_products_df: Any = None
_cust_collection: Any = None
_policies_text: str | None = None


def _to_float(value: Any) -> float | None:
    """Clean up price strings and convert to float."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        f = float(value)
        return None if f != f else f
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null", "n/a", "na", "-"}:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    m = re.search("-?\\d+(?:\\.\\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _to_bool_available(value: Any) -> bool:
    """Convert availability text to a boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    s = str(value).strip().lower()
    if s in {"false", "no", "0", "unavailable", "out of stock", "n", "f"}:
        return False
    if s in {"true", "yes", "1", "available", "in stock", "instock", "y", "t"}:
        return True
    return True


def _series(df: Any, col: Any) -> Any:
    """Helper to safely grab a text column from pandas."""
    import pandas as pd

    if col in df.columns:
        return df[col].astype(str)
    return pd.Series([""] * len(df), index=df.index)


def _get_products_df() -> Any:
    global _products_df
    if _products_df is None:
        import pandas as pd

        df = pd.read_csv(Settings.from_env().product_csv, dtype=str, keep_default_na=False)
        df["_sale_price"] = _series(df, "Sale Price").map(_to_float)
        df["_list_price"] = _series(df, "List Price").map(_to_float)
        df["_available"] = _series(df, "Available").map(_to_bool_available)
        _products_df = df
    return _products_df


def _get_cust_collection() -> Any:
    global _cust_collection
    if _cust_collection is None:
        import mongomock

        with Settings.from_env().customers_json.open(encoding="utf-8") as f:
            records = json.load(f)
        collection = mongomock.MongoClient()["company"]["cust_data"]
        if records:
            collection.insert_many(records)
        _cust_collection = collection
    return _cust_collection


def _get_policies_text() -> str:
    global _policies_text
    if _policies_text is None:
        try:
            _policies_text = Settings.from_env().policies_txt.read_text(encoding="utf-8").strip()
        except OSError:
            _policies_text = ""
        if not _policies_text:
            _policies_text = (_sample_policies()).strip()
    return _policies_text


def _sample_policies() -> str:
    """Use the bundled demo policy when a configured file is missing or empty."""
    from .config import SAMPLE_DATA

    return (SAMPLE_DATA / "policies.txt").read_text(encoding="utf-8")
