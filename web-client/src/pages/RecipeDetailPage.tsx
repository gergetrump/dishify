import { Link, useLocation, useParams } from "react-router-dom";

import type { RecipeResult } from "../api/types";
import { findRecipeById } from "../recommendations/session";

type DetailLocationState = {
  recipe?: RecipeResult;
};

export function RecipeDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const state = location.state as DetailLocationState | null;
  const recipeId = Number(id);
  const recipe = state?.recipe ?? (Number.isFinite(recipeId) ? findRecipeById(recipeId) : null);

  if (!recipe) {
    return (
      <section className="page-section">
        <p className="eyebrow">Recipe</p>
        <h1>Recipe not found</h1>
        <p className="muted">
          Recipe detail is available after choosing a recommendation from the latest results.
        </p>
        <Link className="button button-primary inline-action" to="/results">
          Back to results
        </Link>
      </section>
    );
  }

  const matched = recipe.inventory_matched ?? [];
  const missing = recipe.inventory_missing ?? [];
  const positive = recipe.reasoning?.positive ?? [];
  const negative = recipe.reasoning?.negative ?? [];
  const directions = recipe.directions ?? [];

  return (
    <section className="page-section">
      <p className="eyebrow">Recipe</p>
      <div className="detail-header">
        <div>
          <h1>{recipe.title ?? "Untitled recipe"}</h1>
          <div className="recipe-meta">
            {recipe.time_minutes ? <span>{recipe.time_minutes} min</span> : null}
            <span>Score {Math.round(recipe.score * 100)}</span>
            <span>Rank {recipe.rank}</span>
          </div>
        </div>
        <Link to="/results">Back to results</Link>
      </div>

      {recipe.summary ? <p className="detail-summary">{recipe.summary}</p> : null}

      <div className="detail-grid">
        <section className="detail-panel">
          <h2>Ingredient match</h2>
          <IngredientList title="You have" items={matched} empty="No matched ingredients returned." />
          <IngredientList title="You may need" items={missing} empty="No missing ingredients returned." />
        </section>

        <section className="detail-panel">
          <h2>Reasoning</h2>
          <ReasoningList title="Why it fits" items={positive} empty="No positive reasoning returned." />
          <ReasoningList title="Watch for" items={negative} empty="No concerns returned." />
        </section>
      </div>

      <section className="directions-panel">
        <h2>Directions</h2>
        {directions.length ? (
          <ol className="directions-list">
            {directions.map((step, index) => (
              <li key={`${index}-${step}`}>{step}</li>
            ))}
          </ol>
        ) : (
          <p className="empty-state">No directions were returned for this recipe.</p>
        )}
      </section>
    </section>
  );
}

function IngredientList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="detail-list-group">
      <h3>{title}</h3>
      {items.length ? (
        <div className="tag-list">
          {items.map((item) => (
            <span className="tag" key={item}>
              {item}
            </span>
          ))}
        </div>
      ) : (
        <p className="muted">{empty}</p>
      )}
    </div>
  );
}

function ReasoningList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="detail-list-group">
      <h3>{title}</h3>
      {items.length ? (
        <ul className="reasoning-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">{empty}</p>
      )}
    </div>
  );
}
