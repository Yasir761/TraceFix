import { FileSearch } from "lucide-react";

type Data = Record<string, unknown>;

type EvidenceSectionProps = {
  decision?: Data;
  topology: Data;
  baseline: Data[];
};

function displayItem(item: unknown): string {
  if (typeof item === "string" || typeof item === "number") {
    return String(item);
  }

  if (typeof item === "object" && item !== null) {
    const row = item as Record<string, unknown>;
    const label = row.metric ?? row.name ?? row.title;
    const value = row.value;

    if (label != null && value != null) {
      return `${String(label)}: ${String(value)}`;
    }

    return JSON.stringify(item) ?? "Evidence item";
  }

  return "Evidence item";
}

export default function EvidenceSection({
  decision,
  topology,
  baseline,
}: EvidenceSectionProps) {
  const observations = Array.isArray(topology.observations)
    ? topology.observations
    : [];

  const evidence = Array.isArray(decision?.evidence)
    ? decision.evidence
    : [];

  return (
    <section
      id="investigation-evidence"
      className="tracefix-panel mt-5 min-w-0 p-4 sm:p-6"
    >
      <div className="mb-5 flex items-center gap-3">
        <FileSearch className="h-5 w-5 text-neutral-300" />
        <div>
          <h2 className="text-base font-semibold text-neutral-100">
            Investigation Evidence
          </h2>
          <p className="mt-1 text-sm text-neutral-400">
            Supporting signals and historical context
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-white/10 p-4">
          <h3 className="text-sm font-semibold text-neutral-200">
            Observed signals
          </h3>
          {observations.length > 0 ? (
            <ul className="mt-3 space-y-2 text-sm text-neutral-400">
              {observations.map((item, index) => (
                <li key={index}>{displayItem(item)}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-neutral-500">
              No observations were returned.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-white/10 p-4">
          <h3 className="text-sm font-semibold text-neutral-200">
            Decision evidence
          </h3>
          {evidence.length > 0 ? (
            <ul className="mt-3 space-y-2 text-sm text-neutral-400">
              {evidence.map((item, index) => (
                <li key={index}>{displayItem(item)}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-neutral-500">
              No additional decision evidence was returned.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-white/10 p-4 md:col-span-2">
          <h3 className="text-sm font-semibold text-neutral-200">
            Historical context
          </h3>
          <p className="mt-2 text-sm text-neutral-400">
            {baseline.length} historical{" "}
            {baseline.length === 1 ? "match" : "matches"} returned.
          </p>
        </div>
      </div>
    </section>
  );
}