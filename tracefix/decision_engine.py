"""Turns graph validation rows into an explainable verdict.

The graph query decides, per prerequisite, whether it is met, contradicted or
unknown. This module only aggregates those graph answers; it never inspects
incident properties or hardcodes fix ids.
"""
from __future__ import annotations

from typing import Any

SEVERITY = {"met": 0, "unknown": 1, "contradicted": 2}


def group_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cands: dict[str, dict[str, Any]] = {}
    for r in rows:
        c = cands.setdefault(r["fix_id"], {
            "fix_id": r["fix_id"], "fix_name": r["fix_name"], "symptom": r["symptom"],
            "outcome_note": r["outcome_note"], "precedents": [], "conditions": {},
        })
        if r["precedent_id"] not in c["precedents"]:
            c["precedents"].append(r["precedent_id"])
        c["conditions"].setdefault(r["cond_id"], {
            k: r[k] for k in ("cond_id", "cond_name", "required", "metric_id",
                              "metric_name", "obs_id", "observed", "status")
        })
    out = []
    for c in cands.values():
        c["conditions"] = list(c["conditions"].values())
        c["status"] = max((x["status"] for x in c["conditions"]), key=SEVERITY.get)
        out.append(c)
    return sorted(out, key=lambda c: c["fix_id"])


def path_steps(incident_id: str, cand: dict[str, Any]) -> list[str]:
    steps = [
        f"{incident_id} -HAS_SYMPTOM-> {cand['symptom']}",
        f"{cand['symptom']} <-HAS_SYMPTOM- {', '.join(cand['precedents'])}",
        f"{', '.join(cand['precedents'])} -FIXED_BY-> {cand['fix_name']}",
    ]
    for c in cand["conditions"]:
        steps.append(f"{cand['fix_name']} -REQUIRES-> {c['cond_name']} ({c['metric_id']} = {c['required']})")
        if c["observed"] is None:
            steps.append(f"{incident_id} has no observation of {c['metric_id']}  =>  UNKNOWN")
        else:
            steps.append(f"{incident_id} -OBSERVED-> {c['metric_id']} = {c['observed']}  =>  {c['status'].upper()}")
    return steps


def _evidence(cands: list[dict[str, Any]]) -> list[str]:
    lines = []
    for cand in cands:
        for c in cand["conditions"]:
            seen = c["observed"] if c["observed"] is not None else "not observed"
            lines.append(f"{cand['fix_name']}: needs {c['metric_id']} = {c['required']}, "
                         f"observed {seen} -> {c['status']}")
    return lines


def _decide_core(incident_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    cands = group_candidates(rows)
    applicable = [c for c in cands if c["status"] == "met"]
    pending = [c for c in cands if c["status"] == "unknown"]
    rejected = [c for c in cands if c["status"] == "contradicted"]
    rejected_note = ""
    if rejected:
        rejected_note = " Rejected: " + "; ".join(c["fix_name"] for c in rejected) + \
                        " (a prerequisite is contradicted by current telemetry)."

    decisive = (applicable or pending or rejected or [None])[0]
    paths = {c["fix_id"]: path_steps(incident_id, c) for c in cands}

    base = {
        "candidates": cands,
        "paths": paths,
        "path": paths[decisive["fix_id"]] if decisive else [f"{incident_id}: no precedent shares this symptom"],
        "evidence": _evidence(cands),
        "recommended_fix_id": None,
    }

    if applicable:
        best = applicable[0]
        return {**base,
            "verdict": "REUSE",
            "title": f"Reuse: {best['fix_name']}",
            "recommended_action": best["fix_name"],
            "recommended_fix_id": best["fix_id"],
            "reason": (f"Every prerequisite of this fix is confirmed by current observations, and its "
                       f"precedent ({', '.join(best['precedents'])}) has a verified successful outcome."
                       + rejected_note),
            "caveat": "Recommendation only. Validate before changing infrastructure. Nothing is applied automatically."}

    if pending:
        missing = sorted({c["metric_name"] for p in pending for c in p["conditions"] if c["status"] == "unknown"})
        return {**base,
            "verdict": "INVESTIGATE",
            "title": "Gather more evidence",
            "recommended_action": "Collect missing telemetry: " + ", ".join(missing),
            "reason": ("No precedent fix can be validated yet because prerequisite telemetry is missing "
                       "from the graph." + rejected_note),
            "caveat": "No fix should be applied until the cause is better established."}

    if rejected:
        return {**base,
            "verdict": "REJECT",
            "title": "No known fix applies",
            "recommended_action": "Escalate for manual root-cause analysis",
            "reason": "Every precedent fix has a prerequisite that current observations contradict." + rejected_note,
            "caveat": "Reusing any precedent would be unsupported by the evidence."}

    return {**base,
        "verdict": "INVESTIGATE",
        "title": "No precedent found",
        "recommended_action": "Start a fresh investigation",
        "reason": "No resolved incident with a verified fix shares this symptom.",
        "caveat": "No fix should be applied."}


def decide(incident_id: str, rows: list[dict[str, Any]],
           topology: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fix verdict from prerequisite validation, plus the likely trigger from topology.

    The topology never changes the verdict; it explains what probably started the incident.
    """
    d = _decide_core(incident_id, rows)
    topology = topology or {}
    trigger = topology.get("trigger")
    suspects = topology.get("suspects") or []
    d["likely_trigger"] = trigger
    if trigger:
        d["reason"] += (
            f" Likely trigger: {trigger['summary']} "
            f"({trigger['hops']} hop(s) from the affected service, {trigger['hours_before']}h before "
            f"the incident), corroborated by {trigger['metric_id']} = {trigger['observed']}.")
    elif suspects:
        names = "; ".join(x["summary"] for x in suspects[:2])
        d["reason"] += (f" Recent changes in the dependency chain ({names}) are not corroborated "
                        "by telemetry, so none is named as the cause.")
    return d