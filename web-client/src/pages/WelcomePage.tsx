import { Box, Button, Container, Group, Stack, Title, Text, Image } from "@mantine/core";
import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import parts from "../assets/app-parts-draft-v2.png";
import suggestion from "../assets/suggestion.png";

export function WelcomePage() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  return (
    <DotBackground>
      <Box component="section">
        <Container size="xl" ta="center" >
          <Stack gap="lg" maw={600} mx="auto">
            <Title order={1} fz={{ base: 30, xs: 36, sm: 50 }} >
              Your next meal is
              <Text component="span" c="orange" display="block" inherit>
                already in your kitchen
              </Text>
            </Title>

            <Text maw={480} lh={1.3} fw={500} mx="auto">
              Add what you have, set the foods you avoid, and get recipe ideas that fit your pantry.
            </Text>
            <Stack gap="sm" mt="md">
              <Group gap="md" justify="center">
                <Button component={Link} to="/register">
                  Sign up
                </Button>
                <Button component={Link} to="/login" variant="light">
                  Log in
                </Button>
              </Group>
              <Text c={"dimmed"}>
                <Text component="span" display={{ base: "block", sm: "inline" }} inherit>
                  <Text component="span" fw={700} inherit>4.0/5 </Text>
                  recipe relevance
                </Text>
                <Text component="span" fw={900} inherit visibleFrom="sm"> · </Text>
                <Text component="span" display={{ base: "block", sm: "inline" }} inherit>
                  <Text component="span" fw={700} inherit>3.7/5 </Text>
                  likelihood to reuse
                </Text>
              </Text>
            </Stack>
          </Stack>


          <Image
            src={parts}
            alt="App preview"
            maw={700}
            mx="auto"
            mt="xl"
            visibleFrom="sm"
          />
          <Image
            src={suggestion}
            alt="App preview"
            w="150%"
            maw={700}
            mt="xl"
            hiddenFrom="sm"
            style={{ position: "relative", left: "50%", transform: "translateX(-50%)" }}
          />
        </Container>
      </Box>
    </DotBackground>
  );
}


function DotBackground({ children }: { children: React.ReactNode }) {
  return (
    <Box
      style={{
        minHeight: '100vh',
        width: '100vw',
        marginLeft: 'calc(50% - 50vw)',
        backgroundImage: 'radial-gradient(circle, var(--mantine-color-orange-3) 1px, transparent 1px)',
        backgroundSize: '32px 32px',
      }}
    >
      {children}
    </Box>
  );
}
