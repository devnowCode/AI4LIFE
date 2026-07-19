import { RouterPill } from "./RouterPill";
import { AlertTriangle, Sparkles } from "lucide-react";

/**
 * Side-by-side Compare card. Renders N model results in a responsive grid.
 */
export const CompareCard = ({ prompt, results }) => (
  <article
    data-testid="compare-card"
    className="glass-heavy rounded-2xl overflow-hidden fade-up"
  >
    <header className="px-6 pt-5 pb-4 border-b border-slate-800/60 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="font-mono text-[10px] uppercase tracking-widest text-sky-400/80 mb-1">
          <Sparkles className="inline w-3 h-3 mr-1" strokeWidth={2} /> Comparison Mode
        </p>
        <p className="font-body text-slate-200 text-sm line-clamp-2">{prompt}</p>
      </div>
      <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500 shrink-0">
        {results?.length || 0} modelli
      </span>
    </header>

    <div className={`grid gap-0 ${
      (results?.length || 0) >= 3
        ? "grid-cols-1 md:grid-cols-3"
        : "grid-cols-1 md:grid-cols-2"
    }`}>
      {results?.map((r, i) => (
        <CompareCell key={r.model_id} cell={r} isLast={i === results.length - 1} />
      ))}
    </div>
  </article>
);

const CompareCell = ({ cell, isLast }) => {
  if (!cell.ok) {
    return (
      <div className={`p-5 border-t md:border-t-0 border-slate-800/60 ${!isLast ? "md:border-r" : ""}`} data-testid={`compare-cell-${cell.model_id}`}>
        <p className="font-mono text-[11px] uppercase tracking-widest text-rose-400 mb-2">{cell.model_id}</p>
        <div className="flex items-center gap-2 text-rose-300 font-mono text-xs">
          <AlertTriangle className="w-4 h-4" strokeWidth={1.5} />
          {cell.error}
        </div>
      </div>
    );
  }

  const { response } = cell;
  const selected = response.routing.selected;
  const hasImages = response.images && response.images.length > 0;

  return (
    <div
      data-testid={`compare-cell-${cell.model_id}`}
      className={`p-5 border-t md:border-t-0 border-slate-800/60 ${!isLast ? "md:border-r" : ""}`}
    >
      <div className="mb-3">
        <RouterPill selected={selected} compact costEur={response.cost_estimate_eur} latencyMs={response.latency_ms} />
      </div>
      {hasImages && (
        <div className="mb-3 space-y-2">
          {response.images.map((img, i) => (
            <img key={img.data_url.slice(-64)} src={img.data_url} alt={`compare-${i}`} className="w-full rounded-lg border border-slate-800" />
          ))}
        </div>
      )}
      <p className="font-body text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">
        {response.result}
      </p>
    </div>
  );
};
