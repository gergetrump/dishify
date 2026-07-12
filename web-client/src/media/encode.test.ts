import { describe, expect, it } from "vitest";

import { blobToBase64, parseDataUrl } from "./encode";

describe("parseDataUrl", () => {
  it("splits mime type and base64 payload", () => {
    expect(parseDataUrl("data:image/png;base64,AAAB", "image/jpeg")).toEqual({
      base64: "AAAB",
      mimeType: "image/png",
    });
  });

  it("falls back to the provided mime when the data URL has none", () => {
    expect(parseDataUrl("data:;base64,QQ==", "audio/webm")).toEqual({
      base64: "QQ==",
      mimeType: "audio/webm",
    });
  });

  it("throws on a non-data URL", () => {
    expect(() => parseDataUrl("not-a-data-url", "image/jpeg")).toThrow();
  });
});

describe("blobToBase64", () => {
  it("encodes a blob to base64 and reports its mime type", async () => {
    const blob = new Blob(["hi"], { type: "text/plain" });
    const result = await blobToBase64(blob, "application/octet-stream");
    expect(result.mimeType).toBe("text/plain");
    expect(atob(result.base64)).toBe("hi");
  });
});
