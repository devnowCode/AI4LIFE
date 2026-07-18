import { useEffect, useState } from "react";
import { getArchive, removeFromArchive, clearArchive } from "@/lib/storage";
import { Trash2, Copy, ArchiveX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export const Archive = () => {
  const [items, setItems] = useState([]);

  useEffect(() => { setItems(getArchive()); }, []);

  const remove = (id) => setItems(removeFromArchive(id));
  const clearAll = () => { clearArchive(); setItems([]); toast.success("Archivio svuotato"); };
  const copyItem = async (t) => { await navigator.clipboard.writeText(t); toast.success("Copiato"); };

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-8 py-8 fade-up" data-testid="archive-view">
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-sky-400/80">Local Storage</p>
          <h1 className="font-display font-black text-3xl sm:text-4xl text-slate-50 tracking-tight mt-1">Archivio</h1>
          <p className="font-body text-slate-400 mt-2">{items.length} risultato/i salvato/i in locale.</p>
        </div>
        {items.length > 0 && (
          <Button
            data-testid="clear-archive-btn"
            onClick={clearAll}
            variant="outline"
            className="border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800 hover:text-slate-50"
          >
            <ArchiveX className="w-4 h-4 mr-1.5" strokeWidth={1.5} /> Svuota
          </Button>
        )}
      </header>

      {items.length === 0 ? (
        <div className="glass-heavy rounded-2xl p-12 text-center">
          <p className="font-body text-slate-400">Nessun risultato salvato. Usa <span className="text-sky-300">Salva</span> sotto ogni risposta.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((it) => (
            <article
              key={it.id}
              data-testid={`archive-item-${it.id}`}
              className="glass-heavy rounded-xl p-5"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="min-w-0">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                    {new Date(it.saved_at).toLocaleString("it-IT")} · {it.selected?.display_name}
                  </p>
                  <p className="font-body text-slate-200 text-sm mt-1 line-clamp-2">{it.prompt}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button data-testid={`archive-copy-${it.id}`} onClick={() => copyItem(it.result)} className="p-2 rounded-md text-slate-400 hover:text-sky-300 hover:bg-slate-800/60 transition-colors">
                    <Copy className="w-4 h-4" strokeWidth={1.5} />
                  </button>
                  <button data-testid={`archive-remove-${it.id}`} onClick={() => remove(it.id)} className="p-2 rounded-md text-slate-400 hover:text-rose-300 hover:bg-slate-800/60 transition-colors">
                    <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                  </button>
                </div>
              </div>
              <p className="font-body text-slate-300 text-sm whitespace-pre-wrap line-clamp-6">{it.result}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};
