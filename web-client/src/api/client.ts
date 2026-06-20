import type {
  ApiErrorPayload,
  AuthConfigResponse,
  HealthResponse,
  LoginRequest,
  RecommendRequest,
  RecommendResponse,
  RegisterRequest,
  RegisterResponse,
  TokenResponse,
  UpdatePreferencesRequest,
  UserPreferences,
  UserProfile,
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

export type ApiClientOptions = {
  baseUrl?: string;
  getToken?: () => string | null;
};

export class ApiClient {
  private readonly baseUrl: string;
  private readonly getToken?: () => string | null;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? getConfiguredApiUrl());
    this.getToken = options.getToken;
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

  private async request<T>(
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
      throw await buildApiError(response);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }
}

export const apiClient = new ApiClient({
  getToken: () => window.localStorage.getItem("dishify.access_token"),
});

function getConfiguredApiUrl() {
  return import.meta.env.VITE_API_URL || DEFAULT_API_URL;
}

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

async function buildApiError(response: Response) {
  const payload = await readErrorPayload(response);
  const message = errorMessageFor(response.status, payload?.detail);
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

function errorMessageFor(status: number, detail: unknown) {
  const detailText = detailToText(detail);
  if (detailText) {
    return detailText;
  }

  if (status === 401) {
    return "Your session is missing or expired. Log in again.";
  }
  if (status === 422) {
    return "Some fields need attention before Dishify can continue.";
  }
  if (status === 503) {
    return "Dishify is not ready yet. Check backend services and indexing.";
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
