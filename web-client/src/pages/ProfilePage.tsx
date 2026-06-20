import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/Button";

export function ProfilePage() {
  const { loadUser, logout, user } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(!user);

  useEffect(() => {
    let isMounted = true;

    async function refreshProfile() {
      setError(null);
      setIsLoading(true);

      try {
        await loadUser();
      } catch (err) {
        if (isMounted) {
          setError(err instanceof ApiError ? err.message : "Could not load your profile.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void refreshProfile();

    return () => {
      isMounted = false;
    };
  }, [loadUser]);

  return (
    <section className="narrow-page">
      <p className="eyebrow">Account</p>
      <h1>Profile</h1>
      {error ? <p className="alert alert-error">{error}</p> : null}
      {isLoading ? <p className="muted">Loading your profile...</p> : null}
      <div className="profile-list">
        <div>
          <span>Username</span>
          <strong>{user?.username ?? "Not loaded"}</strong>
        </div>
        <div>
          <span>Email</span>
          <strong>{user?.email ?? "Not loaded"}</strong>
        </div>
        <div>
          <span>Email verified</span>
          <strong>{formatBoolean(user?.email_verified)}</strong>
        </div>
      </div>
      <div className="profile-actions">
        <Link className="button button-primary" to="/preferences">
          Food preferences
        </Link>
        <Button type="button" variant="secondary" onClick={logout}>
          Log out
        </Button>
      </div>
      <p className="muted profile-note">
        Password changes and account deletion are not available in the backend yet.
      </p>
    </section>
  );
}

function formatBoolean(value: boolean | null | undefined) {
  if (value == null) {
    return "Not loaded";
  }
  return value ? "Yes" : "No";
}
