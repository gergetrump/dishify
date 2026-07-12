import { Badge, Button, Card, Group, List, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

import type { RecipeResult } from "../api/types";

type RecipeCardProps = {
  recipe: RecipeResult;
};

export function RecipeCard({ recipe }: RecipeCardProps) {
  const matched = recipe.inventory_matched ?? [];
  const missing = recipe.inventory_missing ?? [];
  const positive = recipe.reasoning?.positive ?? [];
  const negative = recipe.reasoning?.negative ?? [];
  const score = Math.round(recipe.score * 100);

  return (
    <Card withBorder radius="lg" p="lg" shadow="xs">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <Stack gap={4}>
            <Text size="sm" c="dimmed" fw={700}>
              Rank {recipe.rank}
            </Text>
            <Title order={3}>{recipe.title ?? "Untitled recipe"}</Title>

            <Group gap="xs">
              {recipe.time_minutes ? (
                <Badge variant="light" color="orange">
                  {recipe.time_minutes} min
                </Badge>
              ) : null}
              <Badge variant="light" color="green">
                Score {score}
              </Badge>
            </Group>
          </Stack>

          <Badge size="xl" radius="xl" color="orange">
            {score}
          </Badge>
        </Group>

        {recipe.summary ? (
          <Text c="dimmed" size="sm">
            {recipe.summary}
          </Text>
        ) : null}

        {(positive.length || negative.length) ? (
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            {positive.length ? (
              <Stack gap="xs">
                <Text fw={700}>Why it fits</Text>
                <List size="sm" spacing={4}>
                  {positive.slice(0, 2).map((item) => (
                    <List.Item key={item}>{item}</List.Item>
                  ))}
                </List>
              </Stack>
            ) : null}

            {negative.length ? (
              <Stack gap="xs">
                <Text fw={700}>Watch for</Text>
                <List size="sm" spacing={4}>
                  {negative.slice(0, 2).map((item) => (
                    <List.Item key={item}>{item}</List.Item>
                  ))}
                </List>
              </Stack>
            ) : null}
          </SimpleGrid>
        ) : null}

        <Group gap="xs">
          {matched.slice(0, 4).map((item) => (
            <Badge color="green" variant="light" key={`matched-${item}`}>
              Have {item}
            </Badge>
          ))}
          {missing.slice(0, 4).map((item) => (
            <Badge color="yellow" variant="light" key={`missing-${item}`}>
              Need {item}
            </Badge>
          ))}
        </Group>

        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">
            {matched.length} matched · {missing.length} missing
          </Text>

          <Button component={Link} to={`/recipes/${recipe.id}`} state={{ recipe }} variant="light">
            View recipe
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}