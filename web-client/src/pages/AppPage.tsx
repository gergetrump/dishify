import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, apiClient } from "../api/client";
import type { DetectedIngredient } from "../api/types";
import { Button } from "../components/Button";
import { IngredientCapture } from "../components/IngredientCapture";
import { Input } from "../components/Input";
import { blobToBase64 } from "../media/encode";
import { prefetchAugmentAll } from "../recommendations/augmentCache";
import {
  createPantryItem,
  loadPantryItems,
  pantryItemsToIngredients,
  savePantryItems,
  type PantryItem,
} from "../pantry/storage";
import { saveRecommendationSession } from "../recommendations/session";

export function AppPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<PantryItem[]>(() => loadPantryItems());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [showCapture, setShowCapture] = useState(false);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [mediaNotice, setMediaNotice] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const pantryIngredients = useMemo(() => pantryItemsToIngredients(items), [items]);

  useEffect(() => {
    savePantryItems(items);
  }, [items]);

  function resetIngredientForm() {
    setEditingId(null);
    setName("");
    setQuantity("");
    setUnit("");
  }

  function handleIngredientSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      return;
    }

    const parsedQuantity = quantity.trim() ? Number(quantity) : null;
    const nextItem = createPantryItem({
      name: trimmedName,
      quantity: Number.isFinite(parsedQuantity) ? parsedQuantity : null,
      unit,
    });

    setItems((current) => {
      if (!editingId) {
        return [...current, nextItem];
      }
      return current.map((item) => (item.id === editingId ? { ...nextItem, id: editingId } : item));
    });
    resetIngredientForm();
  }

  function editItem(item: PantryItem) {
    setEditingId(item.id);
    setName(item.name);
    setQuantity(item.quantity == null ? "" : String(item.quantity));
    setUnit(item.unit ?? "");
  }

  function deleteItem(id: string) {
    setItems((current) => current.filter((item) => item.id !== id));
    if (editingId === id) {
      resetIngredientForm();
    }
  }

  async function handleRecommendSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const resolvedQuery = query.trim() || defaultQueryFromPantry(items);

    setIsSubmitting(true);
    try {
      const response = await apiClient.recommend({
        query: resolvedQuery,
        top_k: topK,
        available_ingredients: pantryIngredients,
      });
      const request = {
        query: resolvedQuery,
        top_k: topK,
        available_ingredients: pantryIngredients,
      };

      // Start enhancing every result's directions in the background now, so
      // opening any recipe shows the enhanced steps instantly.
      prefetchAugmentAll(response.results);

      saveRecommendationSession({ request, response });

      navigate("/results", {
        state: {
          response,
          request,
        },
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not get recipe suggestions.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function startRecording() {
    setMediaError(null);
    setMediaNotice(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setMediaError("Voice input is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        void transcribeRecording(recorder.mimeType);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setMediaError("Microphone access was denied.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setIsRecording(false);
  }

  async function transcribeRecording(mimeType: string) {
    const blob = new Blob(audioChunksRef.current, { type: mimeType || "audio/webm" });
    audioChunksRef.current = [];
    if (blob.size === 0) {
      return;
    }

    setIsTranscribing(true);
    setMediaError(null);
    setMediaNotice(null);
    try {
      const { base64, mimeType: blobMime } = await blobToBase64(blob, "audio/webm");
      const { ingredients, query: spokenQuery, transcript } = await apiClient.voice({
        audio_base64: base64,
        mime_type: blobMime,
      });

      const detected = ingredients
        .map((ingredient) =>
          createPantryItem({
            name: ingredient.name || ingredient.raw_text,
            quantity: ingredient.quantity ?? null,
            unit: ingredient.unit ?? null,
          }),
        )
        .filter((item) => item.name);
      const added = dedupeByName(items, detected);
      if (added.length) {
        setItems((current) => [...current, ...dedupeByName(current, detected)]);
      }

      const vibe = spokenQuery?.trim();
      if (vibe) {
        setQuery((current) => (current.trim() ? `${current.trim()} ${vibe}` : vibe));
      }

      if (added.length || vibe) {
        const parts: string[] = [];
        if (added.length) parts.push(`added ${added.length} ingredient(s)`);
        if (vibe) parts.push("set your vibe");
        setMediaNotice(`Heard you — ${parts.join(" and ")}.`);
      } else if (!transcript.trim()) {
        setMediaError("Could not hear anything in that recording.");
      } else {
        setMediaError("Didn't catch any ingredients — try naming what you have.");
      }
    } catch (err) {
      setMediaError(err instanceof ApiError ? err.message : "Could not process audio.");
    } finally {
      setIsTranscribing(false);
    }
  }

  function addDetectedIngredients(ingredients: DetectedIngredient[]) {
    setMediaError(null);
    const detected = ingredients
      .map((ingredient) =>
        createPantryItem({
          name: ingredient.name || ingredient.raw_text,
          quantity: ingredient.quantity ?? null,
          unit: ingredient.unit ?? null,
        }),
      )
      .filter((item) => item.name);

    if (!detected.length) {
      return;
    }
    const added = dedupeByName(items, detected);
    setItems((current) => [...current, ...dedupeByName(current, detected)]);
    setMediaNotice(`Added ${added.length} ingredient(s) from your photo.`);
  }

  return (
    <section className="cook-layout">
      {showCapture ? (
        <IngredientCapture
          onConfirm={addDetectedIngredients}
          onClose={() => setShowCapture(false)}
        />
      ) : null}
      <div className="hero-panel">
        <p className="eyebrow">What is available today?</p>
        <h1>Your next meal is already in your kitchen.</h1>
        <p className="muted">
          Add pantry items, describe what sounds good, and Dishify will recommend recipes that fit.
        </p>
        <div className="example-list" aria-label="Example vibe prompts">
          <span>quick high-protein dinner</span>
          <span>cozy vegetarian pasta</span>
          <span>spicy lunch with eggs</span>
        </div>
      </div>

      <div className="compose-panel">
        <form className="stack" onSubmit={handleIngredientSubmit}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Pantry</p>
              <h2>Add ingredients</h2>
            </div>
            {items.length ? (
              <button className="link-button danger-link" type="button" onClick={() => setItems([])}>
                Clear all
              </button>
            ) : null}
          </div>

          <div className="button-row">
            <Button type="button" variant="secondary" onClick={() => setShowCapture(true)}>
              📷 Scan ingredients
            </Button>
            <Button
              type="button"
              variant={isRecording ? "ghost" : "secondary"}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isTranscribing}
            >
              {isRecording ? "■ Stop & add" : isTranscribing ? "Listening..." : "🎤 Say what you have"}
            </Button>
          </div>
          {mediaError ? <p className="alert alert-error">{mediaError}</p> : null}
          {mediaNotice ? <p className="alert alert-success">{mediaNotice}</p> : null}

          <Input
            label="Ingredient"
            name="ingredient"
            placeholder="Eggs"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={512}
            required
          />
          <div className="form-grid">
            <Input
              label="Quantity"
              name="quantity"
              type="number"
              min="0"
              step="any"
              placeholder="2"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
            <Input
              label="Unit"
              name="unit"
              placeholder="pieces"
              value={unit}
              onChange={(event) => setUnit(event.target.value)}
            />
          </div>
          <div className="button-row">
            <Button type="submit" variant="secondary">
              {editingId ? "Save ingredient" : "Add ingredient"}
            </Button>
            {editingId ? (
              <Button type="button" variant="ghost" onClick={resetIngredientForm}>
                Cancel
              </Button>
            ) : null}
          </div>
        </form>

        <div className="pantry-list" aria-live="polite">
          {items.length ? (
            items.map((item) => (
              <article className="pantry-item" key={item.id}>
                <div>
                  <strong>{item.name}</strong>
                  <span>{item.raw_text}</span>
                </div>
                <div className="pantry-actions">
                  <button type="button" onClick={() => editItem(item)}>
                    Edit
                  </button>
                  <button type="button" onClick={() => deleteItem(item.id)}>
                    Delete
                  </button>
                </div>
              </article>
            ))
          ) : (
            <p className="empty-state">No pantry ingredients yet.</p>
          )}
        </div>

        <form className="stack vibe-form" onSubmit={handleRecommendSubmit}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Vibe check</p>
              <h2>What sounds good?</h2>
            </div>
            <label className="compact-field" htmlFor="top-k">
              <span>Results</span>
              <select id="top-k" value={topK} onChange={(event) => setTopK(Number(event.target.value))}>
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </label>
          </div>

          {error ? <p className="alert alert-error">{error}</p> : null}

          <label className="field" htmlFor="query">
            <span>Eating vibe <small>optional</small></span>
            <textarea
              id="query"
              className="textarea"
              placeholder="Optional, e.g. quick spicy dinner with eggs"
              value={query}
              maxLength={512}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Finding recipes..." : "Show recipes"}
          </Button>
        </form>
      </div>
    </section>
  );
}

function dedupeByName(existing: PantryItem[], candidates: PantryItem[]) {
  const seen = new Set(existing.map((item) => item.name.trim().toLowerCase()));
  const added: PantryItem[] = [];
  for (const candidate of candidates) {
    const key = candidate.name.trim().toLowerCase();
    if (key && !seen.has(key)) {
      seen.add(key);
      added.push(candidate);
    }
  }
  return added;
}

function defaultQueryFromPantry(items: PantryItem[]) {
  const names = items.map((item) => item.name).filter(Boolean);
  if (names.length) {
    return `recipe using ${names.slice(0, 8).join(", ")}`;
  }
  return "recipe recommendation";
}
