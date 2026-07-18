import { useState, useRef } from "react";
import { Paperclip, ArrowUp, X, FileText, Image as ImageIcon, GitCompareArrows } from "lucide-react";
import { Button } from "@/components/ui/button";

export const PromptDock = ({
  onSubmit,
  busy,
  models,
  forced,
  onForcedChange,
  compareMode,
  onToggleCompare,
  compareModels,
  onCompareModelsChange,
}) => {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const fileRef = useRef(null);

  const handleFiles = (list) => {
    const arr = Array.from(list || []).slice(0, 5);
    setFiles((prev) => [...prev, ...arr].slice(0, 5));
  };

  const submit = () => {
    if (busy) return;
    if (!text.trim() && files.length === 0) return;
    onSubmit({ text: text.trim(), files });
    setText("");
    setFiles([]);
  };

  const onKey = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
  };

  const toggleCompareModel = (id) => {
    if (compareModels.includes(id)) {
      onCompareModelsChange(compareModels.filter((m) => m !== id));
    } else if (compareModels.length < 4) {
      onCompareModelsChange([...compareModels, id]);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-6 pt-2">
      {compareMode && (
        <div
          data-testid="compare-model-picker"
          className="glass rounded-xl p-3 mb-2 flex flex-wrap items-center gap-2"
        >
          <span className="font-mono text-[10px] uppercase tracking-widest text-sky-400/80 mr-1">
            Compare:
          </span>
          {(models || []).filter((m) => m.type === "text").map((m) => {
            const on = compareModels.includes(m.id);
            return (
              <button
                key={m.id}
                data-testid={`compare-toggle-${m.id}`}
                onClick={() => toggleCompareModel(m.id)}
                className={`px-2.5 py-1 rounded-md font-mono text-[11px] border transition-colors ${
                  on
                    ? "bg-sky-500/15 border-sky-500/40 text-sky-300"
                    : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-100"
                }`}
              >
                {m.display_name}
              </button>
            );
          })}
          <span className="ml-auto font-mono text-[10px] text-slate-500">
            {compareModels.length}/4 selezionati (min 2)
          </span>
        </div>
      )}

      <div className="glass-heavy rounded-2xl p-3 relative" data-testid="prompt-dock">
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {files.map((f, i) => (
              <div
                key={i}
                data-testid={`file-chip-${i}`}
                className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-800/60 border border-slate-700/50 text-xs font-mono text-slate-300"
              >
                {f.type.startsWith("image/") ? (
                  <ImageIcon strokeWidth={1.5} className="w-3.5 h-3.5 text-sky-400" />
                ) : (
                  <FileText strokeWidth={1.5} className="w-3.5 h-3.5 text-sky-400" />
                )}
                <span className="max-w-[180px] truncate">{f.name}</span>
                <button
                  data-testid={`remove-file-${i}`}
                  onClick={() => setFiles(files.filter((_, j) => j !== i))}
                  className="hover:text-slate-100"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <textarea
          data-testid="prompt-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          placeholder={
            compareMode
              ? "Compare mode — la query verrà inviata ai modelli selezionati…"
              : "Chiedi qualsiasi cosa — l'orchestratore sceglie il modello ottimale…"
          }
          rows={2}
          className="w-full resize-none bg-transparent outline-none font-body text-slate-100 placeholder:text-slate-500 text-[15px] leading-relaxed px-2 py-1"
        />

        <div className="flex items-center justify-between mt-2 gap-2 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".pdf,image/*,.txt"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
              data-testid="file-input"
            />
            <button
              data-testid="attach-file-btn"
              onClick={() => fileRef.current?.click()}
              className="p-2 rounded-lg text-slate-400 hover:text-sky-300 hover:bg-slate-800/50 transition-colors"
              title="Allega PDF, immagini o testo"
            >
              <Paperclip strokeWidth={1.5} className="w-4 h-4" />
            </button>

            <button
              data-testid="compare-mode-toggle"
              onClick={onToggleCompare}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-mono uppercase tracking-widest border transition-colors ${
                compareMode
                  ? "bg-sky-500/15 border-sky-500/40 text-sky-300"
                  : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-100"
              }`}
              title="Compara stessa query su più modelli"
            >
              <GitCompareArrows strokeWidth={1.5} className="w-3.5 h-3.5" />
              Compare
            </button>

            {!compareMode && (
              <select
                data-testid="force-model-select"
                value={forced || ""}
                onChange={(e) => onForcedChange(e.target.value || null)}
                className="bg-slate-900/70 border border-slate-800 rounded-lg px-2 py-1.5 text-xs font-mono text-slate-300 outline-none focus:border-sky-500/50"
              >
                <option value="">Auto-Route</option>
                {(models || []).map((m) => (
                  <option key={m.id} value={m.id}>{m.display_name}</option>
                ))}
              </select>
            )}

            <span className="hidden sm:inline text-[10px] font-mono uppercase tracking-widest text-slate-600">
              ⌘ + ↵ per inviare
            </span>
          </div>

          <Button
            data-testid="send-prompt-btn"
            onClick={submit}
            disabled={busy || (!text.trim() && files.length === 0) || (compareMode && compareModels.length < 2)}
            className="h-9 px-4 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold font-body disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {busy ? "Routing…" : (
              <>
                Invia <ArrowUp className="w-4 h-4 ml-1.5" strokeWidth={2.5} />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};
