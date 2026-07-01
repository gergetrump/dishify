import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, apiClient } from "../api/client";
import {
  createPantryItem,
  loadPantryItems,
  pantryItemsToIngredients,
  savePantryItems,
  type PantryItem,
} from "../pantry/storage";
import { saveRecommendationSession } from "../recommendations/session";

import {
  Box,
  Container,
  Stack,
  Text,
  Title,
  Button,
  TextInput,
  Select,
  Textarea,
  Alert,
  Card,
  Group,
  SimpleGrid,
  ScrollArea,
  Divider,
  Paper,
  Flex,
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

  return (
  <Container size="md" my="xl" mt={60} mb={60}>
    <Paper bg="var(--mantine-color-body)">
      <Flex 
        direction={{ base: "column", md: "row" }} 
        gap="xl" 
        align={{ base: "center", md: "stretch" }}
      >

        <Box style={{ flex: 1 }} w="100%" maw={{ base: 480, md: "100%" }}>
          <Stack gap="xl">
            <Box component="form" onSubmit={handleIngredientSubmit}>
              <Stack gap="md">
                <Group justify="space-between" align="flex-end">
                  <Box>
                    <Text size="sm" c="dimmed" fw={500}>1. Pantry</Text>
                    <Title order={2}>Add ingredients</Title>
                  </Box>
                  {items.length > 0 && (
                    <Button variant="subtle" color="red" size="xs" onClick={() => setItems([])}>
                      Clear all
                    </Button>
                  )}
                </Group>

                <TextInput
                  label="Ingredient"
                  placeholder="Eggs"
                  value={name}
                  onChange={(event) => setName(event.currentTarget.value)}
                  required
                />

                <SimpleGrid cols={2} spacing="md">
                  <TextInput
                    label="Quantity"
                    type="number"
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
              <Title order={4} mb="sm">Current Stock</Title>

              <ScrollArea h={items.length > 0 ? 300 : "auto"} type="auto">
                <Stack gap="xs" pr="sm">
                  {items.length > 0 ? (
                    items.map((item) => {
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
                              <Text fw={600} size="sm">{item.name}</Text>
                              {item.raw_text && (
                                <Text size="xs" c="dimmed">{item.raw_text}</Text>
                              )}
                            </Box>
                            <Group gap={4}>
                              <Button 
                                size="xs" 
                                variant={"subtle"} 
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
                      No pantry ingredients yet.
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
                <Text size="sm" c="dimmed" fw={500}>2. Vibe check</Text>
                <Title order={2}>What sounds good?</Title>
              </Box>

              {error && (
                <Alert variant="light" color="red" title="Error">
                  {error}
                </Alert>
              )}

              <Stack gap={"xl"}>
                <Textarea
                  label={
                    <Text size="sm" fw={500}>
                      Eating vibe <Text component="span" size="xs" c="dimmed" fw={400}>(optional)</Text>
                    </Text>
                  }
                  placeholder="Optional, e.g. quick spicy dinner with eggs"
                  minRows={4}
                  value={query}
                  onChange={(event) => setQuery(event.currentTarget.value)}
                />

                <Divider orientation="horizontal"/>

                <Group justify="space-between" align="flex-end" w="100%">
                  <Select
                    label="Results"
                    w={80}
                    size="sm"
                    value={String(topK)}
                    onChange={(val) => setTopK(Number(val))}
                    data={["3", "5", "10"]}
                    allowDeselect={false}
                  />
                  <Button 
                    type="submit" 
                    loading={isSubmitting} 
                    style={{ flex: 1 }}
                  >
                    Show recipes
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

function defaultQueryFromPantry(items: PantryItem[]) {
  const names = items.map((item) => item.name).filter(Boolean);
  if (names.length) {
    return `recipe using ${names.slice(0, 8).join(", ")}`;
  }
  return "recipe recommendation";
}