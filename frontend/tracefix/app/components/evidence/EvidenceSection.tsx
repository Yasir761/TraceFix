
import { FileSearch } from "lucide-react";
import EvidencePanel from "../EvidencePanel";

type Data = Record<string, unknown>;

type EvidenceSectionProps = {
  decision?: Data;
  topology: Data;
  baseline: Data[];
};

export default function EvidenceSection({
  decision,
  topology,
  baseline,
}: EvidenceSectionProps) {
  const evidence = decision?.evidence;
  const evidenceCount = Array.isArray(evidence)
    ? evidence.length
    : null;

  return (
    <section
      id="investigation-evidence"
      className="tracefix-panel mt-5 min-w-0 p-4 sm:p-6"
    >
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
            <FileSearch className="h-5 w-5 text-neutral-300" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-neutral-100">
              Investigation Evidence
            </h2>
            <p className="mt-1 text-sm text-neutral-400">
              Supporting signals and historical context
            </p>
          </div>
        </div>

        {evidenceCount !== null && (
          <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-neutral-300">
            {evidenceCount} items
          </span>
        )}
      </div>

      <EvidencePanel
        decision={decision}
        topology={topology}
        baseline={baseline}
      />
    </section>
  );
}
