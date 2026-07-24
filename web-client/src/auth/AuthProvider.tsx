import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiClient } from "../api/client";
import type { LoginRequest, RegisterRequest, TokenResponse, UserProfile } from "../api/types";
import { clearPantryItems } from "../pantry/storage";
import { clearAugmentCache } from "../recommendations/augmentCache";
import { clearRecommendationSession } from "../recommendations/session";
import {
  clearStoredAccessToken,
  clearStoredRefreshToken,
  getStoredAccessToken,
  getStoredRefreshToken,
  storeAccessToken,
  storeRefreshToken,
} from "./storage";

type AuthContextValue = {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  login: (body: LoginRequest) => Promise<TokenResponse>;
  register: (body: RegisterRequest) => Promise<void>;
  loadUser: () => Promise<UserProfile | null>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(() => getStoredAccessToken());
  const [user, setUser] = useState<UserProfile | null>(null);

  const loadUser = useCallback(async () => {
    if (!getStoredAccessToken()) {
      setUser(null);
      return null;
    }

    const profile = await apiClient.me();
    setUser(profile);
    return profile;
  }, []);

  const login = useCallback(
    async (body: LoginRequest) => {
      const response = await apiClient.login(body);
      storeAccessToken(response.access_token);
      if (response.refresh_token) {
        storeRefreshToken(response.refresh_token);
      }
      setToken(response.access_token);
      await loadUser();
      return response;
    },
    [loadUser],
  );

  const register = useCallback(
    async (body: RegisterRequest) => {
      await apiClient.register(body);
      await login({ username: body.username, password: body.password });
    },
    [login],
  );

  const logout = useCallback(() => {
    const rt = getStoredRefreshToken();
    if (rt) {
      apiClient.logout(rt).catch(() => {});
    }
    clearStoredAccessToken();
    clearStoredRefreshToken();
    clearPantryItems();
    clearRecommendationSession();
    clearAugmentCache();
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    if (!token || user) {
      return;
    }

    void loadUser().catch(() => {
      logout();
    });
  }, [loadUser, logout, token, user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      login,
      register,
      loadUser,
      logout,
    }),
    [loadUser, login, logout, register, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
