
"use client";

import {
  AlertTriangle,
  Bot,
  ChevronDown,
  RefreshCw,
  Sparkles,
} from "lucide-react";

export type DashboardIncident = {
  id: string;
  title?: string;
  description?: string;
  service?: string;
  service_id?: string;
  observations?: unknown[];
};

type IncidentSelectorProps = {
  incidents: DashboardIncident[];
  selected: string;
  selectedIncident?: DashboardIncident;
  investigatedIncident?: DashboardIncident;
  agentMode: boolean;
  loading: boolean;
  onSelect: (incidentId: string) => void;
  onToggleAgentMode: () => void;
  onInvestigate: () => void;
};

export default function IncidentSelector({
  incidents,
  selected,
  selectedIncident,
  investigatedIncident,
  agentMode,
  loading,
  onSelect,
  onToggleAgentMode,
  onInvestigate,
}: IncidentSelectorProps) {
  const displayedIncident = investigatedIncident ?? selectedIncident;

  return (
    <section id="incident-workspace" className="scroll-mt-6 py-4">
      <div className="tracefix-panel overflow-hidden">
        <div className="flex flex-col gap-5 p-4 lg:flex-row lg:items-center lg:justify-between lg:p-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.12em] text-slate-300">
                <AlertTriangle size={11} />
                Active incident
              </span>

              <span className="font-mono text-xs text-slate-400">
                {selected || "Loading incidents"}
              </span>
            </div>

            <h2 className="mt-3 text-xl font-semibold tracking-tight text-white">
              {displayedIncident?.title ?? "Select an incident to begin"}
            </h2>

            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
              {displayedIncident?.description ??
                "Trace connected services, historical remedies, and observed telemetry in one investigation."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="relative">
              <span className="sr-only">Select incident</span>

              <select
                value={selected}
                onChange={(event) => onSelect(event.target.value)}
                className="h-10 max-w-[280px] appearance-none rounded-xl border border-white/10 bg-[#171717] py-2 pl-3 pr-9 text-xs text-slate-200 outline-none transition focus:border-white/30"
              >
                {!incidents.length && (
                  <option value="">Loading incidents…</option>
                )}

                {incidents.map((incident) => (
                  <option key={incident.id} value={incident.id}>
                    {incident.id} — {incident.title ?? "Untitled incident"}
                  </option>
                ))}
              </select>

              <ChevronDown
                className="pointer-events-none absolute right-3 top-3 text-slate-500"
                size={14}
              />
            </label>

            <button
              type="button"
              onClick={onToggleAgentMode}
              aria-pressed={agentMode}
              className={`inline-flex h-10 items-center gap-2 rounded-xl border px-3 text-xs font-medium transition ${
                agentMode
                  ? "border-cyan-300/30 bg-cyan-300/[.10] text-cyan-100 shadow-[0_0_24px_rgba(34,211,238,.06)]"
                  : "border-white/10 bg-white/[.02] text-slate-400 hover:text-white"
              }`}
            >
              <Bot size={14} />
              {agentMode ? "AI Agent" : "Graph-only"}
              <span className="hidden text-[10px] opacity-60 sm:inline">MODE</span>
            </button>

            <button
              type="button"
              onClick={onInvestigate}
              disabled={loading || !selected}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-white/15 bg-[#f0eee9] px-4 text-sm font-semibold text-[#151515] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <RefreshCw className="animate-spin" size={15} />
              ) : (
                <Sparkles size={15} />
              )}
              {loading ? "Investigating…" : "Investigate"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
