import { Link, Route, Routes } from "react-router-dom";

import { RequireAuth } from "./auth/RequireAuth";
import { useAuth } from "./auth/AuthProvider";
import { AppPage } from "./pages/AppPage";
import { LoginPage } from "./pages/LoginPage";
import { PreferencesPage } from "./pages/PreferencesPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RecipeDetailPage } from "./pages/RecipeDetailPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResultsPage } from "./pages/ResultsPage";
import { WelcomePage } from "./pages/WelcomePage";
import { Avatar, Box, Group, Anchor, Button, Text, Menu, Image } from "@mantine/core";
import logo from "./assets/dishify-logo.svg";

export function App() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="app-shell">
      <Box 
        component="header" 
        py="md" 
        px="xl" 
        style={(theme) => ({
          borderBottom: `1px solid ${theme.colors.gray[2]}`,
          backgroundColor: theme.white, 
          position: "sticky",
          top: 0,
          zIndex: 100, 
        })}
        
      >
        <Group justify="space-between" align="center">     
          <Anchor 
            component={Link} 
            to="/" 
            underline="never" 
            aria-label="Dishify home"
            c="dark"
          >
            <Group gap="xs" align="center">
              <Image src={logo} alt="Dishify Logo" w={28} h={28} fit="contain" />
              <Text fw={700} size="lg">
                Dishify
              </Text>
            </Group>
          </Anchor>

          <Group component="nav" aria-label="Main navigation" gap="md">
                    
            {isAuthenticated ? (
              <>
                <Anchor component={Link} to="/app" size="sm" fw={500} c="dimmed">
                  Cook
                </Anchor>
                <Anchor component={Link} to="/preferences" size="sm" fw={500} c="dimmed">
                  Preferences
                </Anchor>
                
                <Menu trigger="hover" openDelay={100} shadow="md" width={160} position="bottom-end">
                  <Menu.Target>
                    <Avatar variant="light" radius="md" color="orange" />
                  </Menu.Target>

                  <Menu.Dropdown>
                    <Menu.Label>Account Options</Menu.Label>
                    
                    <Menu.Item component={Link} to="/profile">
                      View Profile
                    </Menu.Item>

                    <Menu.Divider />

                    <Menu.Item color="red" onClick={logout}>
                      Log out
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              </>
            ) : (
              <>
                <Button component={Link} to="/login" size="sm" variant="light">
                  Log in
                </Button>
                <Button component={Link} to="/register" size="sm" >
                  Sign up
                </Button>
              </>
            )}
          </Group>

        </Group>
     </Box>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<WelcomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/preferences"
            element={
              <RequireAuth>
                <PreferencesPage />
              </RequireAuth>
            }
          />
          <Route
            path="/app"
            element={
              <RequireAuth>
                <AppPage />
              </RequireAuth>
            }
          />
          <Route
            path="/results"
            element={
              <RequireAuth>
                <ResultsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/recipes/:id"
            element={
              <RequireAuth>
                <RecipeDetailPage />
              </RequireAuth>
            }
          />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <ProfilePage />
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
