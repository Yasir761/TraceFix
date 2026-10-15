"""Similarity baseline: what a text-retrieval agent would do with the same data.

Pure-Python TF-IDF cosine over alert/title/service text, so it needs no
dependencies. Swap in real embeddings for a stronger baseline.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_TOKEN = re.compile(r"[a-z0-9]+")


def _text(item: dict[str, Any]) -> str:
    return f"{item.get('title', '')} {item.get('description', '')} {item.get('service', '')}"


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def rank(incident: dict[str, Any], resolved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs = [Counter(_tokens(_text(r))) for r in resolved]
    query = Counter(_tokens(_text(incident)))
    df: Counter[str] = Counter()
    for d in [*docs, query]:
        df.update(d.keys())
    n = len(docs) + 1

    def vec(c: Counter[str]) -> dict[str, float]:
        return {t: n_t * (math.log((1 + n) / (1 + df[t])) + 1) for t, n_t in c.items()}

    def cos(a: dict[str, float], b: dict[str, float]) -> float:
        dot = sum(a[t] * b[t] for t in a.keys() & b.keys())
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    q = vec(query)
    ranked = [
        {"incident_id": r["incident_id"], "title": r["title"], "fix_id": r["fix_id"],
         "fix_name": r["fix_name"], "score": cos(q, vec(d))}
        for r, d in zip(resolved, docs)
    ]
    return sorted(ranked, key=lambda x: x["score"], reverse=True)