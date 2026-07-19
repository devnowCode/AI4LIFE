import { useState } from "react";
import { Copy, Save, RefreshCw, Share2, Sparkles, Terminal, Check } from "lucide-react";
import { RouterPill } from "./RouterPill";
import { toast } from "sonner";
import { saveToArchive } from "@/lib/storage";

const Markdown = ({ text }) => {
  if (!text) return null;
  const parts = String(text).split(/(```[\s\S]*?```)/g);
  return (
    <div className="space-y-3">
      {parts.map((chunk, i) => {
        // Stable-ish key: index + short content hash. Chunk list order is deterministic
        // for the same input, so index alone would work, but this survives concurrent renders.
        const k = `${i}-${chunk.length}-${chunk.charCodeAt(0) || 0}`;
        if (chunk.startsWith("```")) {
          const body = chunk.replace(/^```[a-z]*\n?/, "").replace(/```$/, "");
          return (
            <pre
              key={k}
              className="font-mono text-xs bg-slate-950/70 border border-slate-800 rounded-lg p-4 overflow-x-auto text-sky-100/90 leading-relaxed"
            >
              {body}
            </pre>
          );
        }
        return (
          <p key={k} className="font-body text-[15px] leading-[1.7] text-slate-200 whitespace-pre-wrap">
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

  const { intent, routing, result, insight, prompt, streaming, images, costEur, latencyMs } = entry;
  const selected = routing?.selected;

  const copy = async () => {
    await navigator.clipboard.writeText(result || "");
    setCopied(true);
    toast.success("Risultato copiato negli appunti");
    setTimeout(() => setCopied(false), 1500);
  };

  const save = () => {
    saveToArchive({ prompt, result, insight, selected, intent, images });
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
      } catch (err) {
        console.warn("[ResponseCard] Web Share failed, falling back to clipboard:", err);
      }
    }
    await navigator.clipboard.writeText(`${prompt}\n\n${result}`);
    toast.success("Contenuto copiato per condivisione");
  };

  return (
    <article
      data-testid="response-card"
      className="glass-heavy rounded-2xl overflow-hidden fade-up"
    >
      <header className="px-6 pt-5 pb-4 border-b border-slate-800/60">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500 mb-1">Richiesta</p>
            <p className="font-body text-slate-300 text-sm line-clamp-2">{prompt || "(solo allegati)"}</p>
          </div>
          {selected && <RouterPill selected={selected} costEur={costEur} latencyMs={latencyMs} />}
        </div>
      </header>

      <div className="px-6 pt-4">
        <div className="inline-flex items-center gap-1 rounded-lg bg-slate-900/60 border border-slate-800 p-1">
          <TabBtn active={tab === "result"} onClick={() => setTab("result")} icon={Sparkles} label="Risultato" testid="tab-result" />
          <TabBtn active={tab === "insight"} onClick={() => setTab("insight")} icon={Terminal} label="Insight" testid="tab-insight" />
          {streaming && (
            <span className="ml-2 inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-sky-500/10 border border-sky-500/25 text-[10px] font-mono uppercase tracking-widest text-sky-300">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 beam" /> Streaming
            </span>
          )}
        </div>
      </div>

      <div className="px-6 py-5 min-h-[100px]">
        {tab === "result" ? (
          <>
            {images && images.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4" data-testid="generated-images">
                {images.map((img, i) => (
                  <a
                    key={img.data_url.slice(-64)}
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
            {streaming && (
              <span className="inline-block w-2 h-4 ml-0.5 bg-sky-400 animate-pulse align-middle" />
            )}
          </>
        ) : (
          <pre
            data-testid="insight-content"
            className="font-mono text-xs text-sky-200/90 bg-slate-950/60 border border-slate-800 rounded-lg p-5 overflow-x-auto leading-relaxed whitespace-pre-wrap"
          >
            {insight || "In attesa del routing…"}
          </pre>
        )}
      </div>

      <footer className="px-4 py-3 border-t border-slate-800/60 flex flex-wrap items-center justify-end gap-1 bg-slate-950/40">
        <QuickAction icon={copied ? Check : Copy} label="Copia" onClick={copy} testid="action-copy" active={copied} disabled={streaming} />
        <QuickAction icon={saved ? Check : Save} label="Salva" onClick={save} testid="action-save" active={saved} disabled={streaming} />
        <QuickAction icon={RefreshCw} label="Rielabora" onClick={() => onRework?.(entry)} testid="action-rework" disabled={streaming} />
        <QuickAction icon={Share2} label="Condividi" onClick={share} testid="action-share" disabled={streaming} />
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

const QuickAction = ({ icon: Icon, label, onClick, testid, active, disabled }) => (
  <button
    data-testid={testid}
    onClick={onClick}
    disabled={disabled}
    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-body transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
      active ? "text-sky-300 bg-sky-500/10" : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
    }`}
  >
    <Icon strokeWidth={1.5} className="w-3.5 h-3.5" />
    {label}
  </button>
);
