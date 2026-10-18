
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tracefix.agent import investigate, run_scoreboard
from tracefix.agent_llm import investigate_with_llm
from tracefix.graph_store import GraphStore


app = FastAPI(
    title="TraceFix API",
    description="Graph-powered incident investigation API",
    version="1.0.0",
)

# Allow the local Next.js development server to call this API.
# FRONTEND_ORIGINS can override these defaults with a comma-separated list.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_store() -> GraphStore:
    return GraphStore()


class InvestigationRequest(BaseModel):
    incident_id: str = Field(min_length=1, max_length=100)
    agent_mode: bool = False


class OutcomeRequest(BaseModel):
    worked: bool


class RecordDecisionRequest(BaseModel):
    incident_id: str = Field(min_length=1, max_length=100)
    agent_mode: bool = False


def run_investigation(
    store: GraphStore,
    incident_id: str,
    agent_mode: bool,
) -> dict[str, Any]:
    runner = investigate_with_llm if agent_mode else investigate

    return {
        "incident_id": incident_id,
        **runner(store, incident_id),
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        store = get_store()
        incidents = store.list_open_incidents()

        return {
            "status": "ok",
            "service": "TraceFix API",
            "graph": "connected",
            "open_incidents": len(incidents),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"FalkorDB is unavailable: {exc}",
        ) from exc


@app.get("/api/incidents")
def list_incidents() -> dict[str, Any]:
    try:
        incidents = get_store().list_open_incidents()
        return {"incidents": incidents}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not load incidents: {exc}",
        ) from exc


@app.post("/api/investigate")
def investigate_incident(
    request: InvestigationRequest,
) -> dict[str, Any]:
    try:
        store = get_store()

        return run_investigation(
            store,
            request.incident_id,
            request.agent_mode,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {exc}",
        ) from exc


@app.get("/api/decisions")
def list_decisions() -> dict[str, Any]:
    try:
        decisions = get_store().list_decisions()
        return {"decisions": decisions}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not load decision history: {exc}",
        ) from exc


@app.post("/api/decisions/record")
def record_decision(
    request: RecordDecisionRequest,
) -> dict[str, Any]:
    try:
        store = get_store()

        # Recompute the decision on the backend instead of trusting
        # a verdict submitted by the browser.
        result = run_investigation(
            store,
            request.incident_id,
            request.agent_mode,
        )

        decision = result["decision"]
        decision_id = store.record_decision(
            request.incident_id,
            decision,
        )

        return {
            "recorded": True,
            "decision_id": decision_id,
            "incident_id": request.incident_id,
            "verdict": decision["verdict"],
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not record decision: {exc}",
        ) from exc


@app.post("/api/decisions/{decision_id}/outcome")
def record_outcome(
    decision_id: str,
    request: OutcomeRequest,
) -> dict[str, Any]:
    try:
        result = get_store().record_outcome(
            decision_id,
            request.worked,
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Decision not found, or it has no recommended fix "
                    "to record an outcome for."
                ),
            )

        return {
            "recorded": True,
            "decision_id": decision_id,
            "worked": request.worked,
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not record outcome: {exc}",
        ) from exc


@app.get("/api/scoreboard")
def scoreboard() -> dict[str, Any]:
    try:
        return {
            "scenarios": run_scoreboard(get_store()),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load scenario scoreboard: {exc}",
        ) from exc
