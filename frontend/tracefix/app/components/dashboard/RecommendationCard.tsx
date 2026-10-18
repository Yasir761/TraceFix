
"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Save,
  ShieldCheck,
} from "lucide-react";

type RecommendationCardProps = {
  title: string;
  verdict: string;
  reason: string;
  recommendedAction: string;
  caveat?: string;
  recording: boolean;
  hasResult: boolean;
  onRecordDecision: () => void;
};

export default function RecommendationCard({
  title,
  verdict,
  reason,
  recommendedAction,
  caveat,
  recording,
  hasResult,
  onRecordDecision,
}: RecommendationCardProps) {
  const normalizedVerdict = verdict.toUpperCase();

  return (
    <section className="tracefix-panel min-w-0 overflow-hidden p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="tracefix-eyebrow">Investigation conclusion</p>

          <h2 className="mt-2 text-lg font-semibold leading-snug text-white">
            {title}
          </h2>
        </div>

        <span className="shrink-0 rounded-full border border-white/[.12] bg-white/[.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.12em] text-slate-300">
          {verdict}
        </span>
      </div>

      {hasResult ? (
        <>
          <div className="mt-5 border-l-2 border-white/25 pl-3">
            <p className="text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
              Why this finding
            </p>

            <p className="mt-2 text-sm leading-6 text-slate-300">
              {reason}
            </p>
          </div>

          <div className="mt-5 rounded-xl border border-white/[.09] bg-white/[.03] p-4">
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.12em] text-slate-400">
              {normalizedVerdict === "REJECT" ? (
                <ShieldCheck size={14} />
              ) : (
                <CheckCircle2 size={14} />
              )}
              Recommended next action
            </div>

            <p className="mt-2 text-base font-semibold leading-6 text-white">
              {recommendedAction}
            </p>
          </div>

          {caveat && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-white/[.08] bg-white/[.025] p-3 text-xs leading-5 text-slate-400">
              <AlertTriangle
                className="mt-0.5 shrink-0 text-slate-400"
                size={14}
              />
              <span>{caveat}</span>
            </div>
          )}

          <p className="mt-4 text-[11px] leading-5 text-slate-500">
            Recommendation only. Validate the evidence and proposed change
            before modifying infrastructure.
          </p>

          <button
            type="button"
            onClick={onRecordDecision}
            disabled={recording}
            className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-white/[.14] bg-white/[.05] px-3 text-xs font-semibold text-slate-200 transition hover:bg-white/[.09] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Save size={14} />
            {recording
              ? "Recording decision…"
              : "Record decision in graph memory"}
          </button>
        </>
      ) : (
        <div className="mt-5 rounded-xl border border-dashed border-white/[.1] p-4">
          <p className="text-sm leading-6 text-slate-400">
            Run an investigation to see the finding, supporting evidence,
            and recommended next action.
          </p>
        </div>
      )}
    </section>
  );
}
