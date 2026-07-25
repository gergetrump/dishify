import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, apiClient } from "../api/client";
import type { DetectedIngredient } from "../api/types";
import { IngredientCapture } from "../components/IngredientCapture";
import { blobToBase64 } from "../media/encode";
import {
  createPantryItem,
  loadPantryItems,
  pantryItemsToIngredients,
  savePantryItems,
  type PantryItem,
} from "../pantry/storage";
import { prefetchAugmentAll } from "../recommendations/augmentCache";
import { saveRecommendationSession } from "../recommendations/session";

import {
  Alert,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Flex,
  Group,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";

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
      const request = {
        query: resolvedQuery,
        top_k: topK,
        available_ingredients: pantryIngredients,
      };
      const response = await apiClient.recommend(request);

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
        setMediaNotice(`Heard you - ${parts.join(" and ")}.`);
      } else if (!transcript.trim()) {
        setMediaError("Could not hear anything in that recording.");
      } else {
        setMediaError("Didn't catch any ingredients - try naming what you have.");
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
    <Container size="md" my="xl" mt={60} mb={60}>
      {showCapture ? (
        <IngredientCapture onConfirm={addDetectedIngredients} onClose={() => setShowCapture(false)} />
      ) : null}

      <Paper bg="var(--mantine-color-body)">
        <Flex direction={{ base: "column", md: "row" }} gap="xl" align={{ base: "center", md: "stretch" }}>
          <Box style={{ flex: 1 }} w="100%" maw={{ base: 480, md: "100%" }}>
            <Stack gap="xl">
              <Box component="form" onSubmit={handleIngredientSubmit}>
                <Stack gap="md">
                    <Box>
                      <Text size="sm" c="dimmed" fw={500}>
                        1. Pantry check
                      </Text>
                      <Title order={2}>What's in your kitchen?</Title>
                    </Box>

                  <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                    <Button type="button" variant="light" onClick={() => setShowCapture(true)}>
                      Scan ingredients
                    </Button>
                    <Button
                      type="button"
                      variant={isRecording ? "outline" : "light"}
                      onClick={isRecording ? stopRecording : startRecording}
                      disabled={isTranscribing}
                    >
                      {isRecording ? "Stop and add" : isTranscribing ? "Listening..." : "Say what you have"}
                    </Button>
                  </SimpleGrid>

                  {mediaError ? (
                    <Alert variant="light" color="red" title="Media input">
                      {mediaError}
                    </Alert>
                  ) : null}
                  {mediaNotice ? (
                    <Alert variant="light" color="green" title="Media input">
                      {mediaNotice}
                    </Alert>
                  ) : null}

                  <TextInput
                    label="Ingredient"
                    placeholder="Eggs"
                    value={name}
                    onChange={(event) => setName(event.currentTarget.value)}
                    maxLength={512}
                    required
                  />

                  <SimpleGrid cols={2} spacing="md">
                    <TextInput
                      label="Quantity"
                      type="number"
                      min={0}
                      step="any"
                      placeholder="2"
                      value={quantity}
                      onChange={(event) => setQuantity(event.currentTarget.value)}
                    />
                    <TextInput
                      label="Unit"
                      placeholder="pieces"
                      value={unit}
                      onChange={(event) => setUnit(event.currentTarget.value)}
                    />
                  </SimpleGrid>

                  <Group gap="sm" justify="flex-end">
                    {editingId && (
                      <Button type="button" variant="subtle" color="gray" onClick={resetIngredientForm}>
                        Cancel
                      </Button>
                    )}
                    <Button type="submit" variant="light">
                      {editingId ? "Save ingredient" : "Add ingredient"}
                    </Button>
                  </Group>
                </Stack>
              </Box>

              <Box>
                <Group justify="space-between" align="center" mb="sm">
                  <Title order={4}>Your pantry shelf</Title>
                  {items.length > 0 && (
                    <Button variant="subtle" color="red" size="xs" onClick={() => setItems([])}>
                      Clear all
                    </Button>
                  )}
                </Group>

                <ScrollArea h={items.length > 0 ? 300 : "auto"} type="auto">
                  <Stack gap="xs" pr="sm">
                    {items.length > 0 ? (
                      [...items].reverse().map((item) => {
                        const isEditing = item.id === editingId;

                        return (
                          <Card
                            key={item.id}
                            withBorder
                            p="sm"
                            radius="sm"
                            style={(theme) => ({
                              borderColor: isEditing ? theme.colors.orange[4] : undefined,
                              transition: "all 0.15s ease",
                            })}
                            shadow={isEditing ? "sm" : "none"}
                          >
                            <Group justify="space-between" align="center">
                              <Box style={{ flex: 1 }}>
                                <Text fw={600} size="sm">
                                  {item.name}
                                </Text>
                                {item.raw_text && (
                                  <Text size="xs" c="dimmed">
                                    {item.raw_text}
                                  </Text>
                                )}
                              </Box>
                              <Group gap={4}>
                                <Button
                                  size="xs"
                                  variant="subtle"
                                  disabled={isEditing}
                                  color={isEditing ? "blue" : "gray"}
                                  onClick={() => editItem(item)}
                                >
                                  {isEditing ? "Editing" : "Edit"}
                                </Button>
                                <Button size="xs" variant="subtle" color="red" onClick={() => deleteItem(item.id)}>
                                  Delete
                                </Button>
                              </Group>
                            </Group>
                          </Card>
                        );
                      })
                    ) : (
                      <Text c="dimmed" size="sm" ta="center" py="xs">
                        Your pantry is empty for now. Add a few ingredients to get started.
                      </Text>
                    )}
                  </Stack>
                </ScrollArea>
              </Box>
            </Stack>
          </Box>

          <Divider orientation="horizontal" w="100%" hiddenFrom="md" />
          <Divider orientation="vertical" visibleFrom="md" />

          <Box style={{ flex: 1 }} w="100%" maw={{ base: 480, md: "100%" }}>
            <Box component="form" onSubmit={handleRecommendSubmit}>
              <Stack gap="md">
                <Box>
                  <Text size="sm" c="dimmed" fw={500}>
                    2. Vibe check
                  </Text>
                  <Title order={2}>What are you craving?</Title>
                </Box>

                {error && (
                  <Alert variant="light" color="red" title="Error">
                    {error}
                  </Alert>
                )}

                <Stack gap="xl">
                  <Textarea
                    label={
                      <Text size="sm" fw={500}>
                        Eating vibe{" "}
                        <Text component="span" size="xs" c="dimmed" fw={400}>
                          (optional)
                        </Text>
                      </Text>
                    }
                    placeholder="Optional, e.g. quick spicy dinner with eggs"
                    minRows={4}
                    value={query}
                    onChange={(event) => setQuery(event.currentTarget.value)}
                    maxLength={512}
                  />

                  <Divider orientation="horizontal" />

                  <Group justify="space-between" align="flex-end" w="100%">
                    <Select
                      label="Results"
                      w={80}
                      size="sm"
                      value={String(topK)}
                      onChange={(value) => {
                        if (value) setTopK(Number(value));
                      }}
                      data={["3", "5", "10"]}
                      allowDeselect={false}
                    />
                    <Button type="submit" loading={isSubmitting} style={{ flex: 1 }}>
                      Find my recipes
                    </Button>
                  </Group>
                </Stack>
              </Stack>
            </Box>
          </Box>
        </Flex>
      </Paper>
    </Container>
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
