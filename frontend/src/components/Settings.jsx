import { useState } from "react";
import { Sliders, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { DEFAULT_WEIGHTS, getWeights, setWeights, resetWeights, normalizeWeights } from "@/lib/settings";

const LABELS = {
  capability: { label: "Capability", desc: "Preferisci modelli più capaci (potenza)." },
  latency: { label: "Latency", desc: "Preferisci modelli più veloci." },
  cost: { label: "Cost Efficiency", desc: "Preferisci modelli più economici." },
  context_bonus: { label: "Context Window", desc: "Bonus per modelli con context lungo." },
};

export const Settings = () => {
  const [w, setW] = useState(getWeights());

  const update = (k, v) => setW((prev) => ({ ...prev, [k]: v }));

  const save = () => {
    const norm = normalizeWeights(w);
    setW(norm);
    setWeights(norm);
    toast.success("Pesi salvati e normalizzati a 1.0");
  };

  const reset = () => {
    setW(resetWeights());
    toast.success("Pesi ripristinati ai valori di default");
  };

  const sum = +(w.capability + w.latency + w.cost + w.context_bonus).toFixed(3);

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-8 py-8 fade-up" data-testid="settings-view">
      <header className="mb-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-sky-400/80">Configurazione Router</p>
        <h1 className="font-display font-black text-3xl sm:text-4xl text-slate-50 tracking-tight mt-1">Routing Weights</h1>
        <p className="font-body text-slate-400 mt-2 max-w-2xl">
          Modifica la matrice di pesi che l&apos;orchestratore usa per scegliere il modello ottimale.
          I valori vengono normalizzati automaticamente. Salvati localmente e inviati a ogni richiesta.
        </p>
      </header>

      <div className="glass-heavy rounded-2xl p-6 space-y-6">
        {Object.keys(LABELS).map((k) => (
          <div key={k} data-testid={`weight-slider-${k}`}>
            <div className="flex items-baseline justify-between mb-1.5">
              <div>
                <p className="font-display font-bold text-slate-100 text-sm">{LABELS[k].label}</p>
                <p className="font-body text-xs text-slate-400 mt-0.5">{LABELS[k].desc}</p>
              </div>
              <span className="font-mono text-sky-300 text-sm w-14 text-right">{w[k].toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={w[k]}
              onChange={(e) => update(k, parseFloat(e.target.value))}
              className="w-full accent-sky-400"
              data-testid={`weight-input-${k}`}
            />
          </div>
        ))}

        <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between">
          <div className="font-mono text-xs text-slate-500">
            Somma corrente: <span className={sum === 1 ? "text-emerald-300" : "text-amber-300"}>{sum}</span>
            {sum !== 1 && <span className="text-slate-600 ml-1.5">(verrà normalizzata al salvataggio)</span>}
          </div>
          <div className="flex gap-2">
            <Button
              data-testid="reset-weights-btn"
              onClick={reset}
              variant="outline"
              className="border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800 hover:text-slate-50"
            >
              <RotateCcw className="w-4 h-4 mr-1.5" strokeWidth={1.5} /> Reset
            </Button>
            <Button
              data-testid="save-weights-btn"
              onClick={save}
              className="bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold"
            >
              <Sliders className="w-4 h-4 mr-1.5" strokeWidth={2} /> Salva
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-6 glass rounded-xl p-4 font-mono text-xs text-slate-400">
        <p className="text-sky-300 mb-1">Default:</p>
        {Object.entries(DEFAULT_WEIGHTS).map(([k, v]) => (
          <span key={k} className="mr-4">{k}={v}</span>
        ))}
      </div>
    </div>
  );
};
