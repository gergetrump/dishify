import { Link } from "react-router-dom";

import type { RecipeResult } from "../api/types";

type RecipeCardProps = {
  recipe: RecipeResult;
};

export function RecipeCard({ recipe }: RecipeCardProps) {
  const matched = recipe.inventory_matched ?? [];
  const missing = recipe.inventory_missing ?? [];
  const positive = recipe.reasoning?.positive ?? [];
  const negative = recipe.reasoning?.negative ?? [];

  return (
    <article className="recipe-card">
      <div className="recipe-card-header">
        <div>
          <p className="eyebrow">Rank {recipe.rank}</p>
          <h3>{recipe.title ?? "Untitled recipe"}</h3>
          <div className="recipe-meta">
            {recipe.time_minutes ? <span>{recipe.time_minutes} min</span> : null}
            <span>Score {Math.round(recipe.score * 100)}</span>
          </div>
        </div>
        <strong className="score">{Math.round(recipe.score * 100)}</strong>
      </div>

      {recipe.summary ? <p className="muted">{recipe.summary}</p> : null}

      <div className="reasoning-preview">
        {positive.length ? (
          <div>
            <h4>Why it fits</h4>
            <ul>
              {positive.slice(0, 2).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {negative.length ? (
          <div>
            <h4>Watch for</h4>
            <ul>
              {negative.slice(0, 2).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <div className="tag-list">
        {matched.slice(0, 4).map((item) => (
          <span className="tag tag-good" key={`matched-${item}`}>
            Have {item}
          </span>
        ))}
        {missing.slice(0, 4).map((item) => (
          <span className="tag tag-warn" key={`missing-${item}`}>
            Need {item}
          </span>
        ))}
      </div>

      <div className="ingredient-summary">
        <span>{matched.length} matched</span>
        <span>{missing.length} missing</span>
        <Link to={`/recipes/${recipe.id}`} state={{ recipe }}>
          View recipe
        </Link>
      </div>
    </article>
  );
}
