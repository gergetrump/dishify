import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

export function WelcomePage() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  return (
    <section className="welcome-page">
      <div className="welcome-copy">
        <p className="eyebrow">Dishify</p>
        <h1>Your next meal is already in your kitchen.</h1>
        <p className="muted">
          Add what you have, set the foods you avoid, and get recipe ideas that fit your pantry.
        </p>
        <div className="welcome-actions">
          <Link className="button button-primary" to="/register">
            Sign up
          </Link>
          <Link className="button button-secondary" to="/login">
            Log in
          </Link>
        </div>
      </div>
      <div className="mascot-card" aria-hidden="true">
        <span className="food-shape food-shape-orange" />
        <span className="food-shape food-shape-red" />
        <span className="food-shape food-shape-green" />
      </div>
    </section>
  );
}
