import { beforeEach, describe, expect, it } from "vitest";

import {
  clearStoredAccessToken,
  clearStoredRefreshToken,
  getStoredAccessToken,
  getStoredRefreshToken,
  storeAccessToken,
  storeRefreshToken,
} from "./storage";

describe("auth storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("stores and retrieves access token", () => {
    storeAccessToken("test-at");
    expect(getStoredAccessToken()).toBe("test-at");
  });

  it("stores and retrieves refresh token", () => {
    storeRefreshToken("test-rt");
    expect(getStoredRefreshToken()).toBe("test-rt");
  });

  it("returns null when no tokens stored", () => {
    expect(getStoredAccessToken()).toBeNull();
    expect(getStoredRefreshToken()).toBeNull();
  });

  it("clears access token independently", () => {
    storeAccessToken("at");
    storeRefreshToken("rt");
    clearStoredAccessToken();
    expect(getStoredAccessToken()).toBeNull();
    expect(getStoredRefreshToken()).toBe("rt");
  });

  it("clears refresh token independently", () => {
    storeAccessToken("at");
    storeRefreshToken("rt");
    clearStoredRefreshToken();
    expect(getStoredAccessToken()).toBe("at");
    expect(getStoredRefreshToken()).toBeNull();
  });
});
