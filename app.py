from __future__ import annotations

import html as _html
import os

import streamlit as st

from tracefix.agent import investigate, run_scoreboard
from tracefix.agent_llm import investigate_with_llm
from tracefix.graph_store import GraphStore

st.set_page_config(page_title="TraceFix | Evidence before action", page_icon="🕸️",
                   layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stMarkdown, button { font-family: 'Inter', system-ui, sans-serif; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1180px; padding-top: 1.6rem; padding-bottom: 4rem; }
code, pre { font-family: 'JetBrains Mono', ui-monospace, monospace !important; }

.tf-hero { padding: 2.3rem 2.4rem; border-radius: 24px; border: 1px solid rgba(127,127,127,.22);
  background: radial-gradient(900px 340px at 0% 0%, rgba(99,102,241,.30), transparent 62%),
              radial-gradient(800px 340px at 100% 0%, rgba(20,184,166,.22), transparent 58%),
              rgba(127,127,127,.06); }
.tf-eyebrow { font-size: .74rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; opacity: .65; }
.tf-hero h1 { font-size: 3rem; font-weight: 800; letter-spacing: -.03em; margin: .2rem 0 .5rem 0; padding: 0; line-height: 1.05; }
.tf-lead { font-size: 1.12rem; line-height: 1.55; max-width: 46rem; opacity: .9; margin: 0 0 1.1rem 0; }
.tf-tag { display: inline-block; padding: .22rem .7rem; margin: 0 .4rem .3rem 0; border-radius: 999px;
  font-size: .76rem; font-weight: 500; border: 1px solid rgba(127,127,127,.35); background: rgba(127,127,127,.08); }

.tf-section { font-size: 1.25rem; font-weight: 700; letter-spacing: -.01em; margin: 2.2rem 0 .3rem 0; }
.tf-sub { opacity: .68; margin: 0 0 1rem 0; font-size: .95rem; }

.tf-card { height: 100%; padding: 1.1rem 1.15rem; border-radius: 18px; border: 1px solid rgba(127,127,127,.22);
  background: rgba(127,127,127,.06); }
.tf-card h4 { margin: .1rem 0 .35rem 0; font-size: 1rem; font-weight: 650; }
.tf-card p { margin: 0; font-size: .88rem; line-height: 1.5; opacity: .78; }
.tf-num { display: inline-flex; align-items: center; justify-content: center; width: 1.7rem; height: 1.7rem;
  border-radius: 999px; font-size: .82rem; font-weight: 700; margin-bottom: .55rem;
  background: linear-gradient(135deg, #6366f1, #14b8a6); color: white; }

.tf-note { margin-top: 1rem; padding: .85rem 1.1rem; border-radius: 14px; font-size: .92rem;
  border: 1px dashed rgba(127,127,127,.4); opacity: .9; }
.tf-guard { display: inline-block; margin: .6rem .5rem 0 0; font-size: .82rem; opacity: .8; }

.tf-scn { padding: 1rem 1.1rem 1.05rem 1.1rem; border-radius: 18px; border: 1px solid rgba(127,127,127,.22);
  background: rgba(127,127,127,.06); min-height: 9.2rem; margin-bottom: .5rem; }
.tf-scn.sel { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,.35); }
.tf-scn .tf-id { font-size: .72rem; font-weight: 600; letter-spacing: .06em; opacity: .6; }
.tf-scn h4 { margin: .15rem 0 .3rem 0; font-size: 1rem; font-weight: 650; }
.tf-scn p { margin: 0; font-size: .84rem; line-height: 1.45; opacity: .75; }

.tf-verdict { padding: 1.5rem 1.7rem; border-radius: 20px; border: 1px solid rgba(127,127,127,.22);
  border-left: 7px solid var(--c); background: rgba(127,127,127,.06); }
.tf-vlabel { font-size: .74rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--c); }
.tf-vtitle { font-size: 1.65rem; font-weight: 750; letter-spacing: -.02em; margin: .25rem 0 .55rem 0; line-height: 1.2; }
.tf-verdict p { margin: 0 0 1rem 0; line-height: 1.6; opacity: .9; }
.tf-action { display: flex; flex-direction: column; gap: .15rem; padding: .8rem 1rem; border-radius: 12px;
  background: rgba(127,127,127,.10); }
.tf-action span { font-size: .72rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; opacity: .6; }
.tf-action b { font-size: 1.02rem; }
.tf-caveat { margin-top: .8rem; font-size: .82rem; opacity: .6; }

.tf-cmp { padding: 1.2rem 1.3rem; border-radius: 18px; border: 1px solid rgba(127,127,127,.22); height: 100%; }
.tf-cmp.base { background: rgba(127,127,127,.06); }
.tf-cmp.mine { background: linear-gradient(135deg, rgba(99,102,241,.14), rgba(20,184,166,.10)); border-color: rgba(99,102,241,.45); }
.tf-cmp .tf-big { font-size: 1.15rem; font-weight: 700; margin: .35rem 0 .45rem 0; line-height: 1.3; }
.tf-cmp p { margin: 0; font-size: .88rem; line-height: 1.5; opacity: .78; }
.tf-banner { margin-top: .9rem; padding: .85rem 1.15rem; border-radius: 14px; font-size: .95rem; font-weight: 500; }
.tf-banner.bad { background: rgba(239,68,68,.13); border: 1px solid rgba(239,68,68,.4); }
.tf-banner.good { background: rgba(16,185,129,.13); border: 1px solid rgba(16,185,129,.4); }

.tf-path { list-style: none; margin: .3rem 0 0 0; padding: 0; counter-reset: step; }
.tf-path li { position: relative; margin: 0; padding: .42rem 0 .42rem 2.5rem; counter-increment: step; font-size: .9rem; }
.tf-path li::before { content: counter(step); position: absolute; left: 0; top: .32rem; width: 1.6rem; height: 1.6rem;
  border-radius: 999px; text-align: center; line-height: 1.6rem; font-size: .75rem; font-weight: 700;
  background: rgba(99,102,241,.25); }
.tf-path li::after { content: ""; position: absolute; left: .78rem; top: 2rem; bottom: -.4rem; width: 2px; background: rgba(127,127,127,.25); }
.tf-path li:last-child::after { display: none; }
.tf-path code { font-size: .82rem; }

.tf-dot { display: inline-block; width: .6rem; height: .6rem; border-radius: 999px; margin-right: .45rem; }
.tf-dot.ok { background: #10b981; } .tf-dot.warn { background: #f59e0b; } .tf-dot.bad { background: #ef4444; }

div.stButton > button { border-radius: 12px; font-weight: 600; }
button[data-baseweb="tab"] { font-weight: 600; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)



def _version() -> tuple[int, int]:
    try:
        major, minor = st.__version__.split(".")[:2]
        return int(major), int(minor)
    except Exception:
        return (0, 0)


# Newer Streamlit replaced use_container_width with width="stretch".
STRETCH = {"width": "stretch"} if _version() >= (1, 50) else {"use_container_width": True}

def h(s: str) -> str:
    """Strip indentation so Markdown never treats the HTML as a code block."""
    return "\n".join(line.strip() for line in s.strip().splitlines() if line.strip())


def esc(x) -> str:
    return _html.escape(str(x))


def card(s: str) -> None:
    st.markdown(h(s), unsafe_allow_html=True)


SCENARIOS = {
    "INC-209": ("🧭", "Same alert, different cause",
                "The alert matches a past pool-exhaustion incident, but the pool is healthy and the database route is failing."),
    "INC-250": ("✅", "The familiar fix is right",
                "Same alert, and this time the connection pool really is saturated. Does the agent agree?"),
    "INC-301": ("❔", "No telemetry yet",
                "Nothing was measured. Can the agent admit it doesn't know instead of guessing?"),
    "INC-320": ("🛑", "Nothing applies",
                "Pool and route both look healthy, so no known fix fits. Will it escalate?"),
}

VERDICT = {
    "REUSE": ("#10b981", "Known fix applies"),
    "REJECT": ("#ef4444", "No known fix applies"),
    "INVESTIGATE": ("#f59e0b", "More evidence needed"),
}

STATUS_COLOR = {"met": "#c8f2d4", "contradicted": "#ffd0d0", "unknown": "#e6e6e6"}
STATUS_ICON = {"met": "✅", "contradicted": "❌", "unknown": "❔"}


@st.cache_resource
def get_store() -> GraphStore:
    return GraphStore()


def build_dot(incident_id: str, candidates: list[dict]) -> str:
    """Graphviz DOT built only from rows the validation query returned."""
    q = lambda s: str(s).replace('"', "'")
    lines = [
        "digraph G { rankdir=LR; bgcolor=transparent;",
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#888888", fillcolor="#ffffff"];',
        'edge [fontname="Helvetica", fontsize=9, color="#8a94b8", fontcolor="#a9b2d6"];',
        f'"{q(incident_id)}" [fillcolor="#dbe7ff", penwidth=2];',
    ]
    seen: set[str] = set()

    def add(line: str) -> None:
        if line not in seen:
            seen.add(line)
            lines.append(line)

    for c in candidates:
        sym = c["symptom"]
        add(f'"{q(sym)}" [shape=ellipse];')
        add(f'"{q(incident_id)}" -> "{q(sym)}" [label="HAS_SYMPTOM"];')
        for p in c["precedents"]:
            add(f'"{q(p)}" [fillcolor="#f3e8ff"];')
            add(f'"{q(p)}" -> "{q(sym)}" [label="HAS_SYMPTOM"];')
            add(f'"{q(p)}" -> "{q(c["fix_id"])}" [label="FIXED_BY"];')
        add(f'"{q(c["fix_id"])}" [label="{q(c["fix_name"])}", fillcolor="{STATUS_COLOR[c["status"]]}"];')
        for cond in c["conditions"]:
            add(f'"{q(cond["cond_id"])}" [label="{q(cond["cond_name"])}\\n({q(cond["metric_id"])} = {q(cond["required"])})", '
                f'fillcolor="{STATUS_COLOR[cond["status"]]}"];')
            add(f'"{q(c["fix_id"])}" -> "{q(cond["cond_id"])}" [label="REQUIRES"];')
            if cond["observed"] is None:
                nid = f"none-{incident_id}-{cond['metric_id']}"
                add(f'"{nid}" [label="no {q(cond["metric_id"])} observation", style="rounded,dashed"];')
                add(f'"{q(incident_id)}" -> "{nid}" [style=dashed, label="OBSERVED?"];')
            else:
                oid = cond["obs_id"] or f"obs-{cond['metric_id']}"
                add(f'"{q(oid)}" [label="observed: {q(cond["metric_id"])} = {q(cond["observed"])}", '
                    f'fillcolor="{STATUS_COLOR[cond["status"]]}"];')
                add(f'"{q(incident_id)}" -> "{q(oid)}" [label="OBSERVED"];')
                add(f'"{q(oid)}" -> "{q(cond["cond_id"])}" [label="{cond["status"].upper()}", style=bold];')
    lines.append("}")
    return "\n".join(lines)


def build_topology_dot(service_id: str, topology: dict) -> str:
    """Service dependency graph; failing service blue, suspect-change targets coloured by support."""
    q = lambda x: str(x).replace('"', "'")
    names, edges = {}, topology.get("edges") or []
    for e in edges:
        names[e["source"]], names[e["target"]] = e["source_name"], e["target_name"]
    suspect_color = {"corroborated": "#ffd0d0", "unknown": "#e6e6e6", "none": "#fff3c4", "contradicted": "#e6e6e6"}
    by_target = {x["target_id"]: x for x in topology.get("suspects", [])}
    lines = ["digraph G { rankdir=TB; bgcolor=transparent;",
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#888888", fillcolor="#ffffff"];',
             'edge [fontname="Helvetica", fontsize=9, color="#8a94b8", fontcolor="#a9b2d6"];']
    for sid, name in names.items():
        fill = "#dbe7ff" if sid == service_id else "#ffffff"
        extra = ", penwidth=2" if sid == service_id else ""
        if sid in by_target:
            fill = suspect_color[by_target[sid]["support"]] if sid != service_id else fill
        lines.append(f'"{q(sid)}" [label="{q(name)}", fillcolor="{fill}"{extra}];')
    for e in edges:
        lines.append(f'"{q(e["source"])}" -> "{q(e["target"])}" [label="CALLS"];')
    for x in topology.get("suspects", []):
        cid = x["change_id"]
        lines.append(f'"{q(cid)}" [label="{q(x["summary"])}\\n({x["hours_before"]}h before)", shape=note, fillcolor="{suspect_color[x["support"]]}"];')
        lines.append(f'"{q(cid)}" -> "{q(x["target_id"])}" [label="TOUCHED", style=dashed];')
    lines.append("}")
    return "\n".join(lines)


def section(title: str, sub: str | None = None) -> None:
    st.markdown(f'<div class="tf-section">{esc(title)}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="tf-sub">{sub}</div>', unsafe_allow_html=True)


def how_it_works() -> None:
    section("What this agent does",
            "TraceFix investigates incidents the way a careful engineer would: it checks the evidence "
            "before it repeats a fix that merely looks familiar.")
    steps = [
        ("1", "Read the incident", "Starts from the alert and the telemetry recorded for it, such as pool status and network route."),
        ("2", "Check past fixes", "Finds fixes that solved similar incidents, then tests each fix's prerequisites against this incident's telemetry in the graph."),
        ("3", "Trace recent changes", "Walks the service dependency graph to find which nearby change is actually backed by evidence."),
        ("4", "Decide and remember", "Gives a verdict with the path it followed, and saves the decision so recorded outcomes improve later answers."),
    ]
    for col, (n, title, text) in zip(st.columns(4, gap="medium"), steps):
        with col:
            card(f'<div class="tf-card"><div class="tf-num">{n}</div><h4>{title}</h4><p>{text}</p></div>')
    card('<div class="tf-note"><b>Why not just match similar incidents?</b> '
         'A similarity agent repeats the fix that looks familiar. TraceFix repeats it only when the '
         'evidence says the fix still applies.</div>')
    card('<span class="tf-guard">🔒 Recommends only. Never changes infrastructure.</span>'
         '<span class="tf-guard">❔ Says "unknown" instead of guessing.</span>'
         '<span class="tf-guard">🕸️ The verdict is computed from the graph, never by a language model.</span>')


for key, default in (("result", None), ("recorded", {}), ("pending", None), ("selected", None)):
    st.session_state.setdefault(key, default)


def pick(incident_id: str) -> None:
    st.session_state.pending = incident_id
    st.session_state.selected = incident_id


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### 🕸️ TraceFix")
    st.caption("Evidence before action")

    graph_ok, open_incidents = True, []
    try:
        open_incidents = get_store().list_open_incidents()
    except Exception:
        graph_ok = False

    if not graph_ok:
        card('<span class="tf-dot bad"></span>FalkorDB is not reachable')
        st.code("docker compose up -d", language="bash")
    elif not open_incidents:
        card('<span class="tf-dot warn"></span>Connected, graph is empty')
    else:
        card('<span class="tf-dot ok"></span>Connected to FalkorDB')

    if st.button("Reset & seed demo graph", **STRETCH, disabled=not graph_ok):
        try:
            get_store().reset_and_seed()
            st.session_state.update(result=None, recorded={}, pending=None, selected=None)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not seed graph: {exc}")

    st.divider()
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    agent_mode = st.toggle(
        "Agent mode", value=False, disabled=not has_key,
        help="Claude chooses which graph tools to call. The verdict is still computed from the graph.")
    st.caption("Claude picks the graph tools to call." if has_key else "Set ANTHROPIC_API_KEY to enable.")
    st.divider()
    st.caption("Synthetic demo data only. No production systems are connected. "
               "TraceFix only recommends and never changes infrastructure.")

# ------------------------------------------------------------------ run
if st.session_state.pending and graph_ok:
    iid = st.session_state.pending
    st.session_state.pending = None
    st.session_state.recorded.pop(iid, None)  # fresh run, fresh decision record
    try:
        runner = investigate_with_llm if agent_mode else investigate
        with st.spinner("Reading the graph..."):
            st.session_state.result = {"incident_id": iid, **runner(get_store(), iid)}
    except Exception as exc:
        st.session_state.result = None
        st.error(f"Investigation failed. Is FalkorDB running and the graph seeded? Details: {exc}")

result = st.session_state.result

# ------------------------------------------------------------------ hero
card("""
<div class="tf-hero">
<div class="tf-eyebrow">Graph Hacks · Track 01 · Agents that act on connected data</div>
<h1>TraceFix</h1>
<p class="tf-lead">An incident investigator that checks whether a past fix still applies, using a graph, before it recommends anything.</p>
<div><span class="tf-tag">FalkorDB</span><span class="tf-tag">Cypher</span><span class="tf-tag">Graph algorithms</span><span class="tf-tag">Explainable</span><span class="tf-tag">Read-only</span></div>
</div>
""")

if not graph_ok:
    card('<div class="tf-note"><b>Start the database first.</b> Run <code>docker compose up -d</code>, '
         'then reload this page.</div>')
    st.stop()
if not open_incidents:
    card('<div class="tf-note"><b>The graph is empty.</b> Click <b>Reset &amp; seed demo graph</b> in the sidebar to load '
         'the demo incidents.</div>')
    st.stop()

if result:
    with st.expander("How TraceFix works"):
        how_it_works()
else:
    how_it_works()

section("Try a scenario",
        "Four hand-built incidents with the same kind of alert. Pick one and watch how the agent reasons.")
for col, inc in zip(st.columns(min(4, len(open_incidents)), gap="medium"), open_incidents[:4]):
    iid = inc["id"]
    icon, name, desc = SCENARIOS.get(iid, ("🔹", inc["title"], ""))
    selected = st.session_state.selected == iid
    with col:
        cls = "tf-scn sel" if selected else "tf-scn"
        card(f'<div class="{cls}"><div class="tf-id">{esc(iid)}</div><h4>{icon} {esc(name)}</h4><p>{esc(desc)}</p></div>')
        st.button("Investigate again →" if selected else "Investigate →", key=f"go-{iid}", on_click=pick,
                  args=(iid,), **STRETCH, type="primary" if selected else "secondary")

# ------------------------------------------------------------------ result
if not result:
    card('<div class="tf-note">👆 Pick a scenario to see the baseline and TraceFix reason about the same incident.</div>')
else:
    inc, decision, baseline = result["incident"], result["decision"], result["baseline"]
    topo = result.get("topology") or {}
    top = baseline[0] if baseline else None
    b_fix = top["fix_id"] if top else None
    t_fix = decision["recommended_fix_id"]

    section(f"{inc['id']} · {inc['title']}")
    st.markdown(f'<div class="tf-sub">Alert <code>{esc(inc["description"])}</code> on <b>{esc(inc["service"])}</b></div>',
                unsafe_allow_html=True)

    color, label = VERDICT[decision["verdict"]]
    card(f"""
    <div class="tf-verdict" style="--c:{color}">
    <div class="tf-vlabel">{esc(decision['verdict'])} · {label}</div>
    <div class="tf-vtitle">{esc(decision['title'])}</div>
    <p>{esc(decision['reason'])}</p>
    <div class="tf-action"><span>Recommended next step</span><b>{esc(decision['recommended_action'])}</b></div>
    <div class="tf-caveat">{esc(decision['caveat'])}</div>
    </div>
    """)

    st.markdown("&nbsp;", unsafe_allow_html=True)
    left, right = st.columns(2, gap="medium")
    with left:
        if top:
            card(f"""
            <div class="tf-cmp base"><div class="tf-eyebrow">Similarity baseline</div>
            <div class="tf-big">{esc(top['fix_name'])}</div>
            <p>Closest past incident <b>{esc(top['incident_id'])}</b> ({top['score']:.0%} similar). It sees matching
            text, not whether the fix's conditions hold.</p></div>
            """)
    with right:
        mine = decision["recommended_action"] if t_fix else "No fix recommended yet"
        why = ("Every prerequisite of this fix is confirmed by the incident's telemetry." if t_fix
               else "No fix has all of its prerequisites confirmed by telemetry.")
        card(f"""
        <div class="tf-cmp mine"><div class="tf-eyebrow">TraceFix · graph validation</div>
        <div class="tf-big">{esc(mine)}</div><p>{why}</p></div>
        """)

    if b_fix != t_fix:
        outcome = f"recommends <b>{esc(decision['recommended_action'])}</b>" if t_fix else "<b>withholds action</b>"
        card(f"""<div class="tf-banner bad">They disagree. The baseline would apply
        <b>{esc(top['fix_name'] if top else 'nothing')}</b>; TraceFix {outcome}.</div>""")
    else:
        card('<div class="tf-banner good">They agree here. The familiar fix is backed by the evidence.</div>')

    section("How it got there",
            "The exact relationships the agent followed. Each step is an edge returned by FalkorDB.")
    items = "".join(f"<li><code>{esc(s)}</code></li>" for s in decision["path"])
    card(f'<ol class="tf-path">{items}</ol>')

    st.markdown("&nbsp;", unsafe_allow_html=True)
    tabs = st.tabs(["Fix validation", "Topology & changes", "Evidence", "Agent steps"])

    with tabs[0]:
        st.caption("Green = prerequisite met · red = contradicted by telemetry · grey = unknown. "
                   "Every node and edge was returned by the Cypher validation query.")
        if decision["candidates"]:
            st.graphviz_chart(build_dot(inc["id"], decision["candidates"]), **STRETCH)
            for cand in decision["candidates"]:
                with st.expander(f"{STATUS_ICON[cand['status']]} {cand['fix_name']}  ({cand['status']})"):
                    st.caption(f"Precedent outcome: {cand['outcome_note']}")
                    for step in decision["paths"][cand["fix_id"]]:
                        st.markdown(f"- `{step}`")
        else:
            st.info("No resolved incident shares this symptom, so there is nothing to validate.")

    with tabs[1]:
        st.caption("Graph algorithms over the service dependency graph: Cypher shortestPath, algo.bfs, "
                   "algo.pageRank, and a variable-length blast-radius match.")
        if topo.get("errors"):
            st.warning("Some graph algorithms failed: " + " | ".join(topo["errors"]))
        if topo.get("edges"):
            st.graphviz_chart(build_topology_dot(topo["service_id"], topo), **STRETCH)
            st.caption("Blue = affected service · red = change corroborated by telemetry · "
                       "yellow = change with no telemetry link.")
        if topo.get("suspects"):
            st.markdown("**Recent changes in the dependency chain**")
            st.dataframe(
                [{"Change": x["summary"], "Hours before": x["hours_before"], "Hops": x["hops"],
                  "Path": " → ".join(x["path_names"]),
                  "Evidence": (f"{x['metric_id']} = {x['observed']} (needs {x['required']})"
                               if x["support"] == "corroborated" else
                               {"unknown": "telemetry missing", "none": "no telemetry link",
                                "contradicted": "contradicted"}[x["support"]])}
                 for x in topo["suspects"]],
                **STRETCH, hide_index=True)
        elif not topo.get("errors"):
            st.info("No recent change touched this service's dependency chain.")
        c1, c2 = st.columns(2)
        with c1:
            if topo.get("blast_radius"):
                st.markdown("**Blast radius of the likely trigger**")
                st.write(", ".join(b["name"] for b in topo["blast_radius"]))
            if topo.get("closure"):
                st.markdown("**Dependency closure (algo.bfs)**")
                st.write(", ".join(topo["closure"]))
        with c2:
            if topo.get("criticality"):
                st.markdown("**Most depended-on services (algo.pageRank)**")
                st.bar_chart({c["name"]: c["score"] for c in topo["criticality"]})

    with tabs[2]:
        st.caption("Each precedent fix, the telemetry it needs, and what was actually observed.")
        for line in decision["evidence"]:
            st.markdown(f"- {line}")

    with tabs[3]:
        if result.get("tool_trace") is None:
            st.info("Agent mode is off. Turn it on in the sidebar (needs ANTHROPIC_API_KEY) to watch Claude "
                    "choose graph tools step by step. The verdict stays graph-computed either way.")
        else:
            if not result["validated"]:
                st.warning("The agent never validated a fix's prerequisites. Treat its narrative with caution; "
                           "the verdict above comes from the graph.")
            st.write(result["narrative"])
            for i, t in enumerate(result["tool_trace"], 1):
                st.markdown(f"`{i:02}` **{t['tool']}** `{t['input']}`")
                st.json(t["output"], expanded=False)

    # ---- write the decision back to the graph and close the loop -------------
    section("Remember this decision",
            "Write the decision and its evidence into the graph. Recording an outcome changes what the agent "
            "does next time.")
    recorded = st.session_state.setdefault("recorded", {})
    iid = result["incident_id"]
    entry = recorded.get(iid)

    if not entry:
        if st.button("Record this decision in the graph", type="primary"):
            try:
                recorded[iid] = {"id": get_store().record_decision(iid, decision), "outcome": None}
                st.rerun()
            except Exception as exc:
                st.error(f"Could not record decision: {exc}")
    else:
        st.success(f"Recorded as `{entry['id']}`, linked to the incident, the fixes it recommended or "
                   "rejected, the observations it relied on, and the change it cited.")
        if decision["recommended_fix_id"] and entry["outcome"] is None:
            st.write("After a human applies the recommendation, record what happened:")
            b1, b2 = st.columns(2)
            for col, worked, btn in ((b1, True, "✅ Fix worked"), (b2, False, "❌ Fix did not work")):
                if col.button(btn, **STRETCH):
                    try:
                        out = get_store().record_outcome(entry["id"], worked)
                        entry["outcome"] = (worked, out)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not record outcome: {exc}")
        elif entry["outcome"]:
            worked, out = entry["outcome"]
            if worked:
                st.success(f"Outcome recorded. {iid} is now linked to **{out.get('fix_name')}** as a resolved "
                           "precedent, so future incidents with the same symptom can reuse it.")
            else:
                st.warning(f"Outcome recorded. **{out.get('fix_name')}** is marked as failed for {iid}. "
                           "Click **Investigate again** above to see the agent change its answer.")
        elif not decision["recommended_fix_id"]:
            st.info("No fix was recommended, so there is no outcome to record for this decision.")

    with st.expander("Decision log (from the graph)"):
        try:
            log = get_store().list_decisions()
            if log:
                st.dataframe(log, **STRETCH, hide_index=True)
            else:
                st.caption("No decisions recorded yet.")
        except Exception as exc:
            st.caption(f"Decision log unavailable: {exc}")

with st.expander("Scripted scenario scoreboard (synthetic data)"):
    try:
        rows = run_scoreboard(get_store())
        for r in rows:
            r["baseline"] = f"{'✅' if r.pop('baseline_ok') else '❌'} {r['baseline']}"
            r["tracefix"] = f"{'✅' if r.pop('tracefix_ok') else '❌'} {r['tracefix']}"
        st.dataframe(rows, **STRETCH, hide_index=True)
        st.caption("Four hand-built scenarios, not a benchmark. They show where graph validation and text "
                   "similarity diverge.")
    except Exception as exc:
        st.info(f"Scoreboard unavailable: {exc}")

st.caption("Hackathon prototype · Track 01: Agents That Act on Connected Data · Synthetic incident data · "
           "No automated production changes")