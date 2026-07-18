import { Layers, MessagesSquare, Archive, Database, Zap, Settings as SettingsIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { SessionsPanel } from "./SessionsPanel";

const NAV = [
  { id: "chat", label: "Orchestratore", icon: MessagesSquare, testid: "nav-chat" },
  { id: "registry", label: "Model Registry", icon: Database, testid: "nav-registry" },
  { id: "settings", label: "Weights", icon: SettingsIcon, testid: "nav-settings" },
  { id: "archive", label: "Archivio", icon: Archive, testid: "nav-archive" },
];

export const Sidebar = ({ active, onChange, currentSessionId, onLoadSession, onNewSession, sessionsRefreshKey }) => {
  return (
    <aside
      data-testid="sidebar"
      className="hidden md:flex md:flex-col w-64 shrink-0 border-r border-slate-800/60 glass-heavy relative z-10"
    >
      <div className="px-6 pt-8 pb-6">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 grid place-items-center">
              <Layers strokeWidth={1.75} className="w-5 h-5 text-slate-950" />
            </div>
            <span className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-sky-400 beam" />
          </div>
          <div>
            <p className="font-display font-black text-lg leading-none tracking-tight text-slate-50">AI4LIFE</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-sky-400/80 mt-1">The Orchestrator</p>
          </div>
        </div>
      </div>

      <nav className="px-3 space-y-1">
        {NAV.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              data-testid={item.testid}
              onClick={() => onChange(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors duration-200",
                isActive
                  ? "bg-sky-500/10 text-sky-300 border border-sky-500/25"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 border border-transparent"
              )}
            >
              <Icon strokeWidth={1.5} className="w-4 h-4" />
              <span className="font-body text-sm font-medium">{item.label}</span>
              {isActive && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-sky-400 beam" />}
            </button>
          );
        })}
      </nav>

      <div className="mt-4 flex-1 min-h-0 border-t border-slate-800/60 pt-3 overflow-hidden">
        <SessionsPanel
          currentSessionId={currentSessionId}
          onLoadSession={onLoadSession}
          onNewSession={onNewSession}
          refreshKey={sessionsRefreshKey}
        />
      </div>

      <div className="p-4 mt-auto">
        <div className="glass rounded-xl p-3 flex items-center gap-3">
          <img
            src="https://images.unsplash.com/photo-1764545973653-94c40d993495?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzZ8MHwxfHNlYXJjaHwyfHxwcm9mZXNzaW9uYWwlMjBhdmF0YXIlMjBwb3J0cmFpdCUyMGRhcmslMjBiYWNrZ3JvdW5kfGVufDB8fHx8MTc4NDQwNjEzOXww&ixlib=rb-4.1.0&q=85"
            alt="user"
            className="w-9 h-9 rounded-lg object-cover ring-1 ring-slate-700"
          />
          <div className="min-w-0">
            <p className="font-body text-sm text-slate-100 truncate">Enterprise User</p>
            <p className="font-mono text-[10px] text-slate-500 flex items-center gap-1">
              <Zap className="w-3 h-3 text-sky-400" strokeWidth={2} /> Universal Key attiva
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};

export const MobileNav = ({ active, onChange }) => (
  <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-slate-800/60 glass-heavy sticky top-0 z-20">
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-400 to-blue-600 grid place-items-center">
        <Layers strokeWidth={1.75} className="w-4 h-4 text-slate-950" />
      </div>
      <p className="font-display font-black text-base text-slate-50">AI4LIFE</p>
    </div>
    <div className="flex gap-1">
      {NAV.map((item) => (
        <button
          key={item.id}
          data-testid={`${item.testid}-mobile`}
          onClick={() => onChange(item.id)}
          className={cn(
            "px-2.5 py-1.5 rounded-md text-xs font-body transition-colors",
            active === item.id ? "bg-sky-500/15 text-sky-300" : "text-slate-400"
          )}
        >
          <item.icon strokeWidth={1.5} className="w-4 h-4" />
        </button>
      ))}
    </div>
  </div>
);
