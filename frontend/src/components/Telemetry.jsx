import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Zap, TrendingUp, Timer, Image as ImageIcon, Activity } from "lucide-react";

export const Telemetry = () => {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const { data } = await api.get("/telemetry");
        if (mounted) setData(data);
      } catch (e) {
        if (mounted) setErr(String(e));
      }
    };
    load();
    const t = setInterval(load, 5000);
    return () => { mounted = false; clearInterval(t); };
  }, []);

  if (err) return <div className="p-8 text-rose-300 font-mono text-sm">Errore: {err}</div>;
  if (!data) return <div className="p-8 text-slate-500 font-mono text-sm">Caricamento telemetria…</div>;

  const { totals, by_model, recent } = data;
  const maxCost = Math.max(...by_model.map((m) => m.total_cost_eur), 0.0001);

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-8 fade-up" data-testid="telemetry-view">
      <header className="mb-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-sky-400/80">FinOps</p>
        <h1 className="font-display font-black text-3xl sm:text-4xl text-slate-50 tracking-tight mt-1">Telemetry</h1>
        <p className="font-body text-slate-400 mt-2 max-w-2xl">
          Monitoraggio costi e latenza per modello. Aggiornato ogni 5 secondi.
        </p>
      </header>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <KpiCard icon={Activity} label="Richieste totali" value={totals.requests} testid="kpi-requests" />
        <KpiCard icon={Zap} label="Costo totale" value={`€${totals.total_cost_eur.toFixed(4)}`} testid="kpi-cost" />
        <KpiCard icon={Timer} label="Latenza media" value={`${totals.avg_latency_ms} ms`} testid="kpi-latency" />
      </div>

      {/* By model */}
      <section className="glass-heavy rounded-2xl p-6 mb-6" data-testid="telemetry-by-model">
        <h2 className="font-display font-bold text-slate-100 text-lg mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-sky-400" strokeWidth={1.5} />
          Distribuzione per Modello
        </h2>
        {by_model.length === 0 ? (
          <p className="font-body text-sm text-slate-500">Nessuna richiesta ancora registrata.</p>
        ) : (
          <div className="space-y-3">
            {by_model.map((m) => (
              <div key={m.model} className="grid grid-cols-12 gap-2 items-center" data-testid={`row-${m.model}`}>
                <div className="col-span-4 md:col-span-3">
                  <p className="font-display font-bold text-sm text-slate-100 truncate">{m.model}</p>
                  <p className="font-mono text-[10px] text-slate-500">{m.requests} richieste · {m.total_images} img</p>
                </div>
                <div className="col-span-5 md:col-span-6">
                  <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-500 to-sky-400 transition-all duration-500"
                      style={{ width: `${(m.total_cost_eur / maxCost) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="col-span-3 text-right">
                  <p className="font-mono text-emerald-300 text-sm">€{m.total_cost_eur.toFixed(4)}</p>
                  <p className="font-mono text-[10px] text-slate-500">{m.avg_latency_ms} ms</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Recent */}
      <section className="glass-heavy rounded-2xl p-6" data-testid="telemetry-recent">
        <h2 className="font-display font-bold text-slate-100 text-lg mb-4">Ultime Richieste</h2>
        {recent.length === 0 ? (
          <p className="font-body text-sm text-slate-500">Nessuna richiesta ancora.</p>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-800/60">
                <Th>Timestamp</Th>
                <Th>Modello</Th>
                <Th>Intent</Th>
                <Th>Output</Th>
                <Th>Latenza</Th>
                <Th className="text-right">Costo</Th>
              </tr>
            </thead>
            <tbody>
              {recent.slice(0, 12).map((r, i) => (
                <tr key={i} className="border-b border-slate-800/40" data-testid={`recent-row-${i}`}>
                  <td className="px-3 py-2 font-mono text-[10px] text-slate-500">
                    {new Date(r.created_at).toLocaleTimeString("it-IT")}
                  </td>
                  <td className="px-3 py-2 font-body text-xs text-slate-200">{r.model_display}</td>
                  <td className="px-3 py-2 font-mono text-[10px] text-sky-300">{r.intent_id}</td>
                  <td className="px-3 py-2 font-mono text-[10px] text-slate-400">
                    {r.output_len} chars {r.num_images > 0 && <ImageIcon className="inline w-3 h-3 ml-1 text-sky-400" strokeWidth={1.5} />}
                  </td>
                  <td className="px-3 py-2 font-mono text-[10px] text-slate-400">{r.latency_ms} ms</td>
                  <td className="px-3 py-2 font-mono text-[11px] text-emerald-300 text-right">€{r.cost_eur.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

const KpiCard = ({ icon: Icon, label, value, testid }) => (
  <div data-testid={testid} className="glass-heavy rounded-xl p-5">
    <div className="flex items-center gap-2 mb-2">
      <Icon className="w-4 h-4 text-sky-400" strokeWidth={1.5} />
      <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">{label}</p>
    </div>
    <p className="font-display font-black text-3xl text-slate-50">{value}</p>
  </div>
);

const Th = ({ children, className = "" }) => (
  <th className={`px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-slate-500 font-medium ${className}`}>{children}</th>
);
