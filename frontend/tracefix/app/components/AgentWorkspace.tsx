"use client";

import { useEffect, useMemo, useState } from "react";
import { Database, Search, X, Network, ArrowRight } from "lucide-react";

type Data = Record<string, unknown>;
type IncidentOption = { id: string; title?: string };

const displayValue = (value: unknown, fallback = "Not available") =>
  typeof value === "string" || typeof value === "number" ? String(value) : fallback;

export function CommandPalette({
  open,
  onOpenChange,
  incidents,
  onSelectIncident,
  onInvestigate,
  canInvestigate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  incidents: IncidentOption[];
  onSelectIncident: (id: string) => void;
  onInvestigate: () => void;
  canInvestigate: boolean;
}) {
  const [query, setQuery] = useState("");
  const filteredIncidents = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return incidents;
    return incidents.filter((incident) =>
      `${incident.id} ${incident.title ?? ""}`.toLowerCase().includes(normalized),
    );
  }, [incidents, query]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onOpenChange(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpenChange, open]);

  useEffect(() => {
    if (open) setQuery("");
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 px-4 pt-[12vh] backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) onOpenChange(false); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="command-title" className="w-full max-w-xl overflow-hidden rounded-2xl border border-white/10 bg-[#101823] shadow-2xl">
        <div className="flex items-center gap-3 border-b border-white/[.08] px-4">
          <Search size={17} className="shrink-0 text-cyan-200" />
          <label htmlFor="tracefix-command-search" className="sr-only">Search incidents and actions</label>
          <input id="tracefix-command-search" autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search incidents or actions…" className="h-12 min-w-0 flex-1 border-0 bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500" />
          <button type="button" onClick={() => onOpenChange(false)} aria-label="Close command palette" className="rounded-md p-1.5 text-slate-500 hover:bg-white/[.06] hover:text-white"><X size={16} /></button>
        </div>
        <div className="p-3">
          <h2 id="command-title" className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[.14em] text-slate-500">Actions</h2>
          <button type="button" disabled={!canInvestigate} onClick={() => { onInvestigate(); onOpenChange(false); }} className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-slate-200 hover:bg-white/[.05] disabled:cursor-not-allowed disabled:opacity-40">
            <span className="grid size-8 place-items-center rounded-lg bg-cyan-300/10 text-cyan-200"><Search size={15} /></span>
            <span className="flex-1">Investigate selected incident</span><span className="text-[10px] text-slate-500">Enter</span>
          </button>
          <h3 className="px-2 pb-2 pt-4 text-[10px] font-semibold uppercase tracking-[.14em] text-slate-500">Incidents</h3>
          <div className="max-h-[42vh] overflow-y-auto">
            {filteredIncidents.length ? filteredIncidents.map((incident) => (
              <button key={incident.id} type="button" onClick={() => { onSelectIncident(incident.id); onOpenChange(false); }} className="flex w-full min-w-0 items-center gap-3 rounded-lg px-3 py-2.5 text-left hover:bg-white/[.05]">
                <Network size={15} className="shrink-0 text-slate-500" />
                <span className="min-w-0 flex-1"><span className="block truncate font-mono text-xs text-cyan-100">{incident.id}</span><span className="block truncate text-xs text-slate-400">{incident.title ?? "Untitled incident"}</span></span><ArrowRight size={14} className="shrink-0 text-slate-600" />
              </button>
            )) : <p className="px-3 py-5 text-center text-xs text-slate-500">No matching incidents.</p>}
          </div>
          <p className="px-2 pt-3 text-[10px] text-slate-600">Tip: press Ctrl K to open this command palette.</p>
        </div>
      </section>
    </div>
  );
}

export function ServiceInspector({
  open,
  onOpenChange,
  nodeId,
  nodeName,
  edges,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  nodeId?: string;
  nodeName?: string;
  edges: Data[];
}) {
  const connected = edges.filter((edge) =>
    String(edge.source_id ?? edge.source ?? "") === nodeId ||
    String(edge.target_id ?? edge.target ?? "") === nodeId,
  );

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onOpenChange(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 bg-black/50" onMouseDown={(event) => { if (event.target === event.currentTarget) onOpenChange(false); }}>
      <aside role="dialog" aria-modal="true" aria-labelledby="service-inspector-title" className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col border-l border-white/10 bg-[#101823] shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-white/[.08] p-5">
          <div className="min-w-0"><div className="flex items-center gap-2 text-cyan-200"><Database size={15} /><span className="text-[10px] font-semibold uppercase tracking-[.14em]">Service inspector</span></div><h2 id="service-inspector-title" className="mt-2 break-words text-lg font-semibold text-white">{nodeName ?? nodeId ?? "Service"}</h2><p className="mt-1 break-all font-mono text-[11px] text-slate-500">{nodeId}</p></div>
          <button type="button" onClick={() => onOpenChange(false)} aria-label="Close service inspector" className="rounded-lg p-2 text-slate-500 hover:bg-white/[.06] hover:text-white"><X size={17} /></button>
        </header>
        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[.045] p-4"><p className="text-[10px] font-semibold uppercase tracking-[.12em] text-cyan-200">Connected relationships</p><p className="mt-1 text-2xl font-semibold text-white">{connected.length}</p><p className="mt-1 text-xs leading-5 text-slate-500">Only topology relationships returned by the investigation are shown.</p></div>
          <div><h3 className="text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">Dependencies</h3><div className="mt-2 space-y-2">{connected.length ? connected.map((edge, index) => <div key={`${String(edge.source_id ?? edge.source)}-${String(edge.target_id ?? edge.target)}-${index}`} className="rounded-lg border border-white/[.07] bg-white/[.02] p-3 font-mono text-[11px] leading-5 text-slate-300"><span className="break-words">{displayValue(edge.source_name ?? edge.source_id ?? edge.source)}</span><span className="px-2 text-cyan-300">→</span><span className="break-words">{displayValue(edge.target_name ?? edge.target_id ?? edge.target)}</span></div>) : <p className="rounded-lg border border-dashed border-white/[.08] p-3 text-xs leading-5 text-slate-500">No relationships were returned for this service.</p>}</div></div>
        </div>
      </aside>
    </div>
  );
}
