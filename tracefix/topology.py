"""Topology reasoning: which recent change in the dependency chain explains the incident?

Graph algorithms used (all run inside FalkorDB):
  - Cypher shortestPath()  how the failing service reaches each changed service
  - algo.bfs               the failing service's dependency closure
  - algo.pageRank          which services the whole system leans on most
  - variable-length match  blast radius of the likely trigger
A change is *corroborated* only when the condition it can cause is actually observed
on this incident, so "most recent change" never wins by recency alone.
"""
from __future__ import annotations

from typing import Any

SUPPORT_RANK = {"corroborated": 0, "unknown": 1, "none": 2, "contradicted": 3}
SUPPORT_LABEL = {
    "corroborated": "corroborated by telemetry",
    "unknown": "telemetry missing",
    "none": "no telemetry link",
    "contradicted": "contradicted by telemetry",
}


def analyse(store: Any, incident_id: str, window_hours: int = 24) -> dict[str, Any]:
    errors: list[str] = []
    rows = store.recent_change_rows(incident_id, window_hours * 3600)
    incident = store.get_incident(incident_id)
    service_id = incident["service_id"]

    suspects: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r["change_id"] in suspects:
            continue
        if r["target_id"] == service_id:
            path = {"ids": [service_id], "names": [incident["service"]]}
        else:
            try:
                path = store.shortest_path(service_id, r["target_id"])
            except Exception as exc:
                errors.append(f"shortestPath failed: {exc}")
                path = None
        if not path:
            continue  # changed service is not in this service's dependency chain
        suspects[r["change_id"]] = {
            "change_id": r["change_id"], "summary": r["summary"], "kind": r["kind"],
            "hours_before": round((r["opened_at"] - r["at"]) / 3600, 1),
            "target_id": r["target_id"], "target_name": r["target_name"],
            "hops": len(path["ids"]) - 1, "path_ids": path["ids"], "path_names": path["names"],
            "support": r["support"], "cond_name": r["cond_name"], "metric_id": r["metric_id"],
            "required": r["required"], "observed": r["observed"],
        }

    ranked = sorted(suspects.values(),
                    key=lambda x: (SUPPORT_RANK[x["support"]], x["hops"], x["hours_before"]))
    trigger = next((s for s in ranked if s["support"] == "corroborated"), None)

    def safe(fn, default):
        try:
            return fn()
        except Exception as exc:
            errors.append(f"{getattr(fn, '__name__', 'algorithm')} failed: {exc}")
            return default

    return {
        "service_id": service_id,
        "suspects": ranked,
        "trigger": trigger,
        "closure": safe(lambda: store.dependency_closure(service_id), []),
        "blast_radius": safe(lambda: store.blast_radius(trigger["target_id"]), []) if trigger else [],
        "criticality": safe(lambda: store.criticality(), []),
        "edges": safe(lambda: store.get_service_graph(), []),
        "errors": errors,
    }