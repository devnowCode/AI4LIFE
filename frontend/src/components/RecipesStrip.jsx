import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import * as Icons from "lucide-react";
import { Sparkles } from "lucide-react";

/**
 * Prompt Recipe library. Chip row above PromptDock. Clicking a recipe:
 *  - Fills the prompt input with the template
 *  - Applies the recipe's style presets
 *  - Applies weight hints (temporary — not persisted to Settings)
 */
export const RecipesStrip = ({ onApply, activeRecipeId }) => {
  const [recipes, setRecipes] = useState([]);

  useEffect(() => {
    api.get("/recipes")
      .then(({ data }) => setRecipes(data.recipes || []))
      .catch((err) => console.warn("[RecipesStrip] Failed to load recipes:", err));
  }, []);

  if (recipes.length === 0) return null;

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pt-2 pb-0" data-testid="recipes-strip">
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
        <span className="font-mono text-[10px] uppercase tracking-widest text-sky-400/80 shrink-0 mr-1 flex items-center gap-1">
          <Sparkles className="w-3 h-3" strokeWidth={2} /> Ricette
        </span>
        {recipes.map((r) => {
          const Icon = Icons[r.icon] || Icons.FileText;
          const active = activeRecipeId === r.id;
          return (
            <button
              key={r.id}
              data-testid={`recipe-${r.id}`}
              onClick={() => onApply(r)}
              title={`${r.category} · ${r.label}`}
              className={`shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-mono text-[11px] border transition-colors duration-200 ${
                active
                  ? "bg-sky-500/15 border-sky-500/40 text-sky-300"
                  : "bg-slate-900/50 border-slate-800 text-slate-400 hover:text-slate-100 hover:border-slate-700"
              }`}
            >
              <Icon strokeWidth={1.5} className="w-3 h-3" />
              {r.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
