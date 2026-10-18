
import { Activity } from "lucide-react";

type ReasoningComparisonProps = {
  historicalMatch?: string;
  relationshipCount: number;
};

export default function ReasoningComparison({
  historicalMatch,
  relationshipCount,
}: ReasoningComparisonProps) {
  return (
    <section className="tracefix-panel min-w-0 p-5">
      <div className="flex items-center gap-3">
        <div className="grid size-9 place-items-center rounded-xl border border-white/[.08] bg-white/[.03] text-slate-300">
          <Activity size={17} />
        </div>

        <div>
          <p className="tracefix-eyebrow">Reasoning comparison</p>
          <h2 className="mt-1 text-sm font-semibold text-white">
            Signals vs. context
          </h2>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-white/[.08] bg-white/[.02] p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
            Historical context
          </p>

          <p className="mt-2 text-xs leading-5 text-slate-400">
            {historicalMatch
              ? `Nearest returned precedent: ${historicalMatch}.`
              : "No historical match was returned for comparison."}
          </p>
        </div>

        <div className="rounded-xl border border-white/[.08] bg-white/[.02] p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[.12em] text-slate-500">
            TraceFix graph-aware
          </p>

          <p className="mt-2 text-xs leading-5 text-slate-300">
            {relationshipCount > 0
              ? `${relationshipCount} returned relationship${
                  relationshipCount === 1 ? "" : "s"
                } connect the incident topology to the investigation hypothesis.`
              : "No topology relationships were returned."}
          </p>
        </div>
      </div>
    </section>
  );
}
