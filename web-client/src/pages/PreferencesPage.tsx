import { useEffect, useState } from "react";
import { useDocumentTitle } from "@mantine/hooks";

import { ApiError, apiClient } from "../api/client";
import { formatRestrictionLabel, restrictionSections } from "../data/restrictions";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Divider,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";

export function PreferencesPage() {
  useDocumentTitle("Preferences · Dishify");

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
    <Container size="lg" my="xl" mt={60} mb={60}>
      <Paper>
        <Stack gap="xl">
          <Box>
            <Text size="sm" c="dimmed" fw={500}>
              Hard filters
            </Text>
            <Title order={2} mb="xs">
              Food preferences
            </Title>
            <Text c="dimmed" size="sm">
              Choose allergies, diets, and restrictions Dishify should always avoid.
            </Text>
          </Box>

          {error && (
            <Alert variant="light" color="red" title="Error">
              {error}
            </Alert>
          )}

          {status && (
            <Alert variant="light" color="green" title="Success">
              {status}
            </Alert>
          )}

          <Group justify="space-between" align="center" py="sm">
            <Text size="sm" c="dimmed" fw={500}>
              {selected.length} selected
            </Text>
            <Group gap="sm">
              <Button type="button" variant="subtle" color="red" onClick={() => setSelected([])}>
                Clear all
              </Button>
              <Button type="button" onClick={savePreferences} loading={isSaving} disabled={isLoading}>
                Save preferences
              </Button>
            </Group>
          </Group>

          <Divider />

          {isLoading ? (
            <Group justify="center" py="xl">
              <Loader size="md" />
              <Text size="sm" c="dimmed">
                Loading preferences...
              </Text>
            </Group>
          ) : (
            <Stack gap="xl">
              {restrictionSections.map((section) => (
                <Box key={section.id}>
                  <Box mb="md">
                    <Title order={3}>{section.title}</Title>
                    <Text c="dimmed" size="xs">
                      {section.description}
                    </Text>
                  </Box>

                  <Group gap="xs">
                    {section.tags.map((tag) => (
                      <Chip
                        key={tag}
                        checked={selected.includes(tag)}
                        onChange={() => toggleRestriction(tag)}
                        disabled={isLoading}
                      >
                        {formatRestrictionLabel(tag)}
                      </Chip>
                    ))}
                  </Group>
                </Box>
              ))}
            </Stack>
          )}
        </Stack>
      </Paper>
    </Container>
  );
}
