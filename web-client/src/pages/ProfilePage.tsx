import { useEffect, useState } from "react";
import { useDocumentTitle } from "@mantine/hooks";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Alert, Button, Center, Group, Loader, Paper, Stack, Table, Text, Title } from "@mantine/core";

export function ProfilePage() {
  useDocumentTitle("Profile · Dishify");

  const { loadUser, logout, user } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(!user);

  useEffect(() => {
    let isMounted = true;

    async function refreshProfile() {
      setError(null);
      setIsLoading(true);

      try {
        await loadUser();
      } catch (err) {
        if (isMounted) {
          setError(err instanceof ApiError ? err.message : "Could not load your profile.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void refreshProfile();

    return () => {
      isMounted = false;
    };
  }, [loadUser]);

  return (
    <Center mt={60} mb={60}>
      <Paper w={480}>
        <Stack gap="xl">
          <Stack gap="xs" ta="center">
            <Title order={2}>Profile</Title>
          </Stack>

          {error && (
            <Alert variant="light" color="red" title="Error">
              {error}
            </Alert>
          )}

          {isLoading ? (
            <Center mih={150}>
              <Stack gap="xs" align="center">
                <Loader size="md" />
                <Text size="sm" c="dimmed">
                  Loading your profile...
                </Text>
              </Stack>
            </Center>
          ) : (
            <>
              <Table variant="vertical" layout="fixed" withRowBorders>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Th w="40%">
                      <Text size="sm" fw={500} c="dimmed">
                        Username
                      </Text>
                    </Table.Th>
                    <Table.Td>
                      <Text size="sm" fw={600}>
                        {user?.username ?? "Not loaded"}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Th>
                      <Text size="sm" fw={500} c="dimmed">
                        Email
                      </Text>
                    </Table.Th>
                    <Table.Td>
                      <Text size="sm" fw={600}>
                        {user?.email ?? "Not loaded"}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Th>
                      <Text size="sm" fw={500} c="dimmed">
                        Email verified
                      </Text>
                    </Table.Th>
                    <Table.Td>
                      <Text size="sm" fw={600}>
                        {formatBoolean(user?.email_verified)}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>

              <Group grow gap="sm">
                <Button component={Link} to="/preferences" type="button" variant="light">
                  Food preferences
                </Button>
                <Button type="button" variant="light" color="red" onClick={logout}>
                  Log out
                </Button>
              </Group>
            </>
          )}
        </Stack>
      </Paper>
    </Center>
  );
}

function formatBoolean(value: boolean | null | undefined) {
  if (value == null) {
    return "Not loaded";
  }
  return value ? "Yes" : "No";
}
