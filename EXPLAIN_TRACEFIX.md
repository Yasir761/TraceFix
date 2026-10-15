# How to explain TraceFix

A study sheet for Rules 12 and 13: you must be able to explain the graph model, the queries, the architecture and the decisions. Don't memorise this. Read it with the code open, run each query yourself, and put things in your own words.

## 1. The pitch in 30 seconds

An alert fires that looks exactly like a past incident. A similarity-based agent repeats the old fix. TraceFix asks a harder question: *do the conditions that made that fix work actually hold right now?* It answers by walking a graph that connects incidents, fixes, their prerequisites, and the telemetry observed on the current incident. It also walks the service dependency graph to find which recent change likely started the problem, and it shows the path it followed.

## 2. The architecture in one minute

```
Streamlit UI (app.py)
   └─ agent.py ── runs both approaches on the same incident
        ├─ baseline.py        text similarity over past incidents (the "naive" agent)
        ├─ graph_store.py     all FalkorDB access: seed data, queries, write-back
        ├─ decision_engine.py turns validation rows into REUSE / REJECT / INVESTIGATE
        └─ topology.py        recent changes, shortest path, bfs, pagerank, blast radius
   └─ agent_llm.py (optional) an LLM chooses which graph tools to call
FalkorDB (Docker) ── the only data store
```

Key sentence: **the graph computes the facts, Python only aggregates them, and the LLM (if used) never decides the verdict.**

## 3. The graph model, in plain words

| Node | What it is | Why it exists |
|---|---|---|
| Incident | An alert or outage | The thing being investigated, or a past one |
| Symptom | e.g. "database timeout" | Links incidents that look alike |
| Service | Checkout API, DB Proxy, ... | What fails and what depends on what |
| Metric | e.g. `pool_status` | A thing we can measure |
| Observation | `pool_status = normal` on INC-209 | The telemetry recorded for one incident |
| Fix | A remediation that worked before | The candidate action |
| Condition | `pool_status = saturated` | What must be true for a fix to apply |
| Outcome | `verified_success` | Proof a fix really worked |
| Change | A deploy, config or firewall change | Possible trigger, with a timestamp |
| Decision | What the agent recommended | Memory, written back to the graph |

Key edges: `Fix-[:REQUIRES]->Condition-[:ON]->Metric` and `Incident-[:OBSERVED]->Observation-[:OF]->Metric`. Both sides point at the same `Metric`, so a prerequisite and an observation can be compared through the graph. `Service-[:CALLS]->Service` is the dependency graph, and `Change-[:CAN_CAUSE]->Condition` links a change to the telemetry it would produce.

## 4. The queries, one by one

