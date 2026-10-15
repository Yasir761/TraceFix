# TraceFix

**Don't repeat a fix just because the error looks familiar.**

TraceFix is a read-only incident investigation agent built on FalkorDB. When an alert looks like a past incident, a similarity-based agent repeats the old fix. TraceFix instead checks, in the graph, whether that fix's prerequisites actually hold for the current incident, traces recent changes through the service dependency graph, and explains its decision with the graph path it followed.

Built for **Graph Hacks: Context for AI Agents** (WeMakeDevs x FalkorDB), **Track 01: Agents That Act on Connected Data**.

**Track entered:** Track 01, Agents That Act on Connected Data.

> Demo video: `<link>` · Blog post: `<link>` · Public repo: `<link>` · Live demo: `<link, or remove if running locally only>`

## The central proof

Same alert, two different root causes. `INC-104` (past) was a saturated connection pool. `INC-209` (now) fires the identical alert, `checkout-api: db query timeout, p99 > 5s`, but its pool is normal and its database route is failing.

| | Baseline (text similarity) | TraceFix (graph validation) |
|---|---|---|
| INC-209 | Repeats the pool fix (88% match to INC-104) | Rejects it: `pool_status` is `normal`, the fix requires `saturated`. Recommends the network-route fix. |
| Likely trigger | "Most recent change" would be the Checkout deploy | Traces 2 hops (Checkout → Orders → DB Proxy) to a firewall change whose effect is corroborated by `route_status = failed` |
| INC-301 (no telemetry) | Confidently repeats the pool fix | Withholds action and lists the missing telemetry |

The repo ships four scripted scenarios (INC-209, INC-250, INC-301, INC-320). They are hand-built and synthetic, so they show where graph validation and text similarity diverge. They are **not** a benchmark.

## Why the graph is essential

FalkorDB is the only data store in TraceFix, and there is no fallback database. Take it out and the product stops working:

- **Fix validation** is a multi-hop pattern match across incidents, symptoms, fixes, prerequisites, metrics and observations, run as one Cypher query.
- **Change tracing** uses `shortestPath`, `algo.bfs`, `algo.pageRank` and variable-length traversals over the service dependency graph.
- **Decision memory** is written back as nodes and edges, and recorded outcomes change what later traversals return.

## How it works

1. **Validate precedent fixes (Cypher).** Find fixes that resolved past incidents with the same symptom, then label each of the fix's prerequisites as `met`, `contradicted` or `unknown` against this incident's own observations. A fix is recommended only if every prerequisite is met.
2. **Trace recent changes through the topology.** Changes in the 24 hours before the incident that touch the affected service or anything it depends on are ranked. A change counts as *corroborated* only if the condition it can cause is actually observed on this incident, so recency alone never wins.
3. **Explain with the graph path.** The decision path and Graphviz view are built only from rows the queries returned.
4. **Write decisions back.** The decision, the fixes it recommended or rejected, the observations it relied on and the change it cited are stored as nodes and edges. A recorded outcome changes later behavior: a fix that worked becomes precedent, a fix that failed is not offered again for that incident.

The verdict is computed from the graph by `decision_engine.py`. The optional LLM mode chooses which graph tools to call and writes the explanation, but cannot set the verdict.

## Graph data model

```
(Incident)-[:AFFECTS]->(Service)
(Incident)-[:HAS_SYMPTOM]->(Symptom)
(Incident)-[:OBSERVED]->(Observation)-[:OF]->(Metric)
(Incident)-[:CAUSED_BY]->(RootCause)-[:RESOLVED_BY]->(Fix)        resolved incidents
(Incident)-[:FIXED_BY]->(Fix)-[:HAS_OUTCOME]->(Outcome)           resolved incidents
(Incident)-[:HAS_EVIDENCE]->(Evidence)
(Fix)-[:REQUIRES]->(Condition)-[:ON]->(Metric)
(Service)-[:CALLS]->(Service)                                     dependency topology
(Change)-[:TOUCHED]->(Service)
(Change)-[:CAN_CAUSE]->(Condition)
(Decision)-[:ABOUT]->(Incident)                                   written by the agent
(Decision)-[:RECOMMENDED|REJECTED]->(Fix)
(Decision)-[:RELIED_ON]->(Observation)
(Decision)-[:CITED_CHANGE]->(Change)
(Incident)-[:FIX_FAILED]->(Fix)                                   recorded human outcome
```

Services: Storefront Web → Checkout API → {Orders API, Payments API} → DB Proxy → Primary Database.

## Cypher and graph algorithms the product depends on

**Fix validation** (`CANDIDATE_QUERY` in `tracefix/graph_store.py`):

