"use client";

import { useState } from "react";
import {
  Bot,
  CheckCircle2,
  ChevronDown,
  Circle,
  GitBranch,
  Search,
  ShieldCheck,
  Wrench,
} from "lucide-react";

type TraceItem = {
  tool?: string;
  input?: Record<string, unknown>;
  output?: unknown;
};

const descriptions: Record<string, string> = {
  get_incident: "Read incident details and telemetry",
  find_precedent_fixes: "Retrieved historical fixes",
  check_prerequisites: "Checked a candidate fix against telemetry",
  trace_recent_changes: "Traced recent changes through dependencies",
  blast_radius: "Checked downstream service impact",
};

function pretty(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function AgentRunPanel({
  mode,
  narrative,
  toolTrace,
  validated,
}: {
  mode: "agent" | "graph";
  narrative?: string;
  toolTrace: TraceItem[];
  validated: boolean;
}) {
  const [showTrace, setShowTrace] = useState(false);
  const isAgent = mode === "agent";

  return (
    <section className={`mb-5 overflow-hidden rounded-2xl border ${
      isAgent
        ? "border-cyan-300/20 bg-[linear-gradient(115deg,rgba(8,145,178,.10),rgba(15,23,42,.72)_52%,rgba(15,23,42,.92))]"
        : "border-white/[.09] bg-[#111720]"
    }`}>
      <div className="flex flex-col gap-4 p-4 sm:p-5 md:flex-row md:items-start">
        <div className={`grid size-11 shrink-0 place-items-center rounded-xl border ${
          isAgent
            ? "border-cyan-300/20 bg-cyan-300/[.08] text-cyan-200"
            : "border-white/10 bg-white/[.04] text-slate-300"
        }`}>
          {isAgent ? <Bot size={21} /> : <GitBranch size={21} />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-white">
              {isAgent ? "AI agent investigation" : "Graph analysis"}
            </p>
            <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[.12em] ${
              isAgent
                ? "border-cyan-300/20 bg-cyan-300/[.07] text-cyan-200"
                : "border-white/10 bg-white/[.04] text-slate-300"
            }`}>
              {isAgent ? "Gemini + graph tools" : "Deterministic"}
            </span>
            {isAgent && (
              <span className={`inline-flex items-center gap-1 text-[10px] ${
                validated ? "text-emerald-300" : "text-amber-200"
              }`}>
                {validated ? <CheckCircle2 size={12} /> : <Circle size={12} />}
                {validated ? "Prerequisites checked" : "No prerequisite check recorded"}
              </span>
            )}
          </div>

          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">
            {isAgent
              ? "Gemini selected investigation tools and produced an explanation. TraceFix independently computes the final verdict from graph evidence."
              : "TraceFix evaluates fix prerequisites, historical precedent, and graph topology without running the LLM tool-calling loop."}
          </p>

          {isAgent && (
            <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: "Tools executed", value: String(toolTrace.length), icon: <Wrench size={14} /> },
                { label: "Incident context", value: toolTrace.some((x) => x.tool === "get_incident") ? "Read" : "Not recorded", icon: <Search size={14} /> },
                { label: "Recent changes", value: toolTrace.some((x) => x.tool === "trace_recent_changes") ? "Traced" : "Not recorded", icon: <GitBranch size={14} /> },
                { label: "Verdict authority", value: "Graph engine", icon: <ShieldCheck size={14} /> },
              ].map((item) => (
                <div key={item.label} className="rounded-xl border border-white/[.07] bg-black/20 px-3 py-2.5">
                  <div className="flex items-center gap-2 text-[10px] text-slate-500">{item.icon}{item.label}</div>
                  <p className="mt-1 text-xs font-semibold text-slate-200">{item.value}</p>
                </div>
              ))}
            </div>
          )}

          {isAgent && narrative && (
            <div className="mt-4 rounded-xl border border-cyan-300/10 bg-black/20 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[.13em] text-cyan-200/80">Agent explanation</p>
              <p className="mt-2 text-sm leading-6 text-slate-200">{narrative}</p>
            </div>
          )}

          {isAgent && (
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setShowTrace((value) => !value)}
                className="inline-flex items-center gap-2 text-xs font-medium text-cyan-100/80 transition hover:text-white"
                aria-expanded={showTrace}
              >
                <Wrench size={13} />
                {showTrace ? "Hide tool execution" : "Inspect tool execution"}
                <span className="text-slate-500">({toolTrace.length})</span>
                <ChevronDown size={13} className={`transition ${showTrace ? "rotate-180" : ""}`} />
              </button>

              {showTrace && (
                <div className="mt-3 space-y-2">
                  {toolTrace.length === 0 ? (
                    <p className="rounded-lg border border-white/[.07] p-3 text-xs text-slate-400">
                      No tool calls were returned for this run.
                    </p>
                  ) : toolTrace.map((item, index) => (
                    <details key={`${item.tool ?? "tool"}-${index}`} className="rounded-xl border border-white/[.08] bg-black/20">
                      <summary className="flex cursor-pointer list-none items-start gap-3 p-3">
                        <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-cyan-300/[.08] font-mono text-[10px] text-cyan-200">{String(index + 1).padStart(2, "0")}</span>
                        <span className="min-w-0 flex-1">
                          <span className="block text-xs font-semibold text-slate-200">{item.tool ?? "Unknown tool"}</span>
                          <span className="mt-1 block text-xs text-slate-500">{descriptions[item.tool ?? ""] ?? "Graph tool executed"}</span>
                        </span>
                        <ChevronDown size={14} className="mt-1 shrink-0 text-slate-500" />
                      </summary>
                      <div className="grid gap-3 border-t border-white/[.07] p-3 md:grid-cols-2">
                        <div>
                          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Input</p>
                          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/30 p-3 text-[11px] leading-5 text-slate-300">{pretty(item.input ?? {})}</pre>
                        </div>
                        <div>
                          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Output</p>
                          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/30 p-3 text-[11px] leading-5 text-slate-300">{pretty(item.output ?? {})}</pre>
                        </div>
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
