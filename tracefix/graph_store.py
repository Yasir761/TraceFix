"""FalkorDB access and synthetic incident data for TraceFix.

Design rule: observations, fix prerequisites and precedents are all graph data.
The decision engine never reads properties off the incident to choose a fix;
it only consumes what the Cypher validation query returns.

Schema
  (Incident)-[:AFFECTS]->(Service)
  (Incident)-[:HAS_SYMPTOM]->(Symptom)
  (Incident)-[:OBSERVED]->(Observation)-[:OF]->(Metric)
  (Incident)-[:CAUSED_BY]->(RootCause)-[:RESOLVED_BY]->(Fix)      (resolved incidents)
  (Incident)-[:FIXED_BY]->(Fix)-[:HAS_OUTCOME]->(Outcome)         (resolved incidents)
  (Fix)-[:REQUIRES]->(Condition)-[:ON]->(Metric)
  (Incident)-[:HAS_EVIDENCE]->(Evidence)
  (Service)-[:CALLS]->(Service)                                   (dependency topology)
  (Decision)-[:ABOUT]->(Incident), (Decision)-[:RECOMMENDED|REJECTED]->(Fix)   (written back by the agent)
  (Decision)-[:RELIED_ON]->(Observation), (Decision)-[:CITED_CHANGE]->(Change)
  (Incident)-[:FIXED_BY|FIX_FAILED]->(Fix)                        (recorded outcomes become precedent)
  (Change)-[:TOUCHED]->(Service), (Change)-[:CAN_CAUSE]->(Condition)
"""
from __future__ import annotations

import os
import time
from typing import Any

from falkordb import FalkorDB

GRAPH_NAME = os.getenv("FALKORDB_GRAPH", "tracefix")

H = 3600
T0 = 1_792_000_000  # epoch seconds, mid-Oct 2026; scenarios are spaced 72h apart

# (caller, dependency): the caller depends on the dependency.
CALLS = [
    ("svc-web", "svc-checkout"),
    ("svc-checkout", "svc-orders"),
    ("svc-checkout", "svc-payments"),
    ("svc-orders", "svc-dbproxy"),
    ("svc-payments", "svc-dbproxy"),
    ("svc-dbproxy", "svc-db"),
]

OPENED = {
    "INC-104": T0 - 500 * H, "INC-198": T0 - 300 * H,
    "INC-209": T0, "INC-250": T0 + 72 * H, "INC-301": T0 + 144 * H, "INC-320": T0 + 216 * H,
}

# Recent changes. "cause" is the Condition the change can produce, if any.
# Changes with no cause are plausible suspects the graph cannot corroborate.
CHANGES = [
    {"id": "chg-209-fw", "kind": "network", "svc": "svc-dbproxy", "at": T0 - 3 * H,
     "summary": "Firewall rule update on DB proxy route", "cause": "cond-route-failed"},
    {"id": "chg-209-deploy", "kind": "deploy", "svc": "svc-checkout", "at": T0 - 1 * H,
     "summary": "Checkout API v2.14 deploy", "cause": None},
    {"id": "chg-250-pool", "kind": "config", "svc": "svc-orders", "at": T0 + 72 * H - 5 * H,
     "summary": "Orders API max_connections lowered from 100 to 40", "cause": "cond-pool-saturated"},
    {"id": "chg-301-deploy", "kind": "deploy", "svc": "svc-checkout", "at": T0 + 144 * H - 1 * H,
     "summary": "Checkout API v2.15 deploy", "cause": None},
    {"id": "chg-320-flag", "kind": "config", "svc": "svc-orders", "at": T0 + 216 * H - 2 * H,
     "summary": "Orders API feature flag rollout (bulk-order-sync)", "cause": None},
]

