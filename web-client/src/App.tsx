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

export function App() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="brand" to="/app" aria-label="Dishify home">
          <span className="brand-mark">D</span>
          <span>Dishify</span>
        </Link>
        <nav className="nav-links" aria-label="Main navigation">
          <Link to="/app">Cook</Link>
          {isAuthenticated ? (
            <>
              <Link to="/preferences">Preferences</Link>
              <Link to="/profile">Profile</Link>
              <button className="link-button" type="button" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login">Log in</Link>
              <Link to="/register">Sign up</Link>
            </>
          )}
        </nav>
      </header>

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
