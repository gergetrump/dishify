import type {
  ApiErrorPayload,
  AugmentRequest,
  AugmentResponse,
  AuthConfigResponse,
  HealthResponse,
  LoginRequest,
  RecommendRequest,
  RecommendResponse,
  RegisterRequest,
  RegisterResponse,
  TokenResponse,
  TranscribeRequest,
  TranscribeResponse,
  UpdatePreferencesRequest,
  UserPreferences,
  UserProfile,
  VisionIngredientsRequest,
  VisionIngredientsResponse,
  VoiceResponse,
} from "./types";

const DEFAULT_API_URL = "http://localhost:8000";

export type ApiErrorCode =
  | "auth"
  | "validation"
  | "unavailable"
  | "network"
  | "unknown";

export class ApiError extends Error {
  readonly status?: number;
  readonly code: ApiErrorCode;
  readonly detail?: unknown;

  constructor(message: string, code: ApiErrorCode, status?: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

export type RefreshRequest = {
  refresh_token: string;
};

export type LogoutRequest = {
  refresh_token: string;
};

export type ApiClientOptions = {
  baseUrl?: string;
  getToken?: () => string | null;
  getRefreshToken?: () => string | null;
  onTokenRefreshed?: (accessToken: string, refreshToken: string | null) => void;
  onRefreshFailed?: () => void;
};

export class ApiClient {
  private readonly baseUrl: string;
  private readonly getToken?: () => string | null;
  private readonly getRefreshToken?: () => string | null;
  private readonly onTokenRefreshed?: (accessToken: string, refreshToken: string | null) => void;
  private readonly onRefreshFailed?: () => void;
  private refreshPromise: Promise<TokenResponse> | null = null;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredApiUrl());
    this.getToken = options.getToken;
    this.getRefreshToken = options.getRefreshToken;
    this.onTokenRefreshed = options.onTokenRefreshed;
    this.onRefreshFailed = options.onRefreshFailed;
  }

  health() {
    return this.request<HealthResponse>("/health");
  }

  authConfig() {
    return this.request<AuthConfigResponse>("/auth/config");
  }

  register(body: RegisterRequest) {
    return this.request<RegisterResponse>("/auth/register", {
      method: "POST",
      body,
      skipAuth: true,
    });
  }

  login(body: LoginRequest) {
    return this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body,
      skipAuth: true,
    });
  }

  me() {
    return this.request<UserProfile>("/me");
  }

  preferences() {
    return this.request<UserPreferences>("/me/preferences");
  }

  updatePreferences(body: UpdatePreferencesRequest) {
    return this.request<UserPreferences>("/me/preferences", {
      method: "PUT",
      body,
    });
  }

  recommend(body: RecommendRequest) {
    return this.request<RecommendResponse>("/recommend", {
      method: "POST",
      body,
    });
  }

  transcribe(body: TranscribeRequest) {
    return this.request<TranscribeResponse>("/transcribe", {
      method: "POST",
      body,
    });
  }

  voice(body: TranscribeRequest) {
    return this.request<VoiceResponse>("/voice", {
      method: "POST",
      body,
    });
  }

  detectIngredients(body: VisionIngredientsRequest) {
    return this.request<VisionIngredientsResponse>("/vision/ingredients", {
      method: "POST",
      body,
    });
  }

  augmentRecipe(body: AugmentRequest) {
    return this.request<AugmentResponse>("/recipes/augment", {
      method: "POST",
      body,
    });
  }

  refreshToken(refreshToken: string) {
    return this.rawRequest<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
  }

  logout(refreshToken: string) {
    return this.rawRequest<void>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
  }

  private async request<T>(
    path: string,
    options: {
      method?: "GET" | "POST" | "PUT";
      body?: unknown;
      skipAuth?: boolean;
    } = {},
  ): Promise<T> {
    try {
      return await this.rawRequest<T>(path, options);
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 401 &&
        !options.skipAuth
      ) {
        const refreshed = await this.tryRefresh();
        if (refreshed) {
          return this.rawRequest<T>(path, options);
        }
      }
      throw error;
    }
  }

  private async tryRefresh(): Promise<boolean> {
    const rt = this.getRefreshToken?.();
    if (!rt) {
      this.onRefreshFailed?.();
      return false;
    }

    try {
      if (!this.refreshPromise) {
        this.refreshPromise = this.refreshToken(rt);
      }
      const tokens = await this.refreshPromise;
      this.onTokenRefreshed?.(tokens.access_token, tokens.refresh_token ?? null);
      return true;
    } catch {
      this.onRefreshFailed?.();
      return false;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async rawRequest<T>(
    path: string,
    options: {
      method?: "GET" | "POST" | "PUT";
      body?: unknown;
      skipAuth?: boolean;
    } = {},
  ): Promise<T> {
    const headers = new Headers();
    headers.set("Accept", "application/json");

    if (options.body !== undefined) {
      headers.set("Content-Type", "application/json");
    }

    const token = options.skipAuth ? null : this.getToken?.();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method: options.method ?? "GET",
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
      });
    } catch (error) {
      throw new ApiError(
        "Could not reach the Dishify API. Check that the backend is running.",
        "network",
        undefined,
        error,
      );
    }

    if (!response.ok) {
      throw await buildApiError(response, path);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }
}

export const apiClient = new ApiClient({
  getToken: () => window.localStorage.getItem("dishify.access_token"),
  getRefreshToken: () => window.localStorage.getItem("dishify.refresh_token"),
  onTokenRefreshed: (accessToken, refreshToken) => {
    window.localStorage.setItem("dishify.access_token", accessToken);
    if (refreshToken) {
      window.localStorage.setItem("dishify.refresh_token", refreshToken);
    }
  },
  onRefreshFailed: () => {
    window.localStorage.removeItem("dishify.access_token");
    window.localStorage.removeItem("dishify.refresh_token");
  },
});

function getConfiguredApiUrl() {
  return import.meta.env.VITE_API_URL || DEFAULT_API_URL;
}

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

async function buildApiError(response: Response, path: string) {
  const payload = await readErrorPayload(response);
  const message = errorMessageFor(response.status, payload?.detail, path);
  return new ApiError(message, errorCodeFor(response.status), response.status, payload?.detail);
}

async function readErrorPayload(response: Response): Promise<ApiErrorPayload | null> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  try {
    return (await response.json()) as ApiErrorPayload;
  } catch {
    return null;
  }
}

function errorCodeFor(status: number): ApiErrorCode {
  if (status === 401) {
    return "auth";
  }
  if (status === 422) {
    return "validation";
  }
  if (status === 503) {
    return "unavailable";
  }
  return "unknown";
}

function errorMessageFor(status: number, detail: unknown, path: string) {
  if (status === 401) {
    if (path === "/auth/login") {
      return detailToText(detail) ?? "Invalid username or password.";
    }
    return "Your session is missing or expired. Log in again.";
  }
  if (status === 422) {
    return detailToText(detail) ?? "Some fields need attention before Dishify can continue.";
  }
  if (status === 503) {
    return "Dishify is not ready yet. Try again in a moment.";
  }
  return "Something went wrong. Try again.";
}

function detailToText(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && "msg" in item) {
          return String(item.msg);
        }
        return null;
      })
      .filter(Boolean)
      .join(" ");
  }
  return null;
}