You can paste each into FalkorDB Browser (http://localhost:3000). If parameters are awkward there, replace `$incident_id` with `'INC-209'` directly.

**A. Fix validation (`CANDIDATE_QUERY`).**
1. Start at the current incident and follow its symptom to *other* incidents with the same symptom.
2. Follow those incidents to the fix that resolved them, keeping only fixes with a `verified_success` outcome.
3. For each fix, list the conditions it requires and the metric each condition is about.
4. `OPTIONAL MATCH` the current incident's observation of that metric. Optional, because a missing observation is meaningful.
5. A `CASE` labels each prerequisite: no observation → `unknown`, same value → `met`, different value → `contradicted`.

Why `OPTIONAL MATCH`: a normal `MATCH` would silently drop prerequisites we have no telemetry for, and the agent would think the fix was fine. We need "unknown" to be a first-class answer.

**B. Recent changes (`RECENT_CHANGES_QUERY`).** Finds changes in the 24 hours before the incident, then checks if the condition each change *can cause* matches what was observed. `corroborated` means the change's effect is actually visible in this incident's telemetry. A change with no link to any condition is `none`.

**C. `shortestPath`.** Hops from the affected service to the changed service over `CALLS`, e.g. Checkout → Orders → DB Proxy. FalkorDB only accepts `shortestPath()` inside `WITH` or `RETURN`, which is why the code uses `WITH shortestPath(...) AS p`.

**D. `algo.bfs`.** Everything the affected service depends on, transitively.

**E. `algo.pageRank`.** Scores services by how much the graph leans on them. Check its output yourself in Browser before you describe it, because it follows edge direction.

**F. Blast radius.** A variable-length match going the *other* way: who depends on the changed service, directly or indirectly.

**G. Write-back.** `record_decision` creates a `Decision` node and links it to the incident, the fix recommended, fixes rejected, observations relied on, and the change cited. `record_outcome` marks the result and adds `FIXED_BY` (worked) or `FIX_FAILED` (didn't) on the incident.

## 5. The decision logic

`group_candidates` collapses rows per fix and takes the worst prerequisite status (contradicted > unknown > met). Then `decide`:

| Situation | Verdict |
|---|---|
| At least one fix has every prerequisite met | **REUSE** that fix |
| None met, at least one has missing telemetry | **INVESTIGATE**, listing what to collect |
| Every candidate has a contradicted prerequisite | **REJECT**, escalate for manual analysis |
| No precedent with this symptom | **INVESTIGATE**, start fresh |

Topology never changes the verdict. It adds a "likely trigger" explanation when a change is corroborated.

## 6. Design decisions and the reasons

- **Verdict from the graph, not the LLM.** Models can state a wrong fix confidently. The model only picks tools and writes the explanation, and the verdict is recomputed from the graph afterwards.
- **Fixed, human-written queries.** The model never writes Cypher, so a bad query or an injection can't come from it.
- **Corroboration over recency.** The most recent change is often the wrong suspect. A change only counts when its effect is observed.
- **"Unknown" is its own state.** Missing telemetry is different from a normal reading, and the agent asks for it rather than guessing.
- **Recommendations only.** The agent changes nothing in infrastructure. Writes go only to its own memory in the graph.
- **Synthetic data.** Required by the data rule, and it lets the scenarios be controlled.
- **Streamlit and Python.** Fastest route to a working UI in four days.
- **Ranking heuristic.** Corroborated first, then fewer hops, then more recent. It's my design choice, not a learned model.

## 7. Real problems you hit (good stories to tell)

- `shortestPath` inside a `MATCH` was rejected by FalkorDB. It's only allowed in `WITH` or `RETURN`, and the first version dropped every multi-hop suspect silently until you spotted it from the UI.
- A `NOT (pattern)` predicate in the validation query's `WHERE` clause broke it with "'o' not defined", so failed fixes are now filtered by a separate simple query.

Both show you debugged against the real database instead of trusting generated code.

## 8. Likely judge questions

**"If I remove FalkorDB, does it still work?"** No. Validation, traversals, algorithms and decision memory all run in the database, and there is no fallback store.

**"Isn't this just if/else?"** The branching is small, but the facts feeding it come from a multi-hop pattern match and graph algorithms. The branches only combine `met`, `contradicted` and `unknown`.

**"Why not let the LLM write Cypher?"** It can produce subtly wrong or expensive queries and leaves nothing to audit. Fixed queries are reviewable and the model can't invent a verdict.

**"What does the LLM do?"** In the optional agent mode it chooses which of five tools to call and writes the explanation. Say plainly whether you tested it live.

**"Is the baseline a strawman?"** It's a simple TF-IDF similarity, and it's deliberately naive. A stronger embedding baseline is a fair next step, and with identical alert text, any text-only method would struggle.

**"Does it scale?"** Say honestly that you haven't tested it. The validation cost grows with the number of precedent fixes times their prerequisites, and traversals are depth-limited.

**"What's synthetic and what's real?"** Everything is synthetic, four hand-built scenarios that show where similarity and graph validation diverge. They are not a benchmark.

**"What did AI write versus you?"** Answer from your own experience. Don't rehearse a line you can't stand behind.

**"What would you do next?"** Per-team graphs, real telemetry ingestion, a stronger baseline, and more precedent data.

## 9. Prove to yourself that you understand it

Do these without my help. If one is hard, that's the part to study.

1. **Add a third fix.** Create a "restart the cache" fix with its own condition, metric, outcome and a past incident, then reseed. Predict what each existing scenario does before you run it.
2. **Change the window.** In `topology.py`, change the 24-hour window and predict which changes disappear for INC-209.
3. **Change the ranking.** Make recency matter more than hops. Which suspect now comes first for INC-209?
4. **Add a service.** Add a cache that Checkout calls. What happens to the blast radius of the DB Proxy and the PageRank scores?
5. **Break a prerequisite.** Change INC-250's `pool_status` observation to `normal` and predict the verdict.
6. **Explain a failure.** Run the validation query in Browser for INC-301 and explain why every row says `unknown`.

## 10. Confirm these before you submit

- [ ] The decision record and outcome buttons work against your FalkorDB (they were tested only against a stub).
- [ ] Agent mode was tested with a live model, or the README says it wasn't.
- [ ] You can state what existed before Oct 15, 12:01 AM IST.
- [ ] The AI disclosure and development timeline in the README are in your own words.