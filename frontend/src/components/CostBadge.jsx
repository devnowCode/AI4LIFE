import { Zap } from "lucide-react";

/**
 * Symbolic cost estimate badge. Renders like ⚡€0.0023 with tooltip
 * showing the underlying formula.
 */
export const CostBadge = ({ costEur, latencyMs, compact = false }) => {
  if (costEur == null) return null;

  const formatted = costEur < 0.0001
    ? "<€0.0001"
    : "€" + costEur.toFixed(costEur < 0.01 ? 4 : 3);

  return (
    <span
      data-testid="cost-badge"
      title={`Costo stimato: ${formatted}${latencyMs != null ? ` · Latenza reale: ${latencyMs}ms` : ""}`}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/25 ${compact ? "" : ""}`}
    >
      <Zap className="w-3 h-3 text-emerald-400" strokeWidth={2.5} />
      <span className="font-mono text-[10px] text-emerald-300 font-medium">{formatted}</span>
      {latencyMs != null && !compact && (
        <span className="font-mono text-[10px] text-emerald-500/70">· {latencyMs}ms</span>
      )}
    </span>
  );
};
