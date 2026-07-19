import { useCallback, useEffect, useState } from "react";
import { listSessions, getSessionMessages, deleteSession } from "@/lib/api";
import { Clock, Trash2, MessagesSquare } from "lucide-react";
import { toast } from "sonner";

export const SessionsPanel = ({ currentSessionId, onLoadSession, onNewSession, refreshKey }) => {
  const [sessions, setSessions] = useState([]);

  const load = useCallback(async () => {
    try {
      const s = await listSessions();
      setSessions(s);
    } catch (err) {
      console.warn("[SessionsPanel] Failed to load sessions:", err);
    }
  }, []);

  useEffect(() => { load(); }, [refreshKey, load]);

  const openSession = async (id) => {
    try {
      const msgs = await getSessionMessages(id);
      onLoadSession(id, msgs);
    } catch (err) {
      console.warn("[SessionsPanel] Failed to open session:", err);
      toast.error("Errore caricamento sessione");
    }
  };

  const remove = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Eliminare questa sessione?")) return;
    await deleteSession(id);
    toast.success("Sessione eliminata");
    load();
    if (id === currentSessionId) onNewSession();
  };

  return (
    <div className="px-3 py-2" data-testid="sessions-panel">
      <div className="flex items-center justify-between px-2 pb-2">
        <p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
          Sessioni
        </p>
        <button
          data-testid="new-session-btn"
          onClick={onNewSession}
          className="text-[10px] font-mono uppercase tracking-widest text-sky-400 hover:text-sky-300 transition-colors"
        >
          + Nuova
        </button>
      </div>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {sessions.length === 0 && (
          <p className="px-2 py-3 font-body text-xs text-slate-600">Nessuna sessione ancora.</p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            data-testid={`session-${s.id}`}
            onClick={() => openSession(s.id)}
            className={`group w-full text-left px-2.5 py-2 rounded-md transition-colors border cursor-pointer ${
              s.id === currentSessionId
                ? "bg-sky-500/10 border-sky-500/25 text-slate-100"
                : "border-transparent hover:bg-slate-800/40 text-slate-400"
            }`}
          >
            <div className="flex items-start gap-2">
              <MessagesSquare className="w-3.5 h-3.5 mt-0.5 shrink-0" strokeWidth={1.5} />
              <div className="min-w-0 flex-1">
                <p className="font-body text-xs truncate">{s.title || "Senza titolo"}</p>
                <p className="font-mono text-[9px] text-slate-600 flex items-center gap-1 mt-0.5">
                  <Clock className="w-2.5 h-2.5" strokeWidth={2} />
                  {s.turn_count || 0} turni · {s.last_model || "—"}
                </p>
              </div>
              <button
                data-testid={`delete-session-${s.id}`}
                onClick={(e) => remove(s.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-rose-500/10 text-slate-500 hover:text-rose-300 transition-all"
                title="Elimina"
              >
                <Trash2 className="w-3 h-3" strokeWidth={1.5} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
