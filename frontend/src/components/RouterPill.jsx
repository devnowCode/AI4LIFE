import { Cpu, Zap, DollarSign, Target } from "lucide-react";

export const RouterPill = ({ selected, compact = false }) => {
  if (!selected) return null;
  return (
    <div
      data-testid="router-pill"
      className={`inline-flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-full glass border border-sky-500/25 fade-up ${compact ? "flex-wrap" : ""}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-sky-400 beam shrink-0" />
      {!compact && (
        <span className="font-mono text-[11px] uppercase tracking-widest text-slate-500 shrink-0">Instradato a</span>
      )}
      <span className="font-display font-bold text-sm text-sky-300 shrink-0">{selected.display_name}</span>

      {!compact && <span className="hidden sm:inline w-px h-4 bg-slate-800 mx-1" />}

      <div className={`flex items-center gap-1 ${compact ? "w-full mt-1 pl-3" : ""}`}>
        <Badge icon={Target} label="cap" value={selected.capability_score} compact={compact} />
        <Badge icon={Zap} label="lat" value={selected.latency_index} compact={compact} />
        <Badge icon={DollarSign} label="cost" value={selected.cost_efficiency} compact={compact} />
      </div>
    </div>
  );
};

const Badge = ({ icon: Icon, label, value, compact }) => (
  <span className={`${compact ? "inline-flex" : "hidden sm:inline-flex"} items-center gap-1 px-1.5 py-0.5 rounded-md bg-slate-900/70 border border-slate-800`}>
    <Icon className="w-3 h-3 text-sky-400" strokeWidth={2} />
    <span className="font-mono text-[10px] text-slate-500 uppercase">{label}</span>
    <span className="font-mono text-[10px] text-slate-200 font-medium">{value}</span>
  </span>
);
