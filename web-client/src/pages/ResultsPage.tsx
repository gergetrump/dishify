import { Alert, Button, Container, Group, Paper, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { useDocumentTitle } from "@mantine/hooks";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { ApiError, apiClient } from "../api/client";
import type { RecommendRequest, RecommendResponse } from "../api/types";
import { RecipeCard } from "../components/RecipeCard";
import { prefetchAugmentAll } from "../recommendations/augmentCache";
import {
  loadRecommendationSession,
  saveRecommendationSession,
} from "../recommendations/session";

type ResultsLocationState = {
  response?: RecommendResponse;
  request?: RecommendRequest;
};

export function ResultsPage() {
  useDocumentTitle("Recipe results · Dishify");

  const location = useLocation();
  const state = location.state as ResultsLocationState | null;
  const storedSession = useMemo(() => loadRecommendationSession(), []);
  const initialRequest = state?.request ?? storedSession?.request ?? null;
  const initialResponse = state?.response ?? storedSession?.response ?? null;
  const [request, setRequest] = useState<RecommendRequest | null>(initialRequest);
  const [response, setResponse] = useState<RecommendResponse | null>(initialResponse);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    if (response?.results?.length) {
      prefetchAugmentAll(response.results);
    }
  }, [response]);

  async function retryRecommendation() {
    if (!request) {
      return;
    }

    setError(null);
    setIsRetrying(true);
    try {
      const nextResponse = await apiClient.recommend(request);
      setResponse(nextResponse);
      setRequest(request);
      saveRecommendationSession({ request, response: nextResponse });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not retry recommendation.");
    } finally {
      setIsRetrying(false);
    }
  }

  if (!response) {
    return (
      <Container size="md" py="xl">
        <Paper withBorder radius="lg" p="xl" shadow="xs">
          <Stack gap="md">
            <Text size="sm" c="dimmed" fw={700}>
              Recipe suggestions
            </Text>
            <Title order={1}>No results yet</Title>
            <Text c="dimmed">Add pantry ingredients and describe what sounds good first.</Text>
            <Button component={Link} to="/app" w="fit-content">
              Start cooking
            </Button>
          </Stack>
        </Paper>
      </Container>
    );
  }

  return (
    <Container size="lg" py="xl">
      <Stack gap="xl">
        <Group justify="space-between" align="flex-start">
          <Stack gap={4}>
            <Text size="sm" c="dimmed" fw={700}>
              Recipe suggestions
            </Text>
            <Title order={1}>Best matches</Title>
            {request ? <Text c="dimmed">For: {request.query}</Text> : null}
          </Stack>

          <Group>
            <Button component={Link} variant="light" to="/app">Start over</Button>
            {request ? (
              <Button type="button" variant="light" onClick={retryRecommendation} loading={isRetrying}>
                Retry
              </Button>
            ) : null}
          </Group>
        </Group>

        {error ? (
          <Alert color="red" title="Error" radius="md">
            {error}
          </Alert>
        ) : null}

        {response.results.length ? (
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
            {response.results.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </SimpleGrid>
        ) : (
          <Paper withBorder radius="lg" p="xl">
            <Text c="dimmed">Dishify did not return any recipes for this search.</Text>
          </Paper>
        )}
      </Stack>
    </Container>
  );
}