STATIC_SEED = [
    "CREATE (:Service {id:'svc-web', name:'Storefront Web'})",
    "CREATE (:Service {id:'svc-checkout', name:'Checkout API'})",
    "CREATE (:Service {id:'svc-orders', name:'Orders API'})",
    "CREATE (:Service {id:'svc-payments', name:'Payments API'})",
    "CREATE (:Service {id:'svc-dbproxy', name:'DB Proxy'})",
    "CREATE (:Service {id:'svc-db', name:'Primary Database'})",
    *[
        f"MATCH (a:Service {{id:'{a}'}}), (b:Service {{id:'{b}'}}) CREATE (a)-[:CALLS]->(b)"
        for a, b in CALLS
    ],
    "CREATE (:Symptom {id:'sym-db-timeout', name:'database timeout'})",
    "CREATE (:Metric {id:'pool_status', name:'Connection pool status'})",
    "CREATE (:Metric {id:'route_status', name:'Database network route'})",
    "CREATE (:RootCause {id:'cause-pool', name:'Connection pool exhaustion'})",
    "CREATE (:RootCause {id:'cause-network', name:'Network route failure'})",
    "CREATE (:Fix {id:'fix-pool', name:'Increase connection pool capacity', action:'increase_pool', safe:true})",
    "CREATE (:Fix {id:'fix-network', name:'Inspect and restore the database network route', action:'inspect_network_route', safe:true})",
    "CREATE (:Condition {id:'cond-pool-saturated', name:'Pool is saturated', value:'saturated'})",
    "CREATE (:Condition {id:'cond-route-failed', name:'Route probe fails', value:'failed'})",
    "CREATE (:Outcome {id:'out-pool', status:'verified_success', note:'Pool saturation cleared after capacity increase'})",
    "CREATE (:Outcome {id:'out-network', status:'verified_success', note:'Connectivity restored after route correction'})",
    "MATCH (c:Condition {id:'cond-pool-saturated'}), (m:Metric {id:'pool_status'}) CREATE (c)-[:ON]->(m)",
    "MATCH (c:Condition {id:'cond-route-failed'}), (m:Metric {id:'route_status'}) CREATE (c)-[:ON]->(m)",
    "MATCH (f:Fix {id:'fix-pool'}), (c:Condition {id:'cond-pool-saturated'}) CREATE (f)-[:REQUIRES]->(c)",
    "MATCH (f:Fix {id:'fix-network'}), (c:Condition {id:'cond-route-failed'}) CREATE (f)-[:REQUIRES]->(c)",
    "MATCH (f:Fix {id:'fix-pool'}), (o:Outcome {id:'out-pool'}) CREATE (f)-[:HAS_OUTCOME]->(o)",
    "MATCH (f:Fix {id:'fix-network'}), (o:Outcome {id:'out-network'}) CREATE (f)-[:HAS_OUTCOME]->(o)",
    "MATCH (c:RootCause {id:'cause-pool'}), (f:Fix {id:'fix-pool'}) CREATE (c)-[:RESOLVED_BY]->(f)",
    "MATCH (c:RootCause {id:'cause-network'}), (f:Fix {id:'fix-network'}) CREATE (c)-[:RESOLVED_BY]->(f)",
]

# Resolved incidents carry a post-mortem (cause + fix). Open incidents only
# carry alert text and whatever telemetry was observed.
INCIDENTS: list[dict[str, Any]] = [
    {
        "id": "INC-104", "svc": "svc-checkout", "status": "resolved",
        "title": "Checkout API database timeouts",
        "desc": "checkout-api: db query timeout, p99 > 5s",
        "cause": "cause-pool", "fix": "fix-pool",
        "evidence": "Post-mortem: connection pool hit max capacity during a traffic spike",
        "obs": {"pool_status": "saturated", "route_status": "healthy"},
    },
    {
        "id": "INC-198", "svc": "svc-orders", "status": "resolved",
        "title": "Orders API database timeouts",
        "desc": "orders-api: db query timeout, p99 > 5s",
        "cause": "cause-network", "fix": "fix-network",
        "evidence": "Post-mortem: route change broke connectivity to the database",
        "obs": {"pool_status": "normal", "route_status": "failed"},
    },
    {   # Trap: identical alert to INC-104, different root cause.
        "id": "INC-209", "svc": "svc-checkout", "status": "open",
        "title": "Checkout API timeouts talking to the database",
        "desc": "checkout-api: db query timeout, p99 > 5s",
        "obs": {"pool_status": "normal", "route_status": "failed"},
    },
    {   # Agreement case: the familiar fix really does apply.
        "id": "INC-250", "svc": "svc-checkout", "status": "open",
        "title": "Checkout API database timeouts under load",
        "desc": "checkout-api: db query timeout, p99 > 5s",
        "obs": {"pool_status": "saturated", "route_status": "healthy"},
    },
    {   # Missing telemetry: nothing can be validated yet.
        "id": "INC-301", "svc": "svc-checkout", "status": "open",
        "title": "Checkout API database timeouts, no telemetry",
        "desc": "checkout-api: db query timeout, p99 > 5s",
        "obs": {},
    },
    {   # Every known prerequisite is contradicted: no known fix applies.
        "id": "INC-320", "svc": "svc-orders", "status": "open",
        "title": "Orders API database timeouts",
        "desc": "orders-api: db query timeout, p99 > 5s",
        "obs": {"pool_status": "normal", "route_status": "healthy"},
    },
]