```cypher
MATCH (i:Incident {id:$incident_id})-[:HAS_SYMPTOM]->(sym:Symptom)
      <-[:HAS_SYMPTOM]-(past:Incident)-[:FIXED_BY]->(f:Fix)
WHERE past.id <> i.id
MATCH (f)-[:HAS_OUTCOME]->(o:Outcome {status:'verified_success'})
MATCH (f)-[:REQUIRES]->(c:Condition)-[:ON]->(m:Metric)
OPTIONAL MATCH (m)<-[:OF]-(obs:Observation)<-[:OBSERVED]-(i)
RETURN f.id AS fix_id, f.name AS fix_name, c.name AS cond_name,
       CASE WHEN obs IS NULL THEN 'unknown'
            WHEN obs.value = c.value THEN 'met'
            ELSE 'contradicted' END AS status
```

**Recent changes, checked against telemetry** (`RECENT_CHANGES_QUERY`):

```cypher
MATCH (i:Incident {id:$incident_id})-[:AFFECTS]->(s:Service)
MATCH (ch:Change)-[:TOUCHED]->(t:Service)
WHERE ch.at <= i.opened_at AND ch.at >= i.opened_at - $window
OPTIONAL MATCH (ch)-[:CAN_CAUSE]->(cond:Condition)-[:ON]->(m:Metric)
OPTIONAL MATCH (m)<-[:OF]-(obs:Observation)<-[:OBSERVED]-(i)
RETURN ch.id, ch.summary, t.id,
       CASE WHEN cond IS NULL THEN 'none'
            WHEN obs IS NULL THEN 'unknown'
            WHEN obs.value = cond.value THEN 'corroborated'
            ELSE 'contradicted' END AS support
```

**Graph algorithms** (run inside FalkorDB):

```cypher
-- how the failing service reaches a changed service
WITH shortestPath((s)-[:CALLS*1..5]->(t)) AS p
RETURN [n IN nodes(p) | n.id]

-- dependency closure
CALL algo.bfs(s, 5, 'CALLS') YIELD nodes

-- most depended-on services
CALL algo.pageRank('Service', 'CALLS') YIELD node, score

-- blast radius of the likely trigger
MATCH (up:Service)-[:CALLS*1..5]->(t:Service {id:$id}) RETURN DISTINCT up.id
```

Suspect ranking (corroborated first, then fewer hops, then more recent) is a design heuristic chosen by the author, not a learned model.

## Run it

Requirements: Docker, Python 3.10+.

```bash
docker compose up -d            # FalkorDB on :6379, FalkorDB Browser on :3000
pip install -r requirements.txt
python -m streamlit run tracefix/app.py
```

1. Click **Reset & seed demo graph** in the sidebar.
2. Pick an incident (INC-209 is the main demo) and click **Investigate incident**.
3. Optional: open http://localhost:3000 (FalkorDB Browser) to explore the graph and run the queries above.

Environment variables (all optional): `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_GRAPH`, and for a hosted FalkorDB (such as FalkorDB Cloud) `FALKORDB_USERNAME`, `FALKORDB_PASSWORD`, `FALKORDB_SSL`.

### Optional: agent mode

Set `ANTHROPIC_API_KEY` (and optionally `TRACEFIX_MODEL`) to enable **Agent mode**, where an LLM chooses among graph tools (`get_incident`, `find_precedent_fixes`, `check_prerequisites`, `trace_recent_changes`, `blast_radius`). The verdict shown is always recomputed from the graph. Without a key, the app runs fully in deterministic mode.

## Safety and limitations

- Recommendations only. TraceFix never changes infrastructure.
- All data is synthetic. No production systems are connected.
- The baseline is a simple TF-IDF similarity over incident text. A stronger embedding baseline would be a fairer comparison.
- Four hand-built scenarios demonstrate the idea; they do not measure accuracy.
- `<Fill in: anything you tested or did not test, e.g. agent mode with a live LLM.>`

## Development timeline

`<Confirm and edit: state plainly what existed before the event started on Oct 15, 12:01 AM IST (for example, only the concept and notes) and that the main coding and design work happened during the hackathon.>`

## AI assistance disclosure

`<Edit this to match what is true for you.>` This project was built with assistance from Claude (Anthropic) for design discussion, code generation and debugging. The author, Mohammad Yasir, chose the project idea and scenarios, wrote the initial prototype, ran and tested everything against FalkorDB, and reviewed the code. Sections that were substantially AI-generated: `<list, e.g. topology.py, baseline.py, agent_llm.py>`.

## Project layout

```
app.py                      Streamlit UI (lives in tracefix/ in your folder layout)
tracefix/graph_store.py     FalkorDB access, schema, seed data, queries, decision write-back
tracefix/decision_engine.py Aggregates graph validation into a verdict
tracefix/topology.py        Change tracing and graph-algorithm analysis
tracefix/baseline.py        Similarity baseline
tracefix/agent.py           Runs baseline and TraceFix; scenario scoreboard
tracefix/agent_llm.py       Optional LLM tool-selection loop
docker-compose.yml          FalkorDB
```