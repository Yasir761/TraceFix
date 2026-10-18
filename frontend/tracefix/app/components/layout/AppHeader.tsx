
"use client";

import Image from "next/image";
import { Database, RefreshCw } from "lucide-react";
import Link from "next/link";

type Status = "checking" | "online" | "offline";

function StatusPill({
  label,
  status,
}: {
  label: string;
  status: Status;
}) {
  const colors: Record<Status, string> = {
    checking: "bg-amber-400",
    online: "bg-emerald-400",
    offline: "bg-rose-400",
  };

  const statusText: Record<Status, string> = {
    checking: "Checking",
    online: "Connected",
    offline: "Offline",
  };

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-white/[0.09] bg-white/[0.035] px-3 py-1.5 text-xs text-neutral-300">
      <span
        className={`h-1.5 w-1.5 rounded-full ${colors[status]}`}
      />
      {label}: {statusText[status]}
    </span>
  );
}

export default function AppHeader({
  apiStatus,
  graphStatus,
  onRefresh,
}: {
  apiStatus: Status;
  graphStatus: Status;
  onRefresh: () => void;
}) {
  return (
    <header className="flex min-h-[76px] flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] py-4">
      {/* Brand */}
      <Link
        href="/"
        aria-label="TraceFix home"
        className="group flex shrink-0 items-center gap-3 rounded-lg focus-visible:outline focus-visible:outline-cyan-300"
      >
        <span
          className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-xl border border-cyan-300/20 bg-cyan-300/[.07] transition-colors group-hover:bg-cyan-300/[.12]"
          aria-hidden="true"
        >
          <Image
            src="/logo.png"
            alt=""
            width={40}
            height={40}
            priority
            className="h-full w-full object-contain p-1"
          />
        </span>

        <div className="flex flex-col">
          <span className="text-lg font-semibold tracking-tight text-neutral-100">
            Trace<span className="text-cyan-300">Fix</span>
          </span>
          <span className="text-[10px] font-medium tracking-wide text-slate-500">
            Incident intelligence
          </span>
        </div>
      </Link>

      {/* System status and actions */}
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill label="API" status={apiStatus} />

        <span className="inline-flex items-center gap-2 rounded-full border border-white/[0.09] bg-white/[0.035] px-3 py-1.5 text-xs text-neutral-300">
          <Database size={13} className="text-neutral-400" />
          FalkorDB:{" "}
          {graphStatus === "online"
            ? "Connected"
            : graphStatus === "offline"
              ? "Offline"
              : "Checking"}
        </span>

        <button
          type="button"
          onClick={onRefresh}
          aria-label="Refresh workspace"
          title="Refresh workspace"
          className="grid h-9 w-9 place-items-center rounded-xl border border-white/[0.1] text-neutral-400 transition hover:border-white/20 hover:bg-white/[0.06] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
        >
          <RefreshCw size={15} />
        </button>
      </div>
    </header>
  );
}
