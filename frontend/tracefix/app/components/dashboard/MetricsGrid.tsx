
import { History } from "lucide-react";

type InvestigationSummaryProps = {
  observationsCount: number;
  relationshipCount: number;
  historicalMatches: number;
  trigger: string;
};

const summaryItems = (
  observationsCount: number,
  relationshipCount: number,
  historicalMatches: number,
  trigger: string,
) => [
  {
    number: "01",
    label: "Observed signals",
    value: `${observationsCount} returned observations`,
  },
  {
    number: "02",
    label: "Graph relationships",
    value: `${relationshipCount} returned relationships`,
  },
  {
    number: "03",
    label: "Historical context",
    value: `${historicalMatches} returned matches`,
  },
  {
    number: "04",
    label: "Current hypothesis",
    value: trigger,
  },
];

export default function InvestigationSummary({
  observationsCount,
  relationshipCount,
  historicalMatches,
  trigger,
}: InvestigationSummaryProps) {
  const items = summaryItems(
    observationsCount,
    relationshipCount,
    historicalMatches,
    trigger,
  );

  return (
    <section className="tracefix-panel min-w-0 p-5">
      <div className="flex items-center gap-3">
        <div className="grid size-9 place-items-center rounded-xl border border-white/[.08] bg-white/[.03] text-slate-300">
          <History size={17} />
        </div>

        <div>
          <p className="tracefix-eyebrow">Investigation summary</p>
          <h2 className="mt-1 text-sm font-semibold text-white">
            What TraceFix considered
          </h2>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div
            key={item.number}
            className="flex items-start gap-3 rounded-xl border border-white/[.07] bg-white/[.015] p-3"
          >
            <span className="pt-0.5 font-mono text-xs text-slate-500">
              {item.number}
            </span>

            <span className="min-w-0 flex-1 text-xs text-slate-400">
              {item.label}
            </span>

            <span className="max-w-[55%] break-words text-right text-xs font-medium leading-5 text-slate-200">
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
