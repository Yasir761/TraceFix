
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Toaster, toast } from "sonner";
import DependencyGraph from "./components/DependencyGraph";
import {
  CommandPalette,
  ServiceInspector,
} from "./components/AgentWorkspace";
import AppHeader from "./components/layout/AppHeader";
import HeroSection from "./components/layout/HeroSection";
import IncidentSelector from "./components/dashboard/IncidentSelector";
import MetricsGrid from "./components/dashboard/MetricsGrid";
import RecommendationCard from "./components/dashboard/RecommendationCard";
import DecisionMemory from "./components/dashboard/DecisionMemory";
import EvidenceSection from "./components/evidence/EvidenceSection";
import AgentRunPanel from "./components/dashboard/AgentRunPanel";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Copy,
  Network,
  Terminal,
  ShieldCheck,
} from "lucide-react";

const API = "http://localhost:8000";

type Data = Record<string, unknown>;

type Incident = {
  id: string;
  title?: string;
  description?: string;
  service?: string;
  service_id?: string;
  observations?: unknown[];
};

type Decision = {
  verdict?: string;
  title?: string;
  reason?: string;
  recommended_action?: string;
  caveat?: string;
  recommended_fix_id?: string | null;
  evidence?: unknown[];
  [key: string]: unknown;
};

type Investigation = {
  incident?: Incident;
  decision?: Decision;
  baseline?: Data[];
  narrative?: string;
  tool_trace?: Data[];
  validated?: boolean;
  mode?: "agent" | "graph";
  topology?: {
    edges?: unknown[];
    suspects?: unknown[];
    trigger?: unknown;
    errors?: unknown[];
    [key: string]: unknown;
  };
};

type StoredDecision = {
  decision_id?: string;
  id?: string;
  incident_id?: string;
  verdict?: string;
  worked?: boolean | null;
  recommended_fix_id?: string;
  [key: string]: unknown;
};

const text = (value: unknown, fallback = "Not available") =>
  typeof value === "string" || typeof value === "number"
    ? String(value)
    : fallback;

function Panel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`tracefix-panel min-w-0 ${className}`}>
      {children}
    </section>
  );
}

