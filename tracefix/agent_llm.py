"""LLM agent loop: Claude chooses which graph tools to call.

Safety design: the verdict shown to the user is always recomputed by
decision_engine.decide() from the graph, so the model can choose the
investigation steps and write the explanation, but cannot invent a verdict.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .baseline import rank
from .decision_engine import decide, group_candidates
from .topology import analyse

MODEL = os.getenv("TRACEFIX_MODEL", "claude-sonnet-5-5")

SYSTEM = """You are TraceFix, a read-only incident investigation agent backed by a FalkorDB graph.
Investigate the incident using the tools. Rules:
- Start by reading the incident and its observations.
- Find precedent fixes, then check each candidate fix's prerequisites with check_prerequisites.
- Use trace_recent_changes to find which recent change in the service's dependency chain is
  corroborated by telemetry, and blast_radius to say who is affected. A change with no
  corroboration is only a suspect, never the cause.
- A fix may be recommended only if every prerequisite has status "met". "contradicted" means
  reject it. "unknown" means telemetry is missing: say what to collect, do not guess.
- Never recommend applying anything automatically; you only recommend.
- Finish with a 3-5 sentence explanation that cites incident ids, fix ids, and the observed values."""

TOOLS = [
    {"name": "get_incident",
     "description": "Read an incident: title, alert text, service, and the telemetry observations recorded for it.",
     "input_schema": {"type": "object", "properties": {"incident_id": {"type": "string"}},
                      "required": ["incident_id"]}},
    {"name": "find_precedent_fixes",
     "description": "List fixes that resolved past incidents with the same symptom, with their verified outcomes. Does not say whether a fix applies.",
     "input_schema": {"type": "object", "properties": {"incident_id": {"type": "string"}},
                      "required": ["incident_id"]}},
    {"name": "check_prerequisites",
     "description": "Validate one candidate fix against this incident's observations. Each prerequisite is met, contradicted, or unknown (missing telemetry).",
     "input_schema": {"type": "object",
                      "properties": {"incident_id": {"type": "string"}, "fix_id": {"type": "string"}},
                      "required": ["incident_id", "fix_id"]}},
    {"name": "trace_recent_changes",
     "description": "Graph-algorithm tool: ranks recent changes in the affected service's dependency chain (shortest path hops, recency) and says whether each is corroborated by this incident's telemetry.",
     "input_schema": {"type": "object", "properties": {"incident_id": {"type": "string"}},
                      "required": ["incident_id"]}},
    {"name": "blast_radius",
     "description": "Graph-algorithm tool: services that transitively depend on the given service and would be affected if it fails.",
     "input_schema": {"type": "object", "properties": {"service_id": {"type": "string"}},
                      "required": ["service_id"]}},
]


def dispatch(store: Any, name: str, args: dict[str, Any]) -> Any:
    try:
        if name == "get_incident":
            return store.get_incident(args["incident_id"])
        if name == "find_precedent_fixes":
            return store.find_precedent_fixes(args["incident_id"])
        if name == "check_prerequisites":
            cands = group_candidates(store.evaluate_candidates(args["incident_id"], args["fix_id"]))
            return cands[0] if cands else {"error": f"{args['fix_id']} is not a precedent fix for this incident"}
        if name == "trace_recent_changes":
            t = analyse(store, args["incident_id"])
            return {"suspects": t["suspects"], "trigger": t["trigger"], "errors": t["errors"]}
        if name == "blast_radius":
            return store.blast_radius(args["service_id"])
        return {"error": f"unknown tool {name}"}
    except Exception as exc:  # returned to the model so it can recover
        return {"error": str(exc)}


def investigate_with_llm(store: Any, incident_id: str, client: Any = None, max_steps: int = 8) -> dict[str, Any]:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Investigate incident {incident_id} and recommend a next action."}]
    trace: list[dict[str, Any]] = []
    narrative = ""

    for _ in range(max_steps):
        resp = client.messages.create(model=MODEL, max_tokens=1000, system=SYSTEM,
                                      tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            narrative = "".join(b.text for b in resp.content if b.type == "text")
            break
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                out = dispatch(store, block.name, block.input)
                trace.append({"tool": block.name, "input": dict(block.input), "output": out})
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(out, default=str)})
        messages.append({"role": "user", "content": results})
    else:
        narrative = "(Agent stopped at the step limit. The graph verdict below is still authoritative.)"

    # Authoritative verdict: computed from the graph, never from the model's text.
    try:
        topology = analyse(store, incident_id)
    except Exception as exc:
        topology = {"suspects": [], "trigger": None, "errors": [str(exc)]}
    decision = decide(incident_id, store.evaluate_candidates(incident_id), topology)
    return {
        "incident": store.get_incident(incident_id),
        "decision": decision,
        "topology": topology,
        "baseline": rank(store.get_incident(incident_id), [r for r in store.get_resolved_incidents() if r["incident_id"] != incident_id]),
        "narrative": narrative,
        "tool_trace": trace,
        "validated": any(t["tool"] == "check_prerequisites" for t in trace),
    }