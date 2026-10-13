"""Fictional customer lookup and credential verification with explicit field allowlists."""

from __future__ import annotations

import json
import re

from ..data import _get_cust_collection


def _strip_private(record: dict) -> dict:
    """Filter out the password and other stuff we don't want to show."""
    return {
        "first_name": record.get("first_name"),
        "last_name": record.get("last_name"),
        "age": record.get("age"),
        "email": record.get("email"),
        "status": record.get("status"),
        "product-interests": record.get("product-interests", []),
    }


def get_customer(email: str | None = None, name: str | None = None) -> str:
    """Look up gift interests while omitting private account fields."""
    collection = _get_cust_collection()
    records = []
    if email:
        rec = collection.find_one(
            {"email": {"$regex": f"^{re.escape(str(email))}$", "$options": "i"}}
        )
        if rec:
            records.append(rec)
    elif name:
        parts = str(name).split()
        if len(parts) >= 2:
            query = {
                "first_name": {"$regex": f"^{re.escape(parts[0])}$", "$options": "i"},
                "last_name": {"$regex": f"^{re.escape(parts[-1])}$", "$options": "i"},
            }
        else:
            query = {
                "$or": [
                    {"first_name": {"$regex": f"^{re.escape(str(name))}$", "$options": "i"}},
                    {"last_name": {"$regex": f"^{re.escape(str(name))}$", "$options": "i"}},
                ]
            }
        records = list(collection.find(query))
    else:
        return json.dumps({"error": "provide an email or a name to look up"})
    matches = [
        {
            "first_name": r.get("first_name"),
            "last_name": r.get("last_name"),
            "product-interests": r.get("product-interests", []),
        }
        for r in records
    ]
    return json.dumps({"count": len(matches), "matches": matches})


def authenticate(email: str, pw: str) -> str:
    """Check login info. If correct, returns their account details (no password)."""
    collection = _get_cust_collection()
    rec = collection.find_one({"email": {"$regex": f"^{re.escape(str(email))}$", "$options": "i"}})
    if rec is not None and str(rec.get("pw")) == str(pw):
        safe = _strip_private(rec)
        safe["authenticated"] = True
        return json.dumps(safe)
    return json.dumps({"authenticated": False})
