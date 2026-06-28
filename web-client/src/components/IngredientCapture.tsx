import { useEffect, useRef, useState, type ChangeEvent } from "react";

import { ApiError, apiClient } from "../api/client";
import type { DetectedIngredient } from "../api/types";
import { blobToBase64, parseDataUrl } from "../media/encode";
import { Button } from "./Button";

type CaptureMode = "choose" | "camera" | "review";

type Props = {
  onConfirm: (ingredients: DetectedIngredient[]) => void;
  onClose: () => void;
};

export function IngredientCapture({ onConfirm, onClose }: Props) {
  const [mode, setMode] = useState<CaptureMode>("choose");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [detected, setDetected] = useState<DetectedIngredient[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [hovered, setHovered] = useState<number | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  useEffect(() => stopCamera, []);

  async function openCamera() {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Camera is not supported in this browser — use Upload instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      setMode("camera");
      // attach after the video element renders
      requestAnimationFrame(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play();
        }
      });
    } catch {
      setError("Camera access was denied — use Upload instead.");
    }
  }

  function capturePhoto() {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    stopCamera();
    const { base64, mimeType } = parseDataUrl(dataUrl, "image/jpeg");
    void runDetection(dataUrl, base64, mimeType);
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const { base64, mimeType } = await blobToBase64(file, "image/jpeg");
    void runDetection(URL.createObjectURL(file), base64, mimeType);
  }

  async function runDetection(displayUrl: string, base64: string, mimeType: string) {
    setMode("review");
    setImageUrl(displayUrl);
    setDetected([]);
    setSelected(new Set());
    setError(null);
    setIsDetecting(true);
    try {
      const { ingredients } = await apiClient.detectIngredients({
        image_base64: base64,
        mime_type: mimeType,
      });
      setDetected(ingredients);
      setSelected(new Set(ingredients.map((_, index) => index)));
      if (!ingredients.length) {
        setError("No ingredients recognized. Try a clearer photo.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not read the photo.");
    } finally {
      setIsDetecting(false);
    }
  }

  function toggle(index: number) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function confirm() {
    onConfirm(detected.filter((_, index) => selected.has(index)));
    onClose();
  }

  function reset() {
    stopCamera();
    setMode("choose");
    setImageUrl(null);
    setDetected([]);
    setSelected(new Set());
    setError(null);
  }

  return (
    <div className="capture-overlay" role="dialog" aria-modal="true">
      <div className="capture-modal">
        <div className="capture-head">
          <h2>Scan ingredients</h2>
          <button type="button" className="link-button" onClick={() => { stopCamera(); onClose(); }}>
            Close
          </button>
        </div>

        {error ? <p className="alert alert-error">{error}</p> : null}

        {mode === "choose" ? (
          <div className="capture-choose">
            <p className="muted">Point your camera at your fridge or pantry, or upload a photo.</p>
            <div className="button-row">
              <Button type="button" onClick={openCamera}>📷 Open camera</Button>
              <Button type="button" variant="secondary" onClick={() => fileInputRef.current?.click()}>
                Upload photo
              </Button>
            </div>
            <input ref={fileInputRef} type="file" accept="image/*" hidden onChange={handleUpload} />
          </div>
        ) : null}

        {mode === "camera" ? (
          <div className="capture-camera">
            <video ref={videoRef} className="capture-video" playsInline muted />
            <div className="button-row">
              <Button type="button" onClick={capturePhoto}>Capture</Button>
              <Button type="button" variant="ghost" onClick={reset}>Cancel</Button>
            </div>
          </div>
        ) : null}

        {mode === "review" ? (
          <div className="capture-review">
            <div className="capture-stage">
              {imageUrl ? <img src={imageUrl} alt="Captured ingredients" className="capture-image" /> : null}
              {detected.map((item, index) =>
                item.box && item.box.length === 4 ? (
                  <div
                    key={index}
                    className={`capture-box${selected.has(index) ? " on" : ""}${hovered === index ? " hovered" : ""}`}
                    style={{
                      left: `${item.box[0] * 100}%`,
                      top: `${item.box[1] * 100}%`,
                      width: `${(item.box[2] - item.box[0]) * 100}%`,
                      height: `${(item.box[3] - item.box[1]) * 100}%`,
                    }}
                    onClick={() => toggle(index)}
                  >
                    <span className="capture-box-label">{item.name}</span>
                  </div>
                ) : null,
              )}
              {isDetecting ? <div className="capture-detecting">Detecting…</div> : null}
            </div>

            {detected.length ? (
              <>
                <p className="muted">Tap an item to include or exclude it, then add to your pantry.</p>
                <ul className="capture-list">
                  {detected.map((item, index) => (
                    <li
                      key={index}
                      className={selected.has(index) ? "on" : ""}
                      onMouseEnter={() => setHovered(index)}
                      onMouseLeave={() => setHovered(null)}
                    >
                      <label>
                        <input type="checkbox" checked={selected.has(index)} onChange={() => toggle(index)} />
                        <span>{item.raw_text || item.name}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}

            <div className="button-row">
              <Button type="button" onClick={confirm} disabled={isDetecting || selected.size === 0}>
                Add {selected.size || ""} to pantry
              </Button>
              <Button type="button" variant="ghost" onClick={reset}>Retake</Button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
