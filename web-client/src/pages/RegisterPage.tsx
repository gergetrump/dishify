import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { formatRestrictionLabel, restrictionSections } from "../data/restrictions";
import { 
  Center, 
  Paper, 
  Box, 
  Stack, 
  Text, 
  Title, 
  TextInput, 
  PasswordInput, 
  Group, 
  Button, 
  Alert, 
  Anchor, 
  Chip, 
  Divider
} from "@mantine/core";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [selectedRestrictions, setSelectedRestrictions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await register({
        username,
        email,
        password,
        exclusion_restrictions: selectedRestrictions,
      });
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create your account.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function toggleRestriction(tag: string) {
    setSelectedRestrictions((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
    );
  }

  return (
    <Center mt={60} mb={60}>
      <Paper w={480}>
        <Box component="form" onSubmit={handleSubmit}>
          <Stack gap="xl">
            
            <Stack gap="xs" ta="center">
              <Title order={2}>Create your account</Title>
            </Stack>

            {error && (
              <Alert variant="light" color="red" title="Registration Failed">
                {error}
              </Alert>
            )}

            <Stack gap="md">
              <TextInput
                label="Username"
                placeholder="Pick a unique username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.currentTarget.value)}
                minLength={3}
                required
              />
              <TextInput
                label="Email"
                placeholder="your@email.com"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.currentTarget.value)}
                required
              />
              <PasswordInput
                label="Password"
                placeholder="At least 8 characters"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
                minLength={8}
                required
              />
            </Stack>

            <Divider />

            <Box>
              <Title order={4} mb={2}>Initial preferences</Title>
              <Text size="xs" c="dimmed" mb="sm">Optional. You can change these later.</Text>
              
              <Group gap="xs">
                {restrictionSections.slice(0, 2).flatMap((section) =>
                  section.tags.slice(0, 8).map((tag) => (
                    <Chip
                      key={tag}
                      checked={selectedRestrictions.includes(tag)}
                      onChange={() => toggleRestriction(tag)}
                    >
                      {formatRestrictionLabel(tag)}
                    </Chip>
                  )),
                )}
              </Group>
            </Box>

            <Stack gap="sm">
              <Button 
                type="submit" 
                loading={isSubmitting} 
                fullWidth
              >
                Sign up
              </Button>

              <Group justify="center" gap={4}>
                <Text size="sm" c="dimmed">Already have an account?</Text>
                <Anchor component={Link} to="/login" size="sm" fw={500}>
                  Log in
                </Anchor>
              </Group>
            </Stack>

          </Stack>
        </Box>
      </Paper>
    </Center>
  );
}