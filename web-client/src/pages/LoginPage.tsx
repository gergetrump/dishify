import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/Button";
import { Input } from "../components/Input";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo = getRedirectPath(location.state);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ username, password });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not log in. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="narrow-page">
      <p className="eyebrow">Welcome back</p>
      <h1>Log in to Dishify</h1>
      <form className="stack" onSubmit={handleSubmit}>
        {error ? <p className="alert alert-error">{error}</p> : null}
        <Input
          label="Username"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
        />
        <Input
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Logging in..." : "Log in"}
        </Button>
      </form>
      <p className="muted">
        New here? <Link to="/register">Create an account</Link>
      </p>
    </section>
  );
}

function getRedirectPath(state: unknown) {
  if (
    state &&
    typeof state === "object" &&
    "from" in state &&
    state.from &&
    typeof state.from === "object" &&
    "pathname" in state.from &&
    typeof state.from.pathname === "string"
  ) {
    return state.from.pathname;
  }

  return "/app";
}
