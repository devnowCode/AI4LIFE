import { useState } from "react";
import { Copy, Save, RefreshCw, Share2, Sparkles, Terminal, Check } from "lucide-react";
import { RouterPill } from "./RouterPill";
import { toast } from "sonner";
import { saveToArchive } from "@/lib/storage";

const Markdown = ({ text }) => {
  // Ultra-lightweight rendering: preserve line breaks + code fences visually.
  if (!text) return null;
  const parts = String(text).split(/(```[\s\S]*?```)/g);
  return (
    <div className="space-y-3">
      {parts.map((chunk, i) => {
        if (chunk.startsWith("```")) {
          const body = chunk.replace(/^```[a-z]*\n?/, "").replace(/```$/, "");
          return (
            <pre
              key={i}
              className="font-mono text-xs bg-slate-950/70 border border-slate-800 rounded-lg p-4 overflow-x-auto text-sky-100/90 leading-relaxed"
            >
              {body}
            </pre>
          );
        }
        return (
          <p key={i} className="font-body text-[15px] leading-[1.7] text-slate-200 whitespace-pre-wrap">
            {chunk}
          </p>
        );
      })}
    </div>
  );
};

export const ResponseCard = ({ entry, onRework }) => {
  const [tab, setTab] = useState("result");
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  const { intent, routing, result, insight, prompt } = entry;
  const selected = routing?.selected;

  const copy = async () => {
    await navigator.clipboard.writeText(result || "");
    setCopied(true);
    toast.success("Risultato copiato negli appunti");
    setTimeout(() => setCopied(false), 1500);
  };

  const save = () => {
    saveToArchive({ prompt, result, insight, selected, intent });
    setSaved(true);
    toast.success("Salvato nell'Archivio");
    setTimeout(() => setSaved(false), 1500);
  };

  const share = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title: "AI4LIFE", text: result?.slice(0, 200), url });
        return;
      } catch { /* fallback below */ }
    }
    await navigator.clipboard.writeText(`${prompt}\n\n${result}`);
    toast.success("Contenuto copiato per condivisione");
  };

  return (
    <article
      data-testid="response-card"
      className="glass-heavy rounded-2xl overflow-hidden fade-up"
    >
      {/* Header: prompt echo + routing pill */}
      <header className="px-6 pt-5 pb-4 border-b border-slate-800/60">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500 mb-1">Richiesta</p>
            <p className="font-body text-slate-300 text-sm line-clamp-2">{prompt || "(solo allegati)"}</p>
          </div>
          <RouterPill selected={selected} />
        </div>
      </header>

      {/* Tabs */}
      <div className="px-6 pt-4">
        <div className="inline-flex items-center gap-1 rounded-lg bg-slate-900/60 border border-slate-800 p-1">
          <TabBtn active={tab === "result"} onClick={() => setTab("result")} icon={Sparkles} label="Risultato" testid="tab-result" />
          <TabBtn active={tab === "insight"} onClick={() => setTab("insight")} icon={Terminal} label="Insight" testid="tab-insight" />
        </div>
      </div>

      <div className="px-6 py-5 min-h-[100px]">
        {tab === "result" ? (
          <>
            {entry.images && entry.images.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4" data-testid="generated-images">
                {entry.images.map((img, i) => (
                  <a
                    key={i}
                    href={img.data_url}
                    download={`ai4life-${i}.png`}
                    className="block rounded-xl overflow-hidden border border-slate-800 hover:border-sky-500/50 transition-colors"
                    data-testid={`generated-image-${i}`}
                  >
                    <img src={img.data_url} alt={`Generated ${i}`} className="w-full h-auto object-cover" />
                  </a>
                ))}
              </div>
            )}
            <Markdown text={result} />
          </>
        ) : (
          <pre
            data-testid="insight-content"
            className="font-mono text-xs text-sky-200/90 bg-slate-950/60 border border-slate-800 rounded-lg p-5 overflow-x-auto leading-relaxed whitespace-pre-wrap"
          >
            {insight}
          </pre>
        )}
      </div>

      {/* Quick Action Bar */}
      <footer className="px-4 py-3 border-t border-slate-800/60 flex flex-wrap items-center justify-end gap-1 bg-slate-950/40">
        <QuickAction icon={copied ? Check : Copy} label="Copia" onClick={copy} testid="action-copy" active={copied} />
        <QuickAction icon={saved ? Check : Save} label="Salva" onClick={save} testid="action-save" active={saved} />
        <QuickAction icon={RefreshCw} label="Rielabora" onClick={() => onRework?.(entry)} testid="action-rework" />
        <QuickAction icon={Share2} label="Condividi" onClick={share} testid="action-share" />
      </footer>
    </article>
  );
};

const TabBtn = ({ active, onClick, icon: Icon, label, testid }) => (
  <button
    data-testid={testid}
    onClick={onClick}
    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-body transition-colors ${
      active ? "bg-sky-500/15 text-sky-300 border border-sky-500/25" : "text-slate-400 hover:text-slate-100 border border-transparent"
    }`}
  >
    <Icon strokeWidth={1.5} className="w-3.5 h-3.5" />
    {label}
  </button>
);

const QuickAction = ({ icon: Icon, label, onClick, testid, active }) => (
  <button
    data-testid={testid}
    onClick={onClick}
    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-body transition-colors ${
      active ? "text-sky-300 bg-sky-500/10" : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
    }`}
  >
    <Icon strokeWidth={1.5} className="w-3.5 h-3.5" />
    {label}
  </button>
);
