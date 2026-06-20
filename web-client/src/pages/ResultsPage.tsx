import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { ApiError, apiClient } from "../api/client";
import type { RecommendRequest, RecommendResponse } from "../api/types";
import { Button } from "../components/Button";
import { RecipeCard } from "../components/RecipeCard";
import {
  loadRecommendationSession,
  saveRecommendationSession,
} from "../recommendations/session";

type ResultsLocationState = {
  response?: RecommendResponse;
  request?: RecommendRequest;
};

export function ResultsPage() {
  const location = useLocation();
  const state = location.state as ResultsLocationState | null;
  const storedSession = useMemo(() => loadRecommendationSession(), []);
  const initialRequest = state?.request ?? storedSession?.request ?? null;
  const initialResponse = state?.response ?? storedSession?.response ?? null;
  const [request, setRequest] = useState<RecommendRequest | null>(initialRequest);
  const [response, setResponse] = useState<RecommendResponse | null>(initialResponse);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  async function retryRecommendation() {
    if (!request) {
      return;
    }

    setError(null);
    setIsRetrying(true);
    try {
      const nextResponse = await apiClient.recommend(request);
      setResponse(nextResponse);
      setRequest(request);
      saveRecommendationSession({ request, response: nextResponse });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not retry recommendation.");
    } finally {
      setIsRetrying(false);
    }
  }

  if (!response) {
    return (
      <section className="page-section">
        <p className="eyebrow">Recipe suggestions</p>
        <h1>No results yet</h1>
        <p className="muted">Add pantry ingredients and describe what sounds good first.</p>
        <Link className="button button-primary inline-action" to="/app">
          Start cooking
        </Link>
      </section>
    );
  }

  return (
    <section className="page-section">
      <div className="results-header">
        <div>
          <p className="eyebrow">Recipe suggestions</p>
          <h1>Best matches</h1>
          {request ? <p className="muted">For: {request.query}</p> : null}
        </div>
        {request ? (
          <Button type="button" variant="secondary" onClick={retryRecommendation} disabled={isRetrying}>
            {isRetrying ? "Retrying..." : "Retry"}
          </Button>
        ) : null}
      </div>

      {error ? <p className="alert alert-error">{error}</p> : null}

      <div className="result-list">
        {response.results.length ? (
          response.results.map((recipe) => <RecipeCard key={recipe.id} recipe={recipe} />)
        ) : (
          <p className="empty-state">Dishify did not return any recipes for this search.</p>
        )}
      </div>

      <details className="stage-details">
        <summary>Pipeline details</summary>
        <div className="stage-grid">
          {response.stages.map((stage) => (
            <div className="stage-item" key={stage.name}>
              <span>{stage.name}</span>
              <strong data-status={stage.status}>{stage.status}</strong>
              <small>{stage.latency_ms} ms</small>
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}
