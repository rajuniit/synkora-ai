import { describe, it, expect, beforeEach, vi } from "vitest";
import { secureStorage } from "../auth/secure-storage";

// Reset in-memory token state before each test by calling clearTokens
beforeEach(() => {
  secureStorage.clearTokens();
  vi.restoreAllMocks();
});

describe("SecureTokenStorage", () => {
  describe("storeTokens / getAccessToken", () => {
    it("returns stored access token", () => {
      secureStorage.storeTokens({ access_token: "tok_abc", expires_in: 3600 });
      expect(secureStorage.getAccessToken()).toBe("tok_abc");
    });

    it("returns null before any token is stored", () => {
      expect(secureStorage.getAccessToken()).toBeNull();
    });

    it("returns null after clearTokens", () => {
      secureStorage.storeTokens({ access_token: "tok_abc", expires_in: 3600 });
      secureStorage.clearTokens();
      expect(secureStorage.getAccessToken()).toBeNull();
    });

    it("returns null when token has expired", () => {
      // Store with a negative expires_in so it's already past expiry
      secureStorage.storeTokens({ access_token: "tok_expired", expires_in: -1 });
      expect(secureStorage.getAccessToken()).toBeNull();
    });

    it("ignores the refresh_token field (cookie-only)", () => {
      secureStorage.storeTokens({
        access_token: "tok_access",
        refresh_token: "tok_refresh_ignored",
        expires_in: 3600,
      });
      // Only the access token should be accessible
      expect(secureStorage.getAccessToken()).toBe("tok_access");
    });
  });

  describe("isTokenExpired", () => {
    it("returns true when no token is stored", () => {
      expect(secureStorage.isTokenExpired()).toBe(true);
    });

    it("returns false for a freshly stored token", () => {
      secureStorage.storeTokens({ access_token: "tok_fresh", expires_in: 3600 });
      expect(secureStorage.isTokenExpired()).toBe(false);
    });

    it("returns true when within the 5-minute pre-expiry window", () => {
      // expires_in of 200 seconds is under the 300-second buffer
      secureStorage.storeTokens({ access_token: "tok_near", expires_in: 200 });
      expect(secureStorage.isTokenExpired()).toBe(true);
    });

    it("returns true after clearTokens", () => {
      secureStorage.storeTokens({ access_token: "tok_fresh", expires_in: 3600 });
      secureStorage.clearTokens();
      expect(secureStorage.isTokenExpired()).toBe(true);
    });
  });

  describe("refreshAccessToken", () => {
    it("returns true and updates the access token on success", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: { access_token: "tok_new", expires_in: 3600 },
        }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const result = await secureStorage.refreshAccessToken();
      expect(result).toBe(true);
      expect(secureStorage.getAccessToken()).toBe("tok_new");
    });

    it("returns false and clears tokens on HTTP error", async () => {
      const mockFetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });
      vi.stubGlobal("fetch", mockFetch);

      secureStorage.storeTokens({ access_token: "tok_old", expires_in: 3600 });
      const result = await secureStorage.refreshAccessToken();
      expect(result).toBe(false);
      expect(secureStorage.getAccessToken()).toBeNull();
    });

    it("returns false and clears tokens on network error", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));

      secureStorage.storeTokens({ access_token: "tok_old", expires_in: 3600 });
      const result = await secureStorage.refreshAccessToken();
      expect(result).toBe(false);
      expect(secureStorage.getAccessToken()).toBeNull();
    });

    it("returns false when response body has no access_token", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: false }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const result = await secureStorage.refreshAccessToken();
      expect(result).toBe(false);
    });
  });
});
