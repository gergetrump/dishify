export type EncodedMedia = {
  base64: string;
  mimeType: string;
};

/**
 * Split a `data:<mime>;base64,<data>` URL into its mime type and raw base64 payload.
 * Falls back to the provided default mime type when the URL has none.
 */
export function parseDataUrl(dataUrl: string, fallbackMime: string): EncodedMedia {
  const match = /^data:([^;,]*)[^,]*,(.*)$/s.exec(dataUrl);
  if (!match) {
    throw new Error("Unsupported data URL");
  }
  const [, mime, payload] = match;
  return {
    base64: payload,
    mimeType: mime || fallbackMime,
  };
}

/** Read a Blob/File into base64 + mime type using a FileReader. */
export function blobToBase64(blob: Blob, fallbackMime = "application/octet-stream"): Promise<EncodedMedia> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("Could not read file"));
    reader.onload = () => {
      try {
        resolve(parseDataUrl(String(reader.result), blob.type || fallbackMime));
      } catch (error) {
        reject(error);
      }
    };
    reader.readAsDataURL(blob);
  });
}
