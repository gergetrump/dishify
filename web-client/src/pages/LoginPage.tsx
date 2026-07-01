import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
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
  Anchor 
} from "@mantine/core";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo = getRedirectPath(location.state);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ username, password });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not log in. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Center mt={60} mb={60}>
      <Paper w={480}>
        <Box component="form" onSubmit={handleSubmit}>
          <Stack gap="xl">
            <Stack gap="xs" ta="center">
              <Title order={2}>Log in</Title>
            </Stack>

            {error && (
              <Alert variant="light" color="red" title="Login Failed">
                {error}
              </Alert>
            )}
            
            <Stack gap="md">
              <TextInput 
                label="Username" 
                placeholder="Your username" 
                autoComplete="username"
                value={username} 
                onChange={(event) => setUsername(event.currentTarget.value)} 
                required
              /> 
              <PasswordInput 
                label="Password" 
                placeholder="Your password" 
                autoComplete="current-password"
                value={password} 
                onChange={(event) => setPassword(event.currentTarget.value)} 
                required
              />
            </Stack>

            <Stack gap="sm">
              <Button 
                type="submit" 
                loading={isSubmitting} 
                fullWidth
              >
                Log in
              </Button>
              
              <Group justify="center" gap={4}>
                <Text size="sm" c="dimmed">New here?</Text>
                <Anchor component={Link} to="/register" size="sm" fw={500}>
                  Create an account
                </Anchor>
              </Group>
            </Stack>

          </Stack>
        </Box>
      </Paper>
    </Center>
  );
}

function getRedirectPath(state: unknown) {
  if (
    state &&
    typeof state === "object" &&
    "from" in state &&
    state.from &&
    typeof state.from === "object" &&
    "pathname" in state.from &&
    typeof state.from.pathname === "string"
  ) {
    return state.from.pathname;
  }

  return "/app";
}