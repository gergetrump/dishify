import { useEffect, useState } from "react";

import { ApiError, apiClient } from "../api/client";
import { Button } from "../components/Button";
import { Chip } from "../components/Chip";
import { DishifyLogo } from "../components/DishifyLogo";
import { formatRestrictionLabel, restrictionSections } from "../data/restrictions";

export function PreferencesPage() {
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadPreferences() {
      setError(null);
      setIsLoading(true);
      try {
        const preferences = await apiClient.preferences();
        if (isMounted) {
          setSelected(preferences.exclusion_restrictions);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof ApiError ? err.message : "Could not load preferences.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadPreferences();

    return () => {
      isMounted = false;
    };
  }, []);

  function toggleRestriction(tag: string) {
    setStatus(null);
    setSelected((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
    );
  }

  async function savePreferences() {
    setError(null);
    setStatus(null);
    setIsSaving(true);

    try {
      const preferences = await apiClient.updatePreferences({
        exclusion_restrictions: selected,
      });
      setSelected(preferences.exclusion_restrictions);
      setStatus("Preferences saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save preferences.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="page-section">
      <div className="page-brand-row">
        <DishifyLogo size="compact" />
      </div>
      <p className="eyebrow">Hard filters</p>
      <h1>Food preferences</h1>
      <p className="muted">Choose allergies, diets, and restrictions Dishify should always avoid.</p>

      {error ? <p className="alert alert-error">{error}</p> : null}
      {status ? <p className="alert alert-success">{status}</p> : null}

      <div className="toolbar">
        <p className="muted">{selected.length} selected</p>
        <div className="toolbar-actions">
          <Button type="button" variant="ghost" onClick={() => setSelected([])}>
            Clear all
          </Button>
          <Button type="button" onClick={savePreferences} disabled={isLoading || isSaving}>
            {isSaving ? "Saving..." : "Save preferences"}
          </Button>
        </div>
      </div>

      {isLoading ? <p className="muted">Loading preferences...</p> : null}

      <div className="preference-sections">
        {restrictionSections.map((section) => (
          <section className="preference-section" key={section.id}>
            <div>
              <h2>{section.title}</h2>
              <p className="muted">{section.description}</p>
            </div>
            <div className="chip-grid">
              {section.tags.map((tag) => (
                <Chip
                  key={tag}
                  selected={selected.includes(tag)}
                  onClick={() => toggleRestriction(tag)}
                  disabled={isLoading}
                >
                  {formatRestrictionLabel(tag)}
                </Chip>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
