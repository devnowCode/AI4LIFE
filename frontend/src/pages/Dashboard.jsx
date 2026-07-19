import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Sidebar, MobileNav } from "@/components/Sidebar";
import { PromptDock } from "@/components/PromptDock";
import { ResponseCard } from "@/components/ResponseCard";
import { CompareCard } from "@/components/CompareCard";
import { ModelRegistry } from "@/components/ModelRegistry";
import { Archive } from "@/components/Archive";
import { Settings } from "@/components/Settings";
import { Telemetry } from "@/components/Telemetry";
import { StylePresets, applyStyleModifiers } from "@/components/StylePresets";
import { RecipesStrip } from "@/components/RecipesStrip";
import { fetchModels, orchestrateStream, compare, fileToBase64 } from "@/lib/api";
import { getWeights, getActiveStyles, setActiveStyles } from "@/lib/settings";
import { Brain, Layers3, GitBranch, ChevronDown, ChevronUp } from "lucide-react";

const SHORTCUTS_COLLAPSED_KEY = "ai4life_shortcuts_collapsed_v1";

export default function Dashboard() {
  const [view, setView] = useState("chat");
  const [models, setModels] = useState([]);
  const [forcedModel, setForcedModel] = useState(null);
  const [entries, setEntries] = useState([]);
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [sessionsRefresh, setSessionsRefresh] = useState(0);

  // Compare mode state
  const [compareMode, setCompareMode] = useState(false);
  const [compareModels, setCompareModels] = useState(["gpt-5.2", "claude-sonnet-4.5", "gemini-3-flash"]);

  // Style presets
  const [activeStyles, setActiveStylesState] = useState(() => getActiveStyles());
  const updateStyles = (list) => {
    setActiveStylesState(list);
    setActiveStyles(list);
  };

  // Recipes: when applied, we set active recipe id + fill prompt via a controlled prop
  const [activeRecipeId, setActiveRecipeId] = useState(null);
  const [pendingPrompt, setPendingPrompt] = useState(null);
  const [pendingWeightsOverride, setPendingWeightsOverride] = useState(null);

  // Shortcut strips collapse state (icon-only mode). Persist across reloads.
  // Default: collapsed on mobile (<768px), expanded on desktop.
  const [shortcutsCollapsed, setShortcutsCollapsedState] = useState(() => {
    try {
      const stored = localStorage.getItem(SHORTCUTS_COLLAPSED_KEY);
      if (stored !== null) return stored === "true";
    } catch { /* noop */ }
    return typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;
  });
  const toggleShortcuts = () => {
    setShortcutsCollapsedState((prev) => {
      const next = !prev;
      try { localStorage.setItem(SHORTCUTS_COLLAPSED_KEY, String(next)); } catch { /* noop */ }
      return next;
    });
  };

  const applyRecipe = (recipe) => {
    setActiveRecipeId(recipe.id);
    setPendingPrompt(recipe.template);
    if (recipe.styles && recipe.styles.length) updateStyles(recipe.styles);
    if (recipe.weights_hint) setPendingWeightsOverride(recipe.weights_hint);
    toast.success(`Ricetta applicata: ${recipe.label}`);
  };

  useEffect(() => {
    fetchModels()
      .then((r) => setModels(r.models))
      .catch((err) => console.warn("[Dashboard] Failed to fetch models:", err));
  }, []);

  const bumpSessions = () => setSessionsRefresh((n) => n + 1);

  const handleNewSession = () => {
    setSessionId(crypto.randomUUID());
    setEntries([]);
    setForcedModel(null);
    setCompareMode(false);
  };

  const handleLoadSession = (id, messages) => {
    setSessionId(id);
    // Rehydrate entries from server messages (latest-first)
    const rehydrated = (messages || []).map((m) => ({
      ts: new Date(m.created_at).getTime(),
      prompt: m.prompt,
      result: m.result,
      insight: m.insight,
      intent: m.intent,
      routing: { selected: m.routing_selected, candidates: [] },
      images: m.images || [],
    }));
    setEntries(rehydrated.reverse());
    setView("chat");
  };

  const handleSubmit = async ({ text, files }) => {
    setBusy(true);
    // Prefer recipe weight hint if just applied, else settings weights
    const weights = pendingWeightsOverride || getWeights();
    setPendingWeightsOverride(null);
    setActiveRecipeId(null);
    try {
      const filePayloads = await Promise.all(files.map(fileToBase64));
      const finalPrompt = applyStyleModifiers(text, activeStyles);

      if (compareMode) {
        if (compareModels.length < 2) {
          toast.error("Seleziona almeno 2 modelli per il confronto");
          setBusy(false);
          return;
        }
        const res = await compare({
          prompt: finalPrompt,
          model_ids: compareModels,
          files: filePayloads,
          session_id: sessionId,
        });
        setEntries((prev) => [
          { compare: true, prompt: text, results: res.results, ts: Date.now() },
          ...prev,
        ]);
      } else {
        const entryTs = Date.now();
        setEntries((prev) => [
          { ts: entryTs, prompt: text || "(solo allegati)", result: "", insight: "", intent: null, routing: null, streaming: true, images: [] },
          ...prev,
        ]);

        await orchestrateStream(
          {
            prompt: finalPrompt,
            files: filePayloads,
            force_model_id: forcedModel || undefined,
            session_id: sessionId,
            weights_override: weights,
          },
          {
            onMeta: (meta) => {
              setEntries((prev) => prev.map((e) =>
                e.ts === entryTs
                  ? { ...e, intent: meta.intent, routing: meta.routing, insight: meta.insight }
                  : e
              ));
            },
            onToken: (delta) => {
              setEntries((prev) => prev.map((e) =>
                e.ts === entryTs ? { ...e, result: (e.result || "") + delta } : e
              ));
            },
            onImages: (images) => {
              setEntries((prev) => prev.map((e) =>
                e.ts === entryTs ? { ...e, images } : e
              ));
            },
            onDone: (evt) => {
              setEntries((prev) => prev.map((e) =>
                e.ts === entryTs
                  ? { ...e, streaming: false, result: evt.result || e.result, costEur: evt.cost_estimate_eur, latencyMs: evt.latency_ms }
                  : e
              ));
              bumpSessions();
            },
            onError: (err) => {
              toast.error("Errore stream: " + err.message);
              setEntries((prev) => prev.map((e) =>
                e.ts === entryTs ? { ...e, streaming: false, result: (e.result || "") + `\n\n[Errore: ${err.message}]` } : e
              ));
            },
          }
        );
      }
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
      <Sidebar
        active={view}
        onChange={setView}
        currentSessionId={sessionId}
        onLoadSession={handleLoadSession}
        onNewSession={handleNewSession}
        sessionsRefreshKey={sessionsRefresh}
      />

      <main className="flex-1 flex flex-col min-w-0 relative z-10">
        <MobileNav active={view} onChange={setView} />

        {view === "chat" && (
          <ChatView entries={entries} busy={busy} onRework={handleRework} models={models} />
        )}
        {view === "registry" && <ModelRegistry />}
        {view === "settings" && <Settings />}
        {view === "telemetry" && <Telemetry />}
        {view === "archive" && <Archive />}

        {view === "chat" && (
          <div className="sticky bottom-0 left-0 right-0 pointer-events-none z-20">
            <div
              className="pointer-events-auto pt-2"
              style={{
                background: "linear-gradient(to bottom, rgba(3,7,18,0.4) 0%, rgba(3,7,18,0.9) 12%, rgba(3,7,18,0.98) 30%, rgba(3,7,18,1) 100%)",
                backdropFilter: "blur(24px)",
                WebkitBackdropFilter: "blur(24px)",
              }}
            >
              <div className="w-full max-w-4xl mx-auto px-4 pt-0 pb-0 flex justify-end">
                <button
                  data-testid="toggle-shortcuts-btn"
                  onClick={toggleShortcuts}
                  title={shortcutsCollapsed ? "Espandi scorciatoie" : "Comprimi scorciatoie"}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono uppercase tracking-widest text-slate-500 hover:text-sky-300 hover:bg-slate-800/40 transition-colors"
                >
                  {shortcutsCollapsed
                    ? <><ChevronUp className="w-3 h-3" strokeWidth={2} /> Espandi</>
                    : <><ChevronDown className="w-3 h-3" strokeWidth={2} /> Comprimi</>}
                </button>
              </div>
              <RecipesStrip
                onApply={applyRecipe}
                activeRecipeId={activeRecipeId}
                compact={shortcutsCollapsed}
              />
              <StylePresets
                active={activeStyles}
                onChange={updateStyles}
                compact={shortcutsCollapsed}
              />
              <PromptDock
                onSubmit={handleSubmit}
                busy={busy}
                models={models}
                forced={forcedModel}
                onForcedChange={setForcedModel}
                compareMode={compareMode}
                onToggleCompare={() => setCompareMode((v) => !v)}
                compareModels={compareModels}
                onCompareModelsChange={setCompareModels}
                pendingPrompt={pendingPrompt}
                onPendingConsumed={() => setPendingPrompt(null)}
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
    <div className="max-w-4xl mx-auto px-4 md:px-8 pt-10 pb-56 md:pb-48">
      {entries.length === 0 && !busy && <EmptyState models={models} />}

      <div className="space-y-6">
        {entries.map((entry) =>
          entry.compare ? (
            <CompareCard key={entry.ts} prompt={entry.prompt} results={entry.results} />
          ) : (
            <ResponseCard key={entry.ts} entry={entry} onRework={onRework} />
          )
        )}
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
      al modello più adatto — restituendo Risultato + Insight tecnico in streaming.
    </p>

    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-10">
      <FeatureCard icon={Brain} title="Intent Recognition" desc="Analisi semantica del prompt in tempo reale." />
      <FeatureCard icon={GitBranch} title="Semantic Routing" desc="Matrice di pesi capability × latency × cost." />
      <FeatureCard icon={Layers3} title="Dual Output + Compare" desc="Risultato, Insight tecnico, e Comparison Mode." />
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
