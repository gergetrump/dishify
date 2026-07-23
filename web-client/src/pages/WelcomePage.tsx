import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { DishifyLogo } from "../components/DishifyLogo";

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

        <p className="muted welcome-intro">
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

        <div className="welcome-highlights">
          <span>Use leftovers</span>
          <span>Quick dinner ideas</span>
          <span>Personalized suggestions</span>
        </div>
      </div>

      <div className="welcome-logo-card" aria-hidden="true">
        <DishifyLogo size="hero" />
      </div>
    </section>
  );
}
