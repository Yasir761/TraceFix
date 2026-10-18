import { GitBranch, Network, ShieldCheck } from "lucide-react";

export default function HeroSection() {
  return (
    <section className="border-b border-white/[.06] py-5 sm:py-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <div className="mb-2 inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-cyan-200"><span className="size-1.5 rounded-full bg-cyan-300" />Graph-powered incident response</div>
          <h1 className="text-2xl font-semibold tracking-[-.04em] text-white sm:text-3xl">From incident signal to evidence-backed action.</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">TraceFix connects service dependencies, investigation signals, and historical decisions to explain likely causes—not just surface alerts.</p>
        </div>
        <div className="grid grid-cols-3 gap-2 lg:min-w-[390px]">
          {[
            { icon: <GitBranch size={15} />, label: "Investigate" },
            { icon: <Network size={15} />, label: "Connect" },
            { icon: <ShieldCheck size={15} />, label: "Validate" },
          ].map((item, index) => <div key={item.label} className="flex items-center gap-2 rounded-lg border border-white/[.07] bg-white/[.025] px-3 py-2.5"><span className="text-cyan-200">{item.icon}</span><span className="text-xs font-medium text-slate-300">{String(index + 1).padStart(2, "0")} {item.label}</span></div>)}
        </div>
      </div>
    </section>
  );
}
