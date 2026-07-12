import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "./client";

function mockFetch(responses: Array<{ status: number; body?: unknown; headers?: Record<string, string> }>) {
  let callIndex = 0;
  return vi.fn(async () => {
    const res = responses[callIndex++] ?? responses[responses.length - 1];
    return {
      ok: res.status >= 200 && res.status < 300,
      status: res.status,
      headers: new Headers({ "content-type": "application/json", ...res.headers }),
      json: async () => res.body,
    } as Response;
  });
}

describe("ApiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("defaults to the local gateway when VITE_API_URL is not configured", async () => {
    const fetch = mockFetch([{ status: 200, body: { status: "ok", service: "test" } }]);
    vi.stubGlobal("fetch", fetch);
    vi.stubEnv("VITE_API_URL", "");

    const client = new ApiClient();
    await client.health();

    expect(fetch).toHaveBeenCalledOnce();
    const call = fetch.mock.calls[0] as unknown[];
    expect(call[0]).toBe("http://localhost:8000/health");
  });

  it("attaches bearer token on authenticated requests", async () => {
    const fetch = mockFetch([{ status: 200, body: { status: "ok", service: "test" } }]);
    vi.stubGlobal("fetch", fetch);

    const client = new ApiClient({
      baseUrl: "http://localhost:8000",
      getToken: () => "my-token",
    });
    await client.health();

    expect(fetch).toHaveBeenCalledOnce();
    const call = fetch.mock.calls[0] as unknown[];
    const init = call[1] as RequestInit;
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer my-token");
  });

  it("skips auth on login requests", async () => {
    const fetch = mockFetch([{
      status: 200,
      body: { access_token: "at", expires_in: 300, token_type: "Bearer" },
    }]);
    vi.stubGlobal("fetch", fetch);

    const client = new ApiClient({
      baseUrl: "http://localhost:8000",
      getToken: () => "my-token",
    });
    await client.login({ username: "user", password: "pass" });

    const call = fetch.mock.calls[0] as unknown[];
    const init = call[1] as RequestInit;
    expect((init.headers as Headers).get("Authorization")).toBeNull();
  });

  it("retries with refreshed token on 401", async () => {
    const fetch = mockFetch([
      { status: 401, body: { detail: "expired" } },
      { status: 200, body: { access_token: "new-at", expires_in: 300, refresh_token: "new-rt", token_type: "Bearer" } },
      { status: 200, body: { id: "u1", username: "test" } },
    ]);
    vi.stubGlobal("fetch", fetch);

    const onTokenRefreshed = vi.fn();
    let token = "old-token";
    const client = new ApiClient({
      baseUrl: "http://localhost:8000",
      getToken: () => token,
      getRefreshToken: () => "old-rt",
      onTokenRefreshed: (at, rt) => {
        token = at;
        onTokenRefreshed(at, rt);
      },
    });

    const profile = await client.me();

    expect(profile.username).toBe("test");
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(onTokenRefreshed).toHaveBeenCalledWith("new-at", "new-rt");
  });

  it("calls onRefreshFailed and throws when refresh fails", async () => {
    const fetch = mockFetch([
      { status: 401, body: { detail: "expired" } },
      { status: 401, body: { detail: "bad refresh" } },
    ]);
    vi.stubGlobal("fetch", fetch);

    const onRefreshFailed = vi.fn();
    const client = new ApiClient({
      baseUrl: "http://localhost:8000",
      getToken: () => "bad-token",
      getRefreshToken: () => "bad-rt",
      onRefreshFailed,
    });

    await expect(client.me()).rejects.toThrow(ApiError);
    expect(onRefreshFailed).toHaveBeenCalledOnce();
  });

  it("calls onRefreshFailed when no refresh token available", async () => {
    const fetch = mockFetch([
      { status: 401, body: { detail: "expired" } },
    ]);
    vi.stubGlobal("fetch", fetch);

    const onRefreshFailed = vi.fn();
    const client = new ApiClient({
      baseUrl: "http://localhost:8000",
      getToken: () => "bad-token",
      getRefreshToken: () => null,
      onRefreshFailed,
    });

    await expect(client.me()).rejects.toThrow(ApiError);
    expect(onRefreshFailed).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("maps 422 to validation error", async () => {
    vi.stubGlobal("fetch", mockFetch([
      { status: 422, body: { detail: "Unknown restriction tag" } },
    ]));

    const client = new ApiClient({ baseUrl: "http://localhost:8000" });

    try {
      await client.recommend({ query: "test", top_k: 3 });
      expect.unreachable("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe("validation");
    }
  });

  it("maps 503 to unavailable error", async () => {
    vi.stubGlobal("fetch", mockFetch([
      { status: 503, body: { detail: "Qdrant not indexed" } },
    ]));

    const client = new ApiClient({ baseUrl: "http://localhost:8000" });

    try {
      await client.recommend({ query: "test", top_k: 3 });
      expect.unreachable("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe("unavailable");
    }
  });

  it("posts voice and vision media requests to gateway endpoints with auth", async () => {
    const fetch = mockFetch([
      {
        status: 200,
        body: {
          transcript: "eggs and rice",
          ingredients: [],
          query: null,
        },
      },
      {
        status: 200,
        body: {
          ingredients: [],
        },
      },
    ]);
    vi.stubGlobal("fetch", fetch);

    const client = new ApiClient({
      baseUrl: "http://localhost:8000",
      getToken: () => "media-token",
    });

    await client.voice({ audio_base64: "abc", mime_type: "audio/webm" });
    await client.detectIngredients({ image_base64: "def", mime_type: "image/jpeg" });

    expect(fetch).toHaveBeenCalledTimes(2);
    const voiceCall = fetch.mock.calls[0] as unknown[];
    const visionCall = fetch.mock.calls[1] as unknown[];
    expect(voiceCall[0]).toBe("http://localhost:8000/voice");
    expect(visionCall[0]).toBe("http://localhost:8000/vision/ingredients");
    expect(((voiceCall[1] as RequestInit).headers as Headers).get("Authorization")).toBe(
      "Bearer media-token",
    );
    expect(((visionCall[1] as RequestInit).headers as Headers).get("Authorization")).toBe(
      "Bearer media-token",
    );
  });

  it("throws network error when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));

    const client = new ApiClient({ baseUrl: "http://localhost:8000" });

    try {
      await client.health();
      expect.unreachable("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe("network");
    }
  });

  it("sends logout with refresh token", async () => {
    const fetch = mockFetch([{ status: 204 }]);
    vi.stubGlobal("fetch", fetch);

    const client = new ApiClient({ baseUrl: "http://localhost:8000" });
    await client.logout("my-refresh-token");

    const call = fetch.mock.calls[0] as unknown[];
    expect(call[0]).toBe("http://localhost:8000/auth/logout");
    expect(JSON.parse((call[1] as RequestInit).body as string)).toEqual({ refresh_token: "my-refresh-token" });
  });
});