# Validates every precedent fix against the incident's own observations.
# status: met | contradicted | unknown  (decided here, in the graph query)
CANDIDATE_QUERY = """
MATCH (i:Incident {id:$incident_id})-[:HAS_SYMPTOM]->(sym:Symptom)
      <-[:HAS_SYMPTOM]-(past:Incident)-[:FIXED_BY]->(f:Fix)
WHERE past.id <> i.id
MATCH (f)-[:HAS_OUTCOME]->(o:Outcome {status:'verified_success'})
MATCH (f)-[:REQUIRES]->(c:Condition)-[:ON]->(m:Metric)
OPTIONAL MATCH (m)<-[:OF]-(obs:Observation)<-[:OBSERVED]-(i)
RETURN sym.name AS symptom,
       past.id AS precedent_id,
       f.id AS fix_id, f.name AS fix_name,
       o.note AS outcome_note,
       c.id AS cond_id, c.name AS cond_name, c.value AS required,
       m.id AS metric_id, m.name AS metric_name,
       obs.id AS obs_id, obs.value AS observed,
       CASE WHEN obs IS NULL THEN 'unknown'
            WHEN obs.value = c.value THEN 'met'
            ELSE 'contradicted' END AS status
"""


# Changes inside the window before the incident, touching any service. Each change is
# checked against the incident's own observations via the condition it can cause.
RECENT_CHANGES_QUERY = """
MATCH (i:Incident {id:$incident_id})-[:AFFECTS]->(s:Service)
MATCH (ch:Change)-[:TOUCHED]->(t:Service)
WHERE ch.at <= i.opened_at AND ch.at >= i.opened_at - $window
OPTIONAL MATCH (ch)-[:CAN_CAUSE]->(cond:Condition)-[:ON]->(m:Metric)
OPTIONAL MATCH (m)<-[:OF]-(obs:Observation)<-[:OBSERVED]-(i)
RETURN s.id AS service_id, ch.id AS change_id, ch.summary AS summary, ch.kind AS kind,
       ch.at AS at, i.opened_at AS opened_at, t.id AS target_id, t.name AS target_name,
       cond.name AS cond_name, cond.value AS required, m.id AS metric_id, obs.value AS observed,
       CASE WHEN cond IS NULL THEN 'none'
            WHEN obs IS NULL THEN 'unknown'
            WHEN obs.value = cond.value THEN 'corroborated'
            ELSE 'contradicted' END AS support
ORDER BY ch.at DESC
"""


