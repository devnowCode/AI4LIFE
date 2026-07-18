import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Sidebar, MobileNav } from "@/components/Sidebar";
import { PromptDock } from "@/components/PromptDock";
import { ResponseCard } from "@/components/ResponseCard";
import { ModelRegistry } from "@/components/ModelRegistry";
import { Archive } from "@/components/Archive";
import { fetchModels, orchestrate, fileToBase64 } from "@/lib/api";
import { Sparkles, Brain, Layers3, GitBranch } from "lucide-react";

export default function Dashboard() {
  const [view, setView] = useState("chat");
  const [models, setModels] = useState([]);
  const [forcedModel, setForcedModel] = useState(null);
  const [entries, setEntries] = useState([]);
  const [busy, setBusy] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  useEffect(() => {
    fetchModels().then((r) => setModels(r.models)).catch(() => {});
  }, []);

  const handleSubmit = async ({ text, files }) => {
    setBusy(true);
    try {
      const filePayloads = await Promise.all(files.map(fileToBase64));
      const res = await orchestrate({
        prompt: text,
        files: filePayloads,
        force_model_id: forcedModel || undefined,
        session_id: sessionId,
      });
      setEntries((prev) => [
        { ...res, prompt: text || "(solo allegati)", ts: Date.now() },
        ...prev,
      ]);
    } catch (e) {
      toast.error("Errore orchestratore: " + (e?.response?.data?.detail || e.message));
    } finally {
      setBusy(false);
    }
  };

  const handleRework = (entry) => {
    setEntries((prev) => prev.filter((e) => e.ts !== entry.ts));
    handleSubmit({ text: entry.prompt + "\n\n[RIELABORA con approccio alternativo]", files: [] });
  };

  return (
    <div className="min-h-screen flex text-slate-100 grain relative" data-testid="dashboard">
      <Sidebar active={view} onChange={setView} />

      <main className="flex-1 flex flex-col min-w-0 relative z-10">
        <MobileNav active={view} onChange={setView} />

        {view === "chat" && (
          <ChatView entries={entries} busy={busy} onRework={handleRework} models={models} />
        )}
        {view === "registry" && <ModelRegistry />}
        {view === "archive" && <Archive />}

        {view === "chat" && (
          <div className="sticky bottom-0 left-0 right-0 pointer-events-none">
            <div className="pointer-events-auto">
              <PromptDock
                onSubmit={handleSubmit}
                busy={busy}
                models={models}
                forced={forcedModel}
                onForcedChange={setForcedModel}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

const ChatView = ({ entries, busy, onRework, models }) => (
  <div className="flex-1 overflow-y-auto">
    <div className="max-w-4xl mx-auto px-4 md:px-8 pt-10 pb-4">
      {entries.length === 0 && !busy && <EmptyState models={models} />}

      {busy && <RoutingSkeleton />}

      <div className="space-y-6">
        {entries.map((entry) => (
          <ResponseCard key={entry.ts} entry={entry} onRework={onRework} />
        ))}
      </div>
    </div>
  </div>
);

const EmptyState = ({ models }) => (
  <div className="mt-8 mb-16 fade-up" data-testid="empty-state">
    <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-sky-400/80">The Intelligent Orchestrator</p>
    <h1 className="font-display font-black text-4xl sm:text-5xl lg:text-6xl text-slate-50 tracking-tight mt-2 leading-[1.05]">
      Un input.<br/>
      <span className="text-slate-500">Il modello ottimale.</span><br/>
      <span className="bg-gradient-to-r from-sky-300 to-blue-500 bg-clip-text text-transparent">Zero attriti.</span>
    </h1>
    <p className="font-body text-slate-400 mt-6 max-w-xl leading-relaxed">
      AI4LIFE analizza l&apos;intento, incrocia una matrice di pesi e instrada la richiesta
      al modello più adatto — restituendo Risultato + Insight tecnico.
    </p>

    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-10">
      <FeatureCard icon={Brain} title="Intent Recognition" desc="Analisi semantica del prompt in tempo reale." />
      <FeatureCard icon={GitBranch} title="Semantic Routing" desc="Matrice di pesi capability × latency × cost." />
      <FeatureCard icon={Layers3} title="Dual Output" desc="Risultato leggibile + Insight tecnico di routing." />
    </div>

    <div className="mt-10 flex flex-wrap gap-2">
      {models.slice(0, 5).map((m) => (
        <span key={m.id} className="font-mono text-[10px] px-2.5 py-1 rounded-full glass border border-slate-800 text-slate-400">
          <span className="text-sky-400">●</span> {m.display_name}
        </span>
      ))}
    </div>
  </div>
);

const FeatureCard = ({ icon: Icon, title, desc }) => (
  <div className="glass rounded-xl p-5 hover:-translate-y-1 transition-transform duration-200">
    <Icon strokeWidth={1.5} className="w-5 h-5 text-sky-400 mb-3" />
    <p className="font-display font-bold text-slate-100 text-base">{title}</p>
    <p className="font-body text-sm text-slate-400 mt-1">{desc}</p>
  </div>
);

const RoutingSkeleton = () => (
  <div className="glass-heavy rounded-2xl p-6 mb-6 fade-up" data-testid="routing-skeleton">
    <div className="flex items-center gap-3 mb-4">
      <Sparkles className="w-4 h-4 text-sky-400 beam" />
      <p className="font-mono text-xs uppercase tracking-widest text-sky-300">Routing in corso…</p>
    </div>
    <div className="space-y-2">
      <div className="h-2 rounded bg-slate-800/70 w-3/4 animate-pulse" />
      <div className="h-2 rounded bg-slate-800/70 w-full animate-pulse" />
      <div className="h-2 rounded bg-slate-800/70 w-5/6 animate-pulse" />
    </div>
  </div>
);
