import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  List,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { Link, useLocation, useParams } from "react-router-dom";

import type { AugmentResponse, RecipeResult } from "../api/types";
import { getAugment, prefetchAugment } from "../recommendations/augmentCache";
import { findRecipeById } from "../recommendations/session";
import { formatIngredientName } from "../utils/ingredientFormatting";

type DetailLocationState = {
  recipe?: RecipeResult;
};

export function RecipeDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const state = location.state as DetailLocationState | null;
  const recipeId = Number(id);
  const recipe = state?.recipe ?? (Number.isFinite(recipeId) ? findRecipeById(recipeId) : null);

  if (!recipe) {
    return (
      <Container size="md" py="xl">
        <Paper withBorder radius="lg" p="xl" shadow="xs">
          <Stack gap="md">
            <Text size="sm" c="dimmed" fw={700}>
              Recipe
            </Text>
            <Title order={1}>Recipe not found</Title>
            <Text c="dimmed">
              Recipe detail is available after choosing a recommendation from the latest results.
            </Text>
            <Button component={Link} to="/results" w="fit-content">
              Back to results
            </Button>
          </Stack>
        </Paper>
      </Container>
    );
  }

  const matched = recipe.inventory_matched ?? [];
  const missing = recipe.inventory_missing ?? [];
  const positive = recipe.reasoning?.positive ?? [];
  const negative = recipe.reasoning?.negative ?? [];
  const directions = recipe.directions ?? [];

  return (
    <RecipeDetailBody
      recipe={recipe}
      matched={matched}
      missing={missing}
      positive={positive}
      negative={negative}
      directions={directions}
    />
  );
}

function RecipeDetailBody({
  recipe,
  matched,
  missing,
  positive,
  negative,
  directions,
}: {
  recipe: RecipeResult;
  matched: string[];
  missing: string[];
  positive: string[];
  negative: string[];
  directions: string[];
}) {
  const [augmented, setAugmented] = useState<AugmentResponse | null>(null);
  const score = Math.round(recipe.score * 100);

  useEffect(() => {
    let cancelled = false;
    const pending = getAugment(recipe.id) ?? prefetchAugment(recipe);
    pending
      .then((result) => {
        if (!cancelled) setAugmented(result);
      })
      .catch(() => {
        // Original directions remain visible if enhancement fails.
      });
    return () => {
      cancelled = true;
    };
  }, [recipe.id, recipe]);

  return (
    <Container size="lg" py="xl">
      <Stack gap="xl">
        <Group justify="space-between" align="flex-start">
          <Stack gap="sm">
            <Text size="sm" c="dimmed" fw={700}>
              Recipe
            </Text>

            <Title order={1}>{recipe.title ?? "Untitled recipe"}</Title>

            <Group gap="xs">
              {recipe.time_minutes ? (
                <Badge color="orange" variant="light">
                  {recipe.time_minutes} min
                </Badge>
              ) : null}
              <Badge color="green" variant="light">
                Score {score}
              </Badge>
              <Badge variant="light">Rank {recipe.rank}</Badge>
            </Group>
          </Stack>

          <Button component={Link} to="/results" variant="light">
            Back to results
          </Button>
        </Group>

        {recipe.summary ? (
          <Paper withBorder radius="lg" p="lg">
            <Text c="dimmed">{recipe.summary}</Text>
          </Paper>
        ) : null}

        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
          <Card withBorder radius="lg" p="lg" shadow="xs">
            <Stack gap="md">
              <Title order={2}>Ingredient match</Title>
              <IngredientList title="You have" items={matched} empty="No matched ingredients returned." />
              <IngredientList title="You may need" items={missing} empty="No missing ingredients returned." />
            </Stack>
          </Card>

          <Card withBorder radius="lg" p="lg" shadow="xs">
            <Stack gap="md">
              <Title order={2}>Reasoning</Title>
              <ReasoningList title="Why it fits" items={positive} empty="No positive reasoning returned." />
              <ReasoningList title="Watch for" items={negative} empty="No concerns returned." />
            </Stack>
          </Card>
        </SimpleGrid>

        <Card withBorder radius="lg" p="lg" shadow="xs">
          <Stack gap="md">
            <Title order={2}>Directions</Title>
            {augmented ? (
              <Stack gap="md">
                {augmented.estimated_time_minutes ? (
                  <Text c="dimmed">Estimated total: {augmented.estimated_time_minutes} min</Text>
                ) : null}
                <List type="ordered" spacing="sm">
                  {augmented.steps.map((step, index) => (
                    <List.Item key={`${index}-${step.text}`}>
                      <Text component="span">{step.text}</Text>
                      {step.duration_minutes ? (
                        <Text component="span" c="dimmed">
                          {" "}
                          - ~{step.duration_minutes} min
                        </Text>
                      ) : null}
                      {step.tip ? (
                        <Text size="sm" c="dimmed" mt={4}>
                          Tip: {step.tip}
                        </Text>
                      ) : null}
                    </List.Item>
                  ))}
                </List>
                {augmented.tips.length ? <ReasoningList title="Tips" items={augmented.tips} empty="" /> : null}
              </Stack>
            ) : directions.length ? (
              <List type="ordered" spacing="sm">
                {directions.map((step, index) => (
                  <List.Item key={`${index}-${step}`}>{step}</List.Item>
                ))}
              </List>
            ) : (
              <Text c="dimmed">No directions were returned for this recipe.</Text>
            )}
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}

function IngredientList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <Stack gap="xs">
      <Text fw={700}>{title}</Text>
      {items.length ? (
        <Group gap="xs">
          {items.map((item) => (
            <Badge color={title === "You have" ? "green" : "yellow"} variant="light" key={item}>
              {formatIngredientName(item)}
            </Badge>
          ))}
        </Group>
      ) : (
        <Text c="dimmed" size="sm">
          {empty}
        </Text>
      )}
    </Stack>
  );
}

function ReasoningList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <Stack gap="xs">
      <Text fw={700}>{title}</Text>
      {items.length ? (
        <List size="sm" spacing={4}>
          {items.map((item) => (
            <List.Item key={item}>{item}</List.Item>
          ))}
        </List>
      ) : empty ? (
        <Text c="dimmed" size="sm">
          {empty}
        </Text>
      ) : null}
    </Stack>
  );
}
