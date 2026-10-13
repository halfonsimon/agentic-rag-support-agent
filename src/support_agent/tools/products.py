"""Semantic retrieval and exact catalog filtering, with a lazy in-memory index."""

from __future__ import annotations

import json
from typing import Any

from ..config import Settings
from ..data import _get_products_df, _series, _to_bool_available, _to_float

_chroma_collection: Any = None


def _new_chroma_client() -> Any:
    import chromadb

    try:
        return chromadb.EphemeralClient()
    except Exception:
        return chromadb.Client()


def _embedding_function() -> Any:
    """Use the specified sentence-transformer for our vector search."""
    from chromadb.utils import embedding_functions

    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=Settings.from_env().embed_model
    )


def _get_chroma_collection() -> Any:
    """Set up the ChromaDB index for RAG."""
    global _chroma_collection
    if _chroma_collection is None:
        df = _get_products_df()
        client = _new_chroma_client()
        try:
            collection = client.get_or_create_collection(
                name="products",
                embedding_function=_embedding_function(),
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            collection = client.get_or_create_collection(
                name="products", embedding_function=_embedding_function()
            )
        names = _series(df, "Product Name")
        descs = _series(df, "Description")
        brands = _series(df, "Brand")
        cats = _series(df, "Category")
        uids = _series(df, "Uniq Id")
        ids, docs, metas = ([], [], [])
        seen: set[str] = set()
        for pos in range(len(df)):
            uid = uids.iloc[pos].strip() or f"row-{pos}"
            if uid in seen:
                uid = f"{uid}-{pos}"
            seen.add(uid)
            name = names.iloc[pos].strip()
            desc = descs.iloc[pos].strip()
            doc = f"{name}. {desc}".strip()
            if not doc:
                doc = name or f"product-{pos}"
            sp = df["_sale_price"].iloc[pos]
            lp = df["_list_price"].iloc[pos]
            metas.append(
                {
                    "uniq_id": uid,
                    "name": name,
                    "brand": brands.iloc[pos].strip(),
                    "category": cats.iloc[pos].strip(),
                    "sale_price": float(sp) if sp is not None else -1.0,
                    "list_price": float(lp) if lp is not None else -1.0,
                    "available": bool(df["_available"].iloc[pos]),
                    "row": int(pos),
                }
            )
            ids.append(uid)
            docs.append(doc)
        batch = 200
        for start in range(0, len(ids), batch):
            collection.add(
                ids=ids[start : start + batch],
                documents=docs[start : start + batch],
                metadatas=metas[start : start + batch],
            )
        _chroma_collection = collection
    return _chroma_collection


def search_products(query: str, k: int = 5) -> str:
    """RAG semantic search over the product vector index. Returns top-k products."""
    try:
        collection = _get_chroma_collection()
    except Exception as exc:
        return json.dumps({"error": f"product index unavailable: {exc}"})
    try:
        k = max(1, min(int(k), 20))
    except (TypeError, ValueError):
        k = 5
    res = collection.query(query_texts=[str(query)], n_results=min(k, collection.count()))
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    df = _get_products_df()
    descs = _series(df, "Description")
    results = []
    for j in range(len(ids)):
        meta = metas[j] or {}
        row = meta.get("row")
        desc = ""
        if isinstance(row, int | float) and 0 <= int(row) < len(df):
            desc = descs.iloc[int(row)].strip()
        sp = meta.get("sale_price")
        lp = meta.get("list_price")
        results.append(
            {
                "product_name": meta.get("name", ""),
                "brand": meta.get("brand", ""),
                "category": meta.get("category", ""),
                "sale_price": None if sp is None or sp < 0 else sp,
                "list_price": None if lp is None or lp < 0 else lp,
                "available": bool(meta.get("available", False)),
                "description": desc[:600],
                "distance": round(float(dists[j]), 4)
                if j < len(dists) and dists[j] is not None
                else None,
            }
        )
    return json.dumps({"query": str(query), "results": results})


def filter_products(
    max_price: float | str | None = None,
    min_price: float | str | None = None,
    brand: str | None = None,
    category: str | None = None,
    available: bool | str | None = None,
    name_contains: str | None = None,
    on_sale: bool | str | None = None,
    limit: int = 10,
) -> str:
    """Exact attribute filter over the catalog (price uses Sale Price)."""
    import pandas as pd

    df = _get_products_df()
    names = _series(df, "Product Name")
    brands = _series(df, "Brand")
    cats = _series(df, "Category")
    descs = _series(df, "Description")
    sale = df["_sale_price"]
    avail = df["_available"]
    mask = pd.Series(True, index=df.index)
    if name_contains:
        mask &= names.str.contains(str(name_contains), case=False, na=False, regex=False)
    if brand:
        mask &= brands.str.contains(str(brand), case=False, na=False, regex=False)
    if category:
        mask &= cats.str.contains(str(category), case=False, na=False, regex=False)
    if max_price is not None:
        v = _to_float(max_price)
        if v is not None:
            mask &= sale.map(lambda x: x is not None and x <= v + 1e-09)
    if min_price is not None:
        v = _to_float(min_price)
        if v is not None:
            mask &= sale.map(lambda x: x is not None and x >= v - 1e-09)
    if available is not None:
        want = available if isinstance(available, bool) else _to_bool_available(available)
        mask &= avail.map(lambda x: bool(x) == bool(want))
    if on_sale is not None:
        want_sale = on_sale if isinstance(on_sale, bool) else _to_bool_available(on_sale)
        lp = df["_list_price"]
        discounted = pd.Series(
            [
                sale_price is not None
                and list_price is not None
                and (sale_price < list_price - 0.001)
                for sale_price, list_price in zip(sale, lp)
            ],
            index=df.index,
        )
        mask &= discounted if want_sale else ~discounted
    try:
        lim = max(1, min(int(limit), 25))
    except (TypeError, ValueError):
        lim = 10
    results = []
    for i in df.index[mask][:lim]:
        spi = sale.loc[i]
        lpi = df["_list_price"].loc[i]
        results.append(
            {
                "product_name": names.loc[i].strip(),
                "brand": brands.loc[i].strip(),
                "category": cats.loc[i].strip(),
                "sale_price": spi if spi is not None else None,
                "list_price": lpi if lpi is not None else None,
                "available": bool(avail.loc[i]),
                "description": descs.loc[i].strip()[:600],
            }
        )
    return json.dumps({"count": int(mask.sum()), "returned": len(results), "results": results})
