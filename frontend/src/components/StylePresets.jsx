import { Camera, Palette, Cpu, Brush, Layers, Gem } from "lucide-react";

/**
 * Style presets. Selected styles are prepended to the prompt on submit as a
 * "Stile: X, Y." prefix — works uniformly for both text and image intents.
 */
export const STYLE_PRESETS = [
  { id: "photorealistic", label: "Fotorealistico", icon: Camera, modifier: "stile fotorealistico, iper-dettagliato, luce cinematografica" },
  { id: "flat", label: "Illustrazione Flat", icon: Palette, modifier: "stile illustrazione flat design, colori piatti, geometrico minimale" },
  { id: "cyberpunk", label: "Cyberpunk", icon: Cpu, modifier: "estetica cyberpunk, neon, atmosfera notturna, ambientazione futuristica" },
  { id: "watercolor", label: "Watercolor", icon: Brush, modifier: "acquerello morbido, bordi sfumati, palette pastello" },
  { id: "isometric", label: "Isometrico", icon: Layers, modifier: "vista isometrica 3D, colori tenui, dettagli precisi" },
  { id: "luxury", label: "Luxury Editorial", icon: Gem, modifier: "estetica luxury editoriale, tipografia raffinata, palette monocromatica sofisticata" },
];

export const StylePresets = ({ active, onChange }) => {
  const toggle = (id) => {
    if (active.includes(id)) onChange(active.filter((s) => s !== id));
    else onChange([...active, id]);
  };

  return (
    <div
      data-testid="style-presets"
      className="w-full max-w-4xl mx-auto px-4 pt-2 pb-1"
    >
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
        <span className="font-mono text-[10px] uppercase tracking-widest text-slate-500 shrink-0 mr-1">
          Stili
        </span>
        {STYLE_PRESETS.map(({ id, label, icon: Icon }) => {
          const on = active.includes(id);
          return (
            <button
              key={id}
              data-testid={`style-${id}`}
              onClick={() => toggle(id)}
              className={`shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-mono text-[11px] border transition-colors duration-200 ${
                on
                  ? "bg-sky-500/15 border-sky-500/40 text-sky-300"
                  : "bg-slate-900/50 border-slate-800 text-slate-400 hover:text-slate-100 hover:border-slate-700"
              }`}
            >
              <Icon strokeWidth={1.5} className="w-3 h-3" />
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export function applyStyleModifiers(prompt, activeIds) {
  if (!activeIds || activeIds.length === 0) return prompt;
  const mods = STYLE_PRESETS
    .filter((s) => activeIds.includes(s.id))
    .map((s) => s.modifier);
  if (mods.length === 0) return prompt;
  return `[Stile: ${mods.join(" · ")}]\n\n${prompt}`;
}
