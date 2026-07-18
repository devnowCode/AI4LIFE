import { useEffect, useState } from "react";
import { fetchModels } from "@/lib/api";
import { Cpu, Zap, DollarSign, FileText, Image as ImageIcon } from "lucide-react";

export const ModelRegistry = () => {
  const [registry, setRegistry] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    fetchModels().then(setRegistry).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div className="p-8 text-rose-300 font-mono text-sm">Errore: {err}</div>;
  if (!registry) return <div className="p-8 text-slate-500 font-mono text-sm">Caricamento registry…</div>;

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-8 fade-up" data-testid="model-registry-view">
      <header className="mb-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-sky-400/80">Configuration</p>
        <h1 className="font-display font-black text-3xl sm:text-4xl text-slate-50 tracking-tight mt-1">Model Registry</h1>
        <p className="font-body text-slate-400 mt-2 max-w-2xl">
          Matrice di modelli disponibili. Aggiungi un nuovo modello in
          <span className="font-mono text-sky-300"> models_registry.json </span>
          e verrà scoperto automaticamente dal router.
        </p>
      </header>

      <div className="glass-heavy rounded-2xl overflow-hidden">
        <table className="w-full text-left" data-testid="models-table">
          <thead>
            <tr className="border-b border-slate-800/60 bg-slate-900/40">
              <Th>Modello</Th>
              <Th>Provider</Th>
              <Th><Cpu className="inline w-3.5 h-3.5 mr-1 text-sky-400" strokeWidth={1.5} />Capability</Th>
              <Th><Zap className="inline w-3.5 h-3.5 mr-1 text-sky-400" strokeWidth={1.5} />Latency</Th>
              <Th><DollarSign className="inline w-3.5 h-3.5 mr-1 text-sky-400" strokeWidth={1.5} />Cost eff.</Th>
              <Th>Best use-case</Th>
              <Th>Supporto</Th>
            </tr>
          </thead>
          <tbody>
            {registry.models.map((m) => (
              <tr
                key={m.id}
                data-testid={`model-row-${m.id}`}
                className="border-b border-slate-800/40 hover:bg-slate-900/40 transition-colors"
              >
                <td className="px-4 py-4">
                  <div className="font-display font-bold text-slate-50">{m.display_name}</div>
                  <div className="font-mono text-[11px] text-slate-500 mt-0.5">{m.id}</div>
                  <div className="font-body text-xs text-slate-400 mt-1 max-w-xs">{m.tagline}</div>
                </td>
                <td className="px-4 py-4 font-mono text-xs text-slate-300 uppercase">{m.provider}</td>
                <ScoreCell value={m.capability_score} />
                <ScoreCell value={m.latency_index} />
                <ScoreCell value={m.cost_efficiency} />
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1">
                    {m.best_use_case.slice(0, 3).map((uc) => (
                      <span key={uc} className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800/70 text-sky-300 border border-slate-700/50">
                        {uc}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <div className="flex gap-1.5">
                    {m.supports_files && <FileText className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />}
                    {m.supports_images && <ImageIcon className="w-4 h-4 text-sky-400" strokeWidth={1.5} />}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 glass rounded-xl p-4 font-mono text-xs text-slate-400">
        <span className="text-sky-300">routing_weights </span>=&nbsp;
        {JSON.stringify(registry.routing_weights)}
      </div>
    </div>
  );
};

const Th = ({ children }) => (
  <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-widest text-slate-500 font-medium">{children}</th>
);

const ScoreCell = ({ value }) => (
  <td className="px-4 py-4">
    <div className="flex items-center gap-2">
      <div className="w-16 h-1 rounded-full bg-slate-800 overflow-hidden">
        <div className="h-full bg-gradient-to-r from-sky-500 to-blue-400" style={{ width: `${value}%` }} />
      </div>
      <span className="font-mono text-xs text-slate-300 w-6 text-right">{value}</span>
    </div>
  </td>
);
