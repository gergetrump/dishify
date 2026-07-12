import {
  Badge,
  Box,
  Button,
  Card,
  Divider,
  Group,
  List,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
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
    <Card
      withBorder
      radius="xl"
      p="lg"
      shadow="sm"
      style={{
        overflow: "hidden",
        transition: "transform 160ms ease, box-shadow 160ms ease",
      }}
    >
      <Stack gap="md">
        <Box
          mx="-lg"
          mt="-lg"
          mb="xs"
          h={8}
          style={{
            background: "linear-gradient(90deg, #F47D54, #D94518)",
          }}
        />

        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Stack gap={6}>
            <Group gap="xs">
              <Badge color="orange" variant="light">
                Rank {recipe.rank}
              </Badge>
              {recipe.time_minutes ? (
                <Badge variant="light" color="green">
                  {recipe.time_minutes} min
                </Badge>
              ) : null}
            </Group>

            <Title order={3}>{recipe.title ?? "Untitled recipe"}</Title>
          </Stack>

          <ThemeIcon size={58} radius="xl" color="orange" variant="light">
            <Stack gap={0} align="center">
              <Text fw={900} size="sm">
                {score}
              </Text>
              <Text size="xs">score</Text>
            </Stack>
          </ThemeIcon>
        </Group>

        <Stack gap={6}>
          <Group justify="space-between">
            <Text size="sm" c="dimmed" fw={700}>
              Match strength
            </Text>
            <Text size="sm" c="dimmed">
              {score}%
            </Text>
          </Group>
          <Progress value={score} color="orange" radius="xl" />
        </Stack>

        {recipe.summary ? (
          <Text c="dimmed" size="sm">
            {recipe.summary}
          </Text>
        ) : null}

        {(positive.length || negative.length) ? (
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            {positive.length ? (
              <Card radius="lg" p="md" bg="orange.0">
                <Stack gap="xs">
                  <Text fw={700}>Why it fits</Text>
                  <List size="sm" spacing={4}>
                    {positive.slice(0, 2).map((item) => (
                      <List.Item key={item}>{item}</List.Item>
                    ))}
                  </List>
                </Stack>
              </Card>
            ) : null}

            {negative.length ? (
              <Card radius="lg" p="md" bg="red.0">
                <Stack gap="xs">
                  <Text fw={700}>Watch for</Text>
                  <List size="sm" spacing={4}>
                    {negative.slice(0, 2).map((item) => (
                      <List.Item key={item}>{item}</List.Item>
                    ))}
                  </List>
                </Stack>
              </Card>
            ) : null}
          </SimpleGrid>
        ) : null}

        <Divider />

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