function Pill({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "slate" | "cyan" | "amber" | "green" | "rose";
}) {
  const tones = {
    slate: "border-white/[.09] bg-white/[.03] text-slate-400",
    cyan: "border-cyan-300/20 bg-cyan-300/[.07] text-cyan-200",
    amber: "border-amber-300/20 bg-amber-300/[.07] text-amber-200",
    green: "border-emerald-300/20 bg-emerald-300/[.07] text-emerald-200",
    rose: "border-rose-300/20 bg-rose-300/[.07] text-rose-200",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.12em] ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function Empty({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="flex min-h-[250px] flex-col items-center justify-center rounded-xl border border-dashed border-white/[.11] bg-[#090e16] px-6 text-center">
      <Network className="text-slate-500" size={24} />
      <p className="mt-4 text-sm font-semibold text-slate-200">{title}</p>
      <p className="mt-2 max-w-sm text-xs leading-5 text-slate-500">{detail}</p>
    </div>
  );
}

export default function Home() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState<Investigation | null>(null);
  const [decisions, setDecisions] = useState<StoredDecision[]>([]);
  const [apiStatus, setApiStatus] = useState<
    "checking" | "online" | "offline"
  >("checking");
  const [graphStatus, setGraphStatus] = useState<
    "checking" | "online" | "offline"
  >("checking");
  const [agentMode, setAgentMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState<string>();
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadWorkspace = useCallback(async () => {
    setApiStatus("checking");
    setGraphStatus("checking");

    try {
      const [
        healthResponse,
        incidentsResponse,
        decisionsResponse,
      ] = await Promise.all([
        fetch(`${API}/api/health`),
        fetch(`${API}/api/incidents`),
        fetch(`${API}/api/decisions`),
      ]);

      if (!healthResponse.ok || !incidentsResponse.ok) {
        throw new Error("The TraceFix API is unavailable.");
      }

      const health = await healthResponse.json();
      const incidentData = await incidentsResponse.json();
      const decisionData = decisionsResponse.ok
        ? await decisionsResponse.json()
        : { decisions: [] };

      const items: Incident[] = Array.isArray(incidentData)
        ? incidentData
        : incidentData.incidents ?? [];

      setIncidents(items);
      setDecisions(
        Array.isArray(decisionData.decisions)
          ? decisionData.decisions
          : [],
      );

      setSelected((current) =>
        current && items.some((item) => item.id === current)
          ? current
          : (items[0]?.id ?? ""),
      );

      setApiStatus("online");
      setGraphStatus(
        health.graph === "connected" ? "online" : "offline",
      );
      setError("");
    } catch (err) {
      setApiStatus("offline");
      setGraphStatus("offline");
      setError(
        err instanceof Error
          ? err.message
          : "Cannot reach the Python API on port 8000.",
      );
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadWorkspace(), 0);
    return () => window.clearTimeout(timer);
  }, [loadWorkspace]);

  const investigate = async () => {
    if (!selected) return;

    setLoading(true);
    setError("");
    setSelectedNode(undefined);

    try {
      const response = await fetch(`${API}/api/investigate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          incident_id: selected,
          agent_mode: agentMode,
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail ?? `Investigation failed (${response.status})`,
        );
      }

      setResult({ ...payload, mode: agentMode ? "agent" : "graph" });
      setApiStatus("online");

      toast.success("Investigation complete", {
        description: `Evidence loaded for ${selected}.`,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Investigation failed.";

      setError(message);
      toast.error("Investigation failed", { description: message });
    } finally {
      setLoading(false);
    }
  };

  const recordDecision = async () => {
    if (!selected) return;

    setRecording(true);

    try {
      const response = await fetch(`${API}/api/decisions/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          incident_id: selected,
          agent_mode: result?.mode === "agent" || (!result && agentMode),
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail ?? "Could not record decision.");
      }

      toast.success("Decision added to graph memory", {
        description: `${payload.decision_id} is ready for future investigations.`,
      });

      await loadWorkspace();
    } catch (err) {
      toast.error("Could not record decision", {
        description: err instanceof Error ? err.message : "Try again.",
      });
    } finally {
      setRecording(false);
    }
  };

  const updateOutcome = async (decisionId: string, worked: boolean) => {
    try {
      const response = await fetch(
        `${API}/api/decisions/${encodeURIComponent(decisionId)}/outcome`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ worked }),
        },
      );

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail ?? "Could not update outcome.");
      }

      toast.success(
        worked ? "Outcome marked resolved" : "Outcome marked unsuccessful",
      );

      await loadWorkspace();
    } catch (err) {
      toast.error("Could not update outcome", {
        description: err instanceof Error ? err.message : "Try again.",
      });
    }
  };

  const decision = result?.decision;
  const topology = result?.topology ?? {};
  const baseline = result?.baseline ?? [];
  const observations = result?.incident?.observations ?? [];

  const graphEdges = (topology.edges ?? []).filter(
    (edge): edge is Data => typeof edge === "object" && edge !== null,
  );

  const trigger = topology.trigger as Data | undefined;
  const affected = result?.incident?.service_id ?? result?.incident?.service;

  const suspect =
    typeof trigger?.target_id === "string"
      ? trigger.target_id
      : undefined;

  const selectedIncident = incidents.find(
    (item) => item.id === selected,
  );

  const nodeSummary = useMemo(
    () =>
      graphEdges
        .flatMap((edge) => [
          [
            String(edge.source_id ?? edge.source ?? ""),
            String(edge.source_name ?? edge.source ?? ""),
          ],
          [
            String(edge.target_id ?? edge.target ?? ""),
            String(edge.target_name ?? edge.target ?? ""),
          ],
        ])
        .find(([id]) => id === selectedNode),
    [graphEdges, selectedNode],
  );

  const verdict = text(decision?.verdict, "Awaiting analysis");

  const path = graphEdges.length
    ? graphEdges
        .slice(0, 3)
        .map((edge) =>
          text(edge.source_name ?? edge.source_id, "Service"),
        )
        .concat(
          text(
            graphEdges[Math.min(graphEdges.length - 1, 2)].target_name ??
              graphEdges[Math.min(graphEdges.length - 1, 2)].target_id,
            "Service",
          ),
        )
        .filter(
          (name, index, values) =>
            index === 0 || values[index - 1] !== name,
        )
        .join("  →  ")
    : "No dependency path returned";

  const copyPayload = async () => {
    if (!result) return;

    try {
      await navigator.clipboard.writeText(
        JSON.stringify(result, null, 2),
      );
      setCopied(true);
      toast.success("Payload copied");
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy payload", {
        description: "Check browser clipboard permissions.",
      });
    }
  };

  return (
    <main className="min-h-screen bg-[#090e16] text-slate-200">
      <Toaster theme="dark" position="top-right" richColors />

      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_15%_0%,rgba(6,182,212,.08),transparent_34%),radial-gradient(ellipse_at_85%_30%,rgba(30,64,175,.08),transparent_30%)]" />

      <div className="relative mx-auto max-w-[1680px] px-4 pb-9 sm:px-6 lg:px-8">
        <AppHeader
          apiStatus={apiStatus}
          graphStatus={graphStatus}
          onRefresh={() => void loadWorkspace()}
        />

        <HeroSection />

        {/* Active incident */}
        <IncidentSelector
          incidents={incidents}
          selected={selected}
          selectedIncident={selectedIncident}
          investigatedIncident={result?.incident}
          agentMode={agentMode}
          loading={loading}
          onSelect={(incidentId) => {
            setSelected(incidentId);
            setResult(null);
            setError("");
          }}
          onToggleAgentMode={() => setAgentMode((value) => !value)}
          onInvestigate={() => void investigate()}
        />

        {error && (
          <div
            role="alert"
            className="mb-5 flex items-start gap-3 rounded-xl border border-amber-300/20 bg-amber-300/[.07] p-4 text-sm text-amber-100"
          >
            <AlertTriangle
              className="mt-0.5 shrink-0 text-amber-300"
              size={17}
            />
            <div>
              <b>Connection needs attention.</b>
              <p className="mt-1 text-amber-100/70">{error}</p>
              <button
                type="button"
                onClick={() => void loadWorkspace()}
                className="mt-2 text-xs font-semibold text-amber-200 underline underline-offset-4"
              >
                Retry connection
              </button>
            </div>
          </div>
        )}

        {/* Investigation metrics */}
        <MetricsGrid
          hasResult={Boolean(result)}
          servicesCount={
            result
              ? String(
                  new Set(
                    graphEdges.flatMap((edge) => [
                      edge.source_id ?? edge.source,
                      edge.target_id ?? edge.target,
                    ]),
                  ).size,
                )
              : "—"
          }
          rootCause={
            result
              ? text(
                  trigger?.target_name ?? trigger?.target_id,
                  "Not identified",
                )
              : "—"
          }
          relationshipCount={result ? String(graphEdges.length) : "—"}
          historicalMatches={result ? String(baseline.length) : "—"}
        />

        {result && (
          <section className="mb-5 overflow-hidden rounded-2xl border border-cyan-300/20 bg-[#101923]">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[.07] px-4 py-3 sm:px-5">
              <div className="flex items-center gap-2">
                <span className="grid size-7 place-items-center rounded-lg bg-cyan-300/10 text-cyan-200"><ShieldCheck size={15} /></span>
                <div>
                  <p className="text-sm font-semibold text-white">Investigation conclusion</p>
                  <p className="text-[11px] text-slate-500">{result.incident?.id ?? selected} · {result.mode === "agent" ? "AI Agent + graph evidence" : "Graph-only analysis"}</p>
                </div>
              </div>
              <Pill tone={String(decision?.verdict ?? "").toUpperCase() === "REJECT" ? "rose" : "cyan"}>{verdict}</Pill>
            </div>
            <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_minmax(280px,.72fr)]">
              <div className="p-4 sm:p-5">
                <p className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-500">Likely cause / trigger</p>
                <h2 className="mt-2 text-lg font-semibold leading-7 text-white">{text(trigger?.summary ?? trigger?.description ?? trigger?.target_name ?? trigger?.target_id, "No likely trigger was returned")}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">{text(decision?.reason, "The backend did not return a separate explanation for this verdict. Review the evidence below before acting.")}</p>
                {decision?.caveat && <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-300/20 bg-amber-300/[.06] p-3 text-xs leading-5 text-amber-100/90"><AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-300" /><span>{text(decision.caveat)}</span></div>}
              </div>
              <div className="border-t border-white/[.07] bg-black/10 p-4 sm:p-5 lg:border-l lg:border-t-0">
                <p className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-500">Recommended next action</p>
                <p className="mt-2 text-base font-semibold leading-6 text-cyan-50">{text(decision?.recommended_action, "No recommended action was returned")}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Pill tone={result.validated === true ? "green" : result.validated === false ? "amber" : "slate"}>{result.validated === true ? "Prerequisites validated" : result.validated === false ? "Prerequisite validation incomplete" : "Validation status not returned"}</Pill>
                  <Pill tone="slate">{baseline.length} historical {baseline.length === 1 ? "match" : "matches"}</Pill>
                </div>
              </div>
            </div>
          </section>
        )}

        {result && (
          <section className="mb-5 rounded-2xl border border-white/[.08] bg-[#101720] p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div><p className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-500">Reasoning path</p><h2 className="mt-1 text-sm font-semibold text-white">How TraceFix reached this recommendation</h2></div>
              <span className="text-[11px] text-slate-500">Only returned investigation data is shown</span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {[
                { n: "01", title: "Signal", value: observations.length ? `${observations.length} observation${observations.length === 1 ? "" : "s"} returned` : "", detail: observations.length ? "Reported incident telemetry" : "" },
                { n: "02", title: "Connection", value: graphEdges.length ? `${graphEdges.length} service relationship${graphEdges.length === 1 ? "" : "s"}` : "", detail: graphEdges.length ? "Dependency topology" : "" },
                { n: "03", title: "Trigger", value: trigger ? text(trigger.target_name ?? trigger.target_id ?? trigger.summary, "Trigger identified") : "", detail: trigger ? "Candidate cause from topology" : "" },
                { n: "04", title: "Validation", value: typeof result.validated === "boolean" ? (result.validated ? "Prerequisites validated" : "Validation not satisfied") : "", detail: typeof result.validated === "boolean" ? "Backend validation result" : "" },
                { n: "05", title: "Action", value: text(decision?.recommended_action, ""), detail: decision?.recommended_action ? "Proposed next step" : "" },
              ].filter((step) => Boolean(step.value)).map((step) => (
                <div key={step.n} className="min-w-0 rounded-xl border border-white/[.07] bg-white/[.02] p-3">
                  <div className="flex items-center gap-2"><span className="font-mono text-[10px] text-cyan-200">{step.n}</span><span className="text-xs font-semibold text-slate-200">{step.title}</span></div>
                  <p className="mt-2 break-words text-xs font-medium leading-5 text-slate-100">{step.value}</p><p className="mt-1 text-[10px] leading-4 text-slate-500">{step.detail}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {result && (
          <AgentRunPanel
            mode={result.mode ?? (agentMode ? "agent" : "graph")}
            narrative={result.narrative}
            toolTrace={result.tool_trace ?? []}
            validated={Boolean(result.validated)}
          />
        )}

        {/* Graph and recommendation */}
        <section className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,0.85fr)]">
          <Panel className="p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="tracefix-eyebrow">Connected context</div>
                <h2 className="mt-1 text-lg font-semibold text-white">
                  Service dependency graph
                </h2>
                <p className="mt-1 max-w-xl text-xs leading-5 text-slate-500">
                  Explore the relationships connecting the affected service
                  to the suspected trigger.
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Pill tone="rose">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-300" />
                  Affected
                </Pill>
                <Pill tone="amber">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-300" />
                  Suspect
                </Pill>
              </div>
            </div>

            <div className="mt-4">
              {result ? (
                <DependencyGraph
                  edges={graphEdges}
                  affectedServiceId={affected}
                  suspectTargetId={suspect}
                  selectedNodeId={selectedNode}
                  onNodeSelect={(nodeId) => {
                    setSelectedNode(nodeId);
                    setInspectorOpen(Boolean(nodeId));
                  }}
                />
              ) : (
                <Empty
                  title="Your dependency graph is waiting"
                  detail="Choose an incident and select Investigate to load the real service relationships returned by TraceFix."
                />
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/[.07] bg-black/15 px-3 py-3 text-xs">
              <span className="break-words font-mono leading-5 text-cyan-100/80">
                {path}
              </span>

              {selectedNode && (
                <button
                  type="button"
                  onClick={() => setInspectorOpen(true)}
                  className="shrink-0 text-slate-400 transition hover:text-cyan-200"
                >
                  Inspect:{" "}
                  <b className="text-slate-200">
                    {nodeSummary?.[1] || selectedNode}
                  </b>
                </button>
              )}
            </div>
          </Panel>

          <div className="space-y-5">
            <RecommendationCard
              title={decision?.title ?? verdict}
              verdict={verdict}
              reason={text(decision?.reason)}
              recommendedAction={text(decision?.recommended_action)}
              caveat={decision?.caveat}
              recording={recording}
              hasResult={Boolean(result)}
              onRecordDecision={() => void recordDecision()}
            />

            <DecisionMemory
              decisions={decisions}
              onUpdateOutcome={(decisionId, worked) =>
                void updateOutcome(decisionId, worked)
              }
            />
          </div>
        </section>

        {/* Evidence */}
        {result && (
          <EvidenceSection
            decision={decision as Data | undefined}
            topology={{ ...topology, observations } as Data}
            baseline={baseline}
          />
        )}

        {/* Detailed evidence stays available below the primary recommendation. */}

        {/* Developer information stays collapsed */}
        {result && (
          <details className="group mt-5 rounded-2xl border border-white/[.08] bg-[#101823]">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-medium text-slate-300">
              <span className="flex items-center gap-3">
                <Terminal size={16} className="text-slate-500" />
                Developer payload
                <span className="text-xs font-normal text-slate-500">
                  Raw investigation JSON
                </span>
              </span>

              <ChevronDown
                size={16}
                className="text-slate-500 transition group-open:rotate-180"
              />
            </summary>

            <div className="border-t border-white/[.07] p-4">
              <div className="mb-3 flex justify-end">
                <button
                  type="button"
                  onClick={() => void copyPayload()}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/[.1] px-3 py-2 text-xs text-slate-300 transition hover:bg-white/[.05]"
                >
                  {copied ? (
                    <CheckCircle2 size={13} />
                  ) : (
                    <Copy size={13} />
                  )}
                  {copied ? "Copied" : "Copy JSON"}
                </button>
              </div>

              <pre className="max-h-[420px] overflow-auto rounded-xl border border-white/[.06] bg-[#080c13] p-4 text-xs leading-6 text-cyan-100/80">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          </details>
        )}

        <footer className="flex flex-wrap items-center justify-between gap-3 py-7 text-[10px] font-medium uppercase tracking-[.12em] text-slate-600">
          <span>TraceFix · Explainable incident investigation</span>
          <span className="flex items-center gap-2">
            <Clock3 size={12} />
            Local development
          </span>
        </footer>



        <ServiceInspector
          open={inspectorOpen}
          onOpenChange={setInspectorOpen}
          nodeId={selectedNode}
          nodeName={nodeSummary?.[1]}
          edges={graphEdges}
        />

        <CommandPalette
          open={commandOpen}
          onOpenChange={setCommandOpen}
          incidents={incidents}
          onSelectIncident={(incidentId) => {
            setSelected(incidentId);
            setResult(null);
            setError("");
          }}
          onInvestigate={() => void investigate()}
          canInvestigate={Boolean(selected) && !loading}
        />
      </div>
    </main>
  );
}
