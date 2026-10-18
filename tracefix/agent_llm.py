
"""Gemini-powered LLM agent loop for TraceFix.

The model chooses which graph tools to call and writes the explanation.
The final verdict is always recomputed by decision_engine.decide() from
the graph, so the model cannot invent the authoritative verdict.
"""
from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .baseline import rank
from .decision_engine import decide, group_candidates
from .topology import analyse


load_dotenv()

MODEL = os.getenv("TRACEFIX_MODEL", "gemini-3.5-flash")

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
    {
        "name": "get_incident",
        "description": "Read an incident: title, alert text, service, and the telemetry observations recorded for it.",
        "input_schema": {
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    },
    {
        "name": "find_precedent_fixes",
        "description": "List fixes that resolved past incidents with the same symptom, with their verified outcomes. Does not say whether a fix applies.",
        "input_schema": {
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    },
    {
        "name": "check_prerequisites",
        "description": "Validate one candidate fix against this incident's observations. Each prerequisite is met, contradicted, or unknown (missing telemetry).",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "fix_id": {"type": "string"},
            },
            "required": ["incident_id", "fix_id"],
        },
    },
    {
        "name": "trace_recent_changes",
        "description": "Graph-algorithm tool: ranks recent changes in the affected service's dependency chain and says whether each is corroborated by this incident's telemetry.",
        "input_schema": {
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    },
    {
        "name": "blast_radius",
        "description": "Graph-algorithm tool: services that transitively depend on the given service and would be affected if it fails.",
        "input_schema": {
            "type": "object",
            "properties": {"service_id": {"type": "string"}},
            "required": ["service_id"],
        },
    },
]


def dispatch(store: Any, name: str, args: dict[str, Any]) -> Any:
    """Run an approved, read-only graph tool."""
    try:
        if name == "get_incident":
            return store.get_incident(args["incident_id"])

        if name == "find_precedent_fixes":
            return store.find_precedent_fixes(args["incident_id"])

        if name == "check_prerequisites":
            candidates = group_candidates(
                store.evaluate_candidates(args["incident_id"], args["fix_id"])
            )
            return (
                candidates[0]
                if candidates
                else {
                    "error": (
                        f"{args['fix_id']} is not a precedent fix "
                        "for this incident"
                    )
                }
            )

        if name == "trace_recent_changes":
            result = analyse(store, args["incident_id"])
            return {
                "suspects": result["suspects"],
                "trigger": result["trigger"],
                "errors": result["errors"],
            }

        if name == "blast_radius":
            return store.blast_radius(args["service_id"])

        return {"error": f"Unknown tool: {name}"}

    except Exception as exc:
        # Return tool errors to the model so it can recover.
        return {"error": str(exc)}


def investigate_with_llm(
    store: Any,
    incident_id: str,
    client: Any = None,
    max_steps: int = 8,
) -> dict[str, Any]:
    """Investigate an incident using Gemini function calling."""

    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Add it to the project's .env file."
            )
        client = genai.Client(api_key=api_key)

    function_declarations = [
        types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["input_schema"],
        )
        for tool in TOOLS
    ]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[types.Tool(function_declarations=function_declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        max_output_tokens=1000,
    )

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        f"Investigate incident {incident_id} "
                        "and recommend a next action."
                    )
                )
            ],
        )
    ]

    trace: list[dict[str, Any]] = []
    narrative = ""

    for _ in range(max_steps):
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        if not response.candidates:
            raise RuntimeError(
                "Gemini returned no response. Check the API key, model, "
                "and API availability."
            )

        model_content = response.candidates[0].content
        if model_content is None:
            raise RuntimeError("Gemini returned an empty response.")

        contents.append(model_content)

        function_calls = [
            part.function_call
            for part in (model_content.parts or [])
            if part.function_call is not None
        ]

        if not function_calls:
            narrative = response.text or ""
            break

        function_responses = []

        for call in function_calls:
            name = call.name
            args = dict(call.args or {})

            if name not in {tool["name"] for tool in TOOLS}:
                output = {"error": f"Unknown tool requested: {name}"}
            else:
                output = dispatch(store, name, args)

            trace.append(
                {
                    "tool": name,
                    "input": args,
                    "output": output,
                }
            )

            # Convert tool output to JSON-compatible data.
            safe_output = json.loads(json.dumps(output, default=str))

            function_responses.append(
                types.Part.from_function_response(
                    name=name,
                    response={"result": safe_output},
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=function_responses,
            )
        )
    else:
        narrative = (
            "(Agent stopped at the step limit. "
            "The graph verdict below is still authoritative.)"
        )

    # Authoritative verdict: computed from the graph, never from model text.
    try:
        topology = analyse(store, incident_id)
    except Exception as exc:
        topology = {
            "suspects": [],
            "trigger": None,
            "errors": [str(exc)],
        }

    decision = decide(
        incident_id,
        store.evaluate_candidates(incident_id),
        topology,
    )

    incident = store.get_incident(incident_id)
    resolved_incidents = [
        item
        for item in store.get_resolved_incidents()
        if item["incident_id"] != incident_id
    ]

    return {
        "incident": incident,
        "decision": decision,
        "topology": topology,
        "baseline": rank(incident, resolved_incidents),
        "narrative": narrative,
        "tool_trace": trace,
        "validated": any(
            item["tool"] == "check_prerequisites" for item in trace
        ),
    }
