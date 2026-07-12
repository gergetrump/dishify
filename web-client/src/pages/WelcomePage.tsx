import { Anchor, Box, Button, Card, Container, Group, Stack, Text, Title } from "@mantine/core";
import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

export function WelcomePage() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  return (
    <Container size="lg" py={{ base: "xl", md: 96 }}>
      <Group justify="space-between" align="center" gap="xl">
        <Stack gap="lg" maw={560}>
          <Text size="sm" c="dimmed" fw={700}>
            Dishify
          </Text>

          <Title order={1} fz={{ base: 42, md: 64 }} lh={1}>
            Your next meal is already in your kitchen.
          </Title>

          <Text size="lg" c="dimmed">
            Add what you have, set the foods you avoid, and get recipe ideas that fit your pantry.
          </Text>

          <Group gap="sm">
            <Button component={Link} to="/register" size="md">
              Sign up
            </Button>

            <Button component={Link} to="/login" size="md" variant="light">
              Log in
            </Button>
          </Group>
        </Stack>

        <Card
          withBorder
          radius="xl"
          p="xl"
          shadow="sm"
          w={{ base: "100%", md: 360 }}
          mih={300}
          aria-hidden="true"
        >
          <Stack h="100%" justify="center" align="center" gap="lg">
            <Box fz={80}>🥗</Box>
            <Title order={2} ta="center">
              Pantry-first cooking
            </Title>
            <Text ta="center" c="dimmed">
              Turn ingredients into practical recipe ideas in seconds.
            </Text>
          </Stack>
        </Card>
      </Group>

      <Text mt="xl" size="sm" c="dimmed">
        Already have an account?{" "}
        <Anchor component={Link} to="/login">
          Log in here
        </Anchor>
      </Text>
    </Container>
  );
}