class GraphStore:
    def __init__(self) -> None:
        host = os.getenv("FALKORDB_HOST", "localhost")
        port = int(os.getenv("FALKORDB_PORT", "6379"))
        # Optional credentials so the same code runs against a managed/hosted FalkorDB.
        kwargs: dict[str, Any] = {}
        if os.getenv("FALKORDB_USERNAME"):
            kwargs["username"] = os.environ["FALKORDB_USERNAME"]
        if os.getenv("FALKORDB_PASSWORD"):
            kwargs["password"] = os.environ["FALKORDB_PASSWORD"]
        if os.getenv("FALKORDB_SSL", "").lower() in ("1", "true", "yes"):
            kwargs["ssl"] = True
        self.db = FalkorDB(host=host, port=port, **kwargs)
        self.graph = self.db.select_graph(GRAPH_NAME)

    # ---- plumbing -------------------------------------------------------
    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = self.graph.query(cypher, params or {})
        headers = [
            item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else str(item)
            for item in result.header
        ]
        return [
            {headers[i]: self._normalise(v) for i, v in enumerate(row)}
            for row in result.result_set
        ]

    @classmethod
    def _normalise(cls, value: Any) -> Any:
        if hasattr(value, "properties"):
            return dict(value.properties)
        if isinstance(value, (list, tuple)):
            return [cls._normalise(v) for v in value]
        return value

    # ---- seeding --------------------------------------------------------
    def reset_and_seed(self) -> None:
        try:
            self.graph.delete()
        except Exception:
            pass  # graph did not exist yet
        self.graph = self.db.select_graph(GRAPH_NAME)

        for statement in STATIC_SEED:
            self.graph.query(statement)
        for inc in INCIDENTS:
            self._seed_incident(inc)
        for ch in CHANGES:
            self._seed_change(ch)

    def _seed_change(self, ch: dict[str, Any]) -> None:
        self.graph.query(
            "MATCH (s:Service {id:$svc}) "
            "CREATE (:Change {id:$id, kind:$kind, summary:$summary, at:$at})-[:TOUCHED]->(s)", ch)
        if ch.get("cause"):
            self.graph.query(
                "MATCH (c:Change {id:$id}), (k:Condition {id:$cause}) CREATE (c)-[:CAN_CAUSE]->(k)", ch)

    def _seed_incident(self, inc: dict[str, Any]) -> None:
        p = {"id": inc["id"], "svc": inc["svc"], "title": inc["title"],
             "desc": inc["desc"], "status": inc["status"], "opened": OPENED[inc["id"]]}
        self.graph.query(
            "MATCH (s:Service {id:$svc}), (sym:Symptom {id:'sym-db-timeout'}) "
            "CREATE (i:Incident {id:$id, title:$title, description:$desc, status:$status, opened_at:$opened}) "
            "CREATE (i)-[:AFFECTS]->(s) CREATE (i)-[:HAS_SYMPTOM]->(sym)", p)
        if inc.get("cause"):
            self.graph.query(
                "MATCH (i:Incident {id:$id}), (c:RootCause {id:$cause}) "
                "CREATE (i)-[:CAUSED_BY]->(c)", {"id": inc["id"], "cause": inc["cause"]})
        if inc.get("fix"):
            self.graph.query(
                "MATCH (i:Incident {id:$id}), (f:Fix {id:$fix}) "
                "CREATE (i)-[:FIXED_BY]->(f)", {"id": inc["id"], "fix": inc["fix"]})
        if inc.get("evidence"):
            self.graph.query(
                "MATCH (i:Incident {id:$id}) "
                "CREATE (i)-[:HAS_EVIDENCE]->(:Evidence {id:$eid, name:'Post-mortem', detail:$detail})",
                {"id": inc["id"], "eid": f"ev-{inc['id']}", "detail": inc["evidence"]})
        for metric, value in inc["obs"].items():
            self.graph.query(
                "MATCH (i:Incident {id:$id}), (m:Metric {id:$metric}) "
                "CREATE (i)-[:OBSERVED]->(:Observation {id:$oid, name:$name, value:$value})-[:OF]->(m)",
                {"id": inc["id"], "metric": metric, "value": value,
                 "oid": f"obs-{inc['id']}-{metric}", "name": f"{metric} = {value}"})

    # ---- reads ----------------------------------------------------------
    def list_open_incidents(self) -> list[dict[str, Any]]:
        return self.query(
            "MATCH (i:Incident {status:'open'}) RETURN i.id AS id, i.title AS title ORDER BY i.id")

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        rows = self.query(
            "MATCH (i:Incident {id:$incident_id})-[:AFFECTS]->(s:Service) "
            "OPTIONAL MATCH (i)-[:OBSERVED]->(obs:Observation)-[:OF]->(m:Metric) "
            "RETURN i.id AS id, i.title AS title, i.description AS description, "
            "s.id AS service_id, s.name AS service, collect({metric: m.name, value: obs.value}) AS observations",
            {"incident_id": incident_id})
        if not rows:
            raise ValueError(f"Incident {incident_id} not found. Seed the graph first.")
        row = rows[0]
        row["observations"] = [o for o in row["observations"] if o.get("value") is not None]
        return row

    def get_resolved_incidents(self) -> list[dict[str, Any]]:
        return self.query(
            "MATCH (i:Incident)-[:FIXED_BY]->(f:Fix), (i)-[:AFFECTS]->(s:Service) "
            "RETURN i.id AS incident_id, i.title AS title, i.description AS description, "
            "s.name AS service, f.id AS fix_id, f.name AS fix_name ORDER BY i.id")

    def evaluate_candidates(self, incident_id: str, fix_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.query(CANDIDATE_QUERY, {"incident_id": incident_id})
        # Fixes a human reported as failed for this incident are never offered again.
        failed = {r["fix_id"] for r in self.query(
            "MATCH (:Incident {id:$incident_id})-[:FIX_FAILED]->(f:Fix) RETURN f.id AS fix_id",
            {"incident_id": incident_id})}
        return [r for r in rows if r["fix_id"] not in failed and (fix_id is None or r["fix_id"] == fix_id)]

    def find_precedent_fixes(self, incident_id: str) -> list[dict[str, Any]]:
        """Fixes that resolved past incidents with the same symptom (not yet validated)."""
        return self.query(
            "MATCH (i:Incident {id:$incident_id})-[:HAS_SYMPTOM]->(sym:Symptom)"
            "<-[:HAS_SYMPTOM]-(past:Incident)-[:FIXED_BY]->(f:Fix)-[:HAS_OUTCOME]->(o:Outcome) "
            "WHERE past.id <> i.id "
            "RETURN f.id AS fix_id, f.name AS fix_name, past.id AS precedent_id, "
            "o.status AS outcome_status",
            {"incident_id": incident_id})

    # ---- topology and graph algorithms -----------------------------------
    def get_service_graph(self) -> list[dict[str, Any]]:
        return self.query(
            "MATCH (a:Service)-[:CALLS]->(b:Service) "
            "RETURN a.id AS source, a.name AS source_name, b.id AS target, b.name AS target_name")

    def recent_change_rows(self, incident_id: str, window_seconds: int) -> list[dict[str, Any]]:
        return self.query(RECENT_CHANGES_QUERY, {"incident_id": incident_id, "window": window_seconds})

    def shortest_path(self, source_id: str, target_id: str) -> dict[str, Any] | None:
        """How the failing service reaches a changed one, over CALLS.

        FalkorDB only allows shortestPath() inside WITH or RETURN, so it is used there.
        If that form is rejected, fall back to plain variable-length matching, shortest first.
        """
        params = {"s": source_id, "t": target_id}
        try:
            rows = self.query(
                "MATCH (s:Service {id:$s}), (t:Service {id:$t}) "
                "WITH shortestPath((s)-[:CALLS*1..5]->(t)) AS p "
                "RETURN [n IN nodes(p) | n.id] AS ids, [n IN nodes(p) | n.name] AS names",
                params)
        except Exception:
            rows = self.query(
                "MATCH (s:Service {id:$s}), (t:Service {id:$t}) "
                "MATCH p = (s)-[:CALLS*1..5]->(t) "
                "RETURN [n IN nodes(p) | n.id] AS ids, [n IN nodes(p) | n.name] AS names, length(p) AS hops "
                "ORDER BY hops LIMIT 1",
                params)
        if not rows or not rows[0].get("ids"):
            return None
        return rows[0]

    def dependency_closure(self, service_id: str) -> list[str]:
        """algo.bfs: everything the service transitively depends on."""
        rows = self.query(
            "MATCH (s:Service {id:$id}) CALL algo.bfs(s, 5, 'CALLS') YIELD nodes "
            "RETURN [n IN nodes | n.id] AS ids", {"id": service_id})
        return rows[0]["ids"] if rows else []

    def blast_radius(self, service_id: str) -> list[dict[str, Any]]:
        """Services that transitively depend on this one."""
        return self.query(
            "MATCH (up:Service)-[:CALLS*1..5]->(t:Service {id:$id}) "
            "RETURN DISTINCT up.id AS id, up.name AS name ORDER BY name", {"id": service_id})

    def criticality(self, limit: int = 6) -> list[dict[str, Any]]:
        """algo.pageRank over CALLS: the most depended-on services."""
        return self.query(
            "CALL algo.pageRank('Service', 'CALLS') YIELD node, score "
            "RETURN node.id AS id, node.name AS name, score ORDER BY score DESC LIMIT $limit",
            {"limit": limit})

    # ---- decision write-back ---------------------------------------------
    def record_decision(self, incident_id: str, decision: dict[str, Any]) -> str:
        """Persist the agent's decision and the evidence it rested on as graph nodes and edges."""
        now = int(time.time())
        did = f"dec-{incident_id}-{now}"
        p = {"did": did, "iid": incident_id}
        self.graph.query(
            "MATCH (i:Incident {id:$iid}) "
            "CREATE (d:Decision {id:$did, verdict:$verdict, action:$action, created_at:$now, outcome:'pending'})"
            "-[:ABOUT]->(i)",
            {**p, "verdict": decision["verdict"], "action": decision["recommended_action"], "now": now})
        if decision.get("recommended_fix_id"):
            self.graph.query("MATCH (d:Decision {id:$did}), (f:Fix {id:$fid}) CREATE (d)-[:RECOMMENDED]->(f)",
                             {**p, "fid": decision["recommended_fix_id"]})
        obs_ids: set[str] = set()
        for cand in decision.get("candidates", []):
            if cand["status"] == "contradicted":
                self.graph.query("MATCH (d:Decision {id:$did}), (f:Fix {id:$fid}) CREATE (d)-[:REJECTED]->(f)",
                                 {**p, "fid": cand["fix_id"]})
            obs_ids.update(c["obs_id"] for c in cand["conditions"] if c.get("obs_id"))
        for oid in sorted(obs_ids):
            self.graph.query("MATCH (d:Decision {id:$did}), (o:Observation {id:$oid}) CREATE (d)-[:RELIED_ON]->(o)",
                             {**p, "oid": oid})
        trigger = decision.get("likely_trigger")
        if trigger:
            self.graph.query("MATCH (d:Decision {id:$did}), (c:Change {id:$cid}) CREATE (d)-[:CITED_CHANGE]->(c)",
                             {**p, "cid": trigger["change_id"]})
        return did

    def record_outcome(self, decision_id: str, worked: bool) -> dict[str, Any]:
        """Close the loop: a fix that worked becomes precedent; one that failed is excluded next time."""
        self.graph.query(
            "MATCH (d:Decision {id:$did}) SET d.outcome = $outcome, d.resolved_at = $now",
            {"did": decision_id, "outcome": "worked" if worked else "failed", "now": int(time.time())})
        rows = self.query(
            "MATCH (d:Decision {id:$did})-[:RECOMMENDED]->(f:Fix), (d)-[:ABOUT]->(i:Incident) "
            "RETURN f.id AS fix_id, f.name AS fix_name, i.id AS incident_id", {"did": decision_id})
        if not rows:
            return {}
        edge = "FIXED_BY" if worked else "FIX_FAILED"
        self.graph.query(
            f"MATCH (i:Incident {{id:$iid}}), (f:Fix {{id:$fid}}) MERGE (i)-[:{edge}]->(f)",
            {"iid": rows[0]["incident_id"], "fid": rows[0]["fix_id"]})
        return {**rows[0], "edge": edge}

    def list_decisions(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.query(
            "MATCH (d:Decision)-[:ABOUT]->(i:Incident) OPTIONAL MATCH (d)-[:RECOMMENDED]->(f:Fix) "
            "RETURN d.id AS id, i.id AS incident, d.verdict AS verdict, f.name AS fix, "
            "d.outcome AS outcome, d.created_at AS created_at ORDER BY d.created_at DESC LIMIT $limit",
            {"limit": limit})