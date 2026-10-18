
"use client";

import { Check, History, X } from "lucide-react";

export type StoredDecision = {
  decision_id?: string;
  id?: string;
  incident_id?: string;
  verdict?: string;
  worked?: boolean | null;
  recommended_fix_id?: string;
  [key: string]: unknown;
};

type DecisionMemoryProps = {
  decisions: StoredDecision[];
  onUpdateOutcome: (decisionId: string, worked: boolean) => void;
};

function displayText(value: unknown, fallback = "Not available") {
  return typeof value === "string" || typeof value === "number"
    ? String(value)
    : fallback;
}

export default function DecisionMemory({
  decisions,
  onUpdateOutcome,
}: DecisionMemoryProps) {
  return (
    <section className="tracefix-panel min-w-0 p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="tracefix-eyebrow">Graph memory</p>
          <h2 className="mt-1 text-sm font-semibold text-white">
            Previous decisions
          </h2>
        </div>

        <History className="text-slate-400" size={18} />
      </div>

      <p className="mt-2 text-xs leading-5 text-slate-500">
        Recorded outcomes provide context for future investigations.
      </p>

      <div className="mt-4 space-y-2">
        {decisions.length > 0 ? (
          decisions.slice(0, 3).map((item, index) => {
            const id = displayText(item.decision_id ?? item.id, "");

            return (
              <article
                key={`${id || "decision"}-${index}`}
                className="rounded-xl border border-white/[.08] bg-white/[.02] p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-[11px] text-slate-300">
                    {displayText(item.incident_id, "Incident")}
                  </span>

                  <span className="rounded-full border border-white/10 px-2 py-1 text-[10px] text-slate-400">
                    {displayText(item.verdict, "Recorded")}
                  </span>
                </div>

                <p className="mt-2 break-words text-xs text-slate-400">
                  {displayText(item.recommended_fix_id, "No fix identifier")}
                </p>

                {id && item.worked == null && (
                  <div className="mt-3 flex flex-wrap gap-4">
                    <button
                      type="button"
                      onClick={() => onUpdateOutcome(id, true)}
                      className="inline-flex items-center gap-1.5 text-[11px] text-slate-300 transition hover:text-white"
                    >
                      <Check size={13} />
                      Resolved
                    </button>

                    <button
                      type="button"
                      onClick={() => onUpdateOutcome(id, false)}
                      className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 transition hover:text-white"
                    >
                      <X size={13} />
                      Did not work
                    </button>
                  </div>
                )}

                {item.worked != null && (
                  <p className="mt-3 text-[11px] text-slate-400">
                    Outcome: {item.worked ? "Resolved" : "Did not resolve"}
                  </p>
                )}
              </article>
            );
          })
        ) : (
          <p className="rounded-xl border border-dashed border-white/[.12] p-3 text-xs leading-5 text-slate-500">
            No stored decisions have been returned by the backend yet.
          </p>
        )}
      </div>
    </section>
  );
}
