import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/Button";
import { Chip } from "../components/Chip";
import { Input } from "../components/Input";
import { formatRestrictionLabel, restrictionSections } from "../data/restrictions";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [selectedRestrictions, setSelectedRestrictions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await register({
        username,
        email,
        password,
        exclusion_restrictions: selectedRestrictions,
      });
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create your account.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function toggleRestriction(tag: string) {
    setSelectedRestrictions((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
    );
  }

  return (
    <section className="narrow-page">
      <p className="eyebrow">Start cooking smarter</p>
      <h1>Create your account</h1>
      <form className="stack" onSubmit={handleSubmit}>
        {error ? <p className="alert alert-error">{error}</p> : null}
        <Input
          label="Username"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          minLength={3}
          required
        />
        <Input
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <Input
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={8}
          required
        />

        <div className="form-section">
          <h2>Initial preferences</h2>
          <p className="muted">Optional. You can change these later.</p>
          <div className="chip-grid compact">
            {restrictionSections.slice(0, 2).flatMap((section) =>
              section.tags.slice(0, 8).map((tag) => (
                <Chip
                  key={tag}
                  selected={selectedRestrictions.includes(tag)}
                  onClick={() => toggleRestriction(tag)}
                >
                  {formatRestrictionLabel(tag)}
                </Chip>
              )),
            )}
          </div>
        </div>

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating account..." : "Sign up"}
        </Button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  );
}
