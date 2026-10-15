"""Runs the baseline and TraceFix on the same incident."""
from __future__ import annotations

from typing import Any

from .baseline import rank
from .decision_engine import decide
from .topology import analyse

# Scripted scenario answers for the demo scoreboard (None = no known fix applies).
EXPECTED: dict[str, str | None] = {
    "INC-209": "fix-network",
    "INC-250": "fix-pool",
    "INC-301": None,
    "INC-320": None,
}


def investigate(store: Any, incident_id: str) -> dict[str, Any]:
    incident = store.get_incident(incident_id)
    rows = store.evaluate_candidates(incident_id)
    try:
        topology = analyse(store, incident_id)
    except Exception as exc:  # topology is additive; never block the core verdict
        topology = {"suspects": [], "trigger": None, "errors": [str(exc)]}
    decision = decide(incident_id, rows, topology)
    baseline = rank(incident, [r for r in store.get_resolved_incidents() if r["incident_id"] != incident_id])
    return {"incident": incident, "decision": decision, "baseline": baseline, "topology": topology}


def run_scoreboard(store: Any) -> list[dict[str, Any]]:
    out = []
    for inc in store.list_open_incidents():
        res = investigate(store, inc["id"])
        expected = EXPECTED.get(inc["id"])
        b_fix = res["baseline"][0]["fix_id"] if res["baseline"] else None
        t_fix = res["decision"]["recommended_fix_id"]
        out.append({
            "incident": inc["id"],
            "expected": expected or "no fix applies",
            "baseline": b_fix or "none",
            "baseline_ok": b_fix == expected,
            "tracefix": t_fix or res["decision"]["verdict"].lower(),
            "tracefix_ok": t_fix == expected,
        })
    return out