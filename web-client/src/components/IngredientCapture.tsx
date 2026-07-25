import { useEffect, useRef, useState, type ChangeEvent } from "react";

import { Alert, Badge, Box, Button, Chip, Group, Image, Modal, Overlay, Stack, Text } from "@mantine/core";

import { ApiError, apiClient } from "../api/client";
import type { DetectedIngredient } from "../api/types";
import { blobToBase64, parseDataUrl } from "../media/encode";

type CaptureMode = "choose" | "camera" | "review";

type Props = {
  opened: boolean;
  onConfirm: (ingredients: DetectedIngredient[]) => void;
  onClose: () => void;
};

export function IngredientCapture({ opened, onConfirm, onClose }: Props) {
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
    <Modal
      opened={opened}
      onClose={() => {
        stopCamera();
        onClose();
      }}
      onExitTransitionEnd={reset}
      title="Scan ingredients"
      // size={640}
      centered
    >
      <Stack gap="md">
        {error ? (
          <Alert variant="light" color="red" title="Error">
            {error}
          </Alert>
        ) : null}

        {mode === "choose" ? (
          <Stack gap="md">
            <Text c="dimmed" size="sm">
              Point your camera at your fridge or pantry, or upload a photo.
            </Text>
            <Group gap="sm">
              <Button type="button" onClick={openCamera}>
                📷 Open camera
              </Button>
              <Button type="button" variant="default" onClick={() => fileInputRef.current?.click()}>
                Upload photo
              </Button>
            </Group>
            <input ref={fileInputRef} type="file" accept="image/*" hidden onChange={handleUpload} />
          </Stack>
        ) : null}

        {mode === "camera" ? (
          <Stack gap="md">
            <video
              ref={videoRef}
              playsInline
              muted
              style={{ width: "100%", borderRadius: 12, background: "#000", maxHeight: "60vh", display: "block" }}
            />
            <Group gap="sm">
              <Button type="button" onClick={capturePhoto}>
                Capture
              </Button>
              <Button type="button" variant="subtle" color="gray" onClick={reset}>
                Cancel
              </Button>
            </Group>
          </Stack>
        ) : null}

        {mode === "review" ? (
          <Stack gap="md">
            <Box pos="relative" style={{ display: "inline-block", lineHeight: 0, borderRadius: 12, overflow: "hidden" }}>
              {imageUrl ? <Image src={imageUrl} alt="Captured ingredients" radius="md" /> : null}
              {detected.map((item, index) =>
                item.box && item.box.length === 4 ? (
                  <Box
                    key={index}
                    onClick={() => toggle(index)}
                    style={{
                      position: "absolute",
                      left: `${item.box[0] * 100}%`,
                      top: `${item.box[1] * 100}%`,
                      width: `${(item.box[2] - item.box[0]) * 100}%`,
                      height: `${(item.box[3] - item.box[1]) * 100}%`,
                      borderRadius: 6,
                      cursor: "pointer",
                      border: `2px solid ${
                        hovered === index
                          ? "var(--mantine-color-green-6)"
                          : selected.has(index)
                            ? "var(--mantine-primary-color-filled)"
                            : "rgba(255, 255, 255, 0.7)"
                      }`,
                      background: selected.has(index) ? "var(--mantine-primary-color-light)" : "transparent",
                      transition: "border-color 120ms ease, background 120ms ease",
                    }}
                  >
                    <Badge
                      color={selected.has(index) ? undefined : "dark"}
                      variant="filled"
                      size="sm"
                      tt="none"
                      style={{ position: "absolute", top: "-1.4rem", left: -2, pointerEvents: "none" }}
                    >
                      {item.name}
                    </Badge>
                  </Box>
                ) : null,
              )}
              {isDetecting ? (
                <Overlay color="#000" backgroundOpacity={0.35} radius="md" center>
                  <Text c="white" fw={700}>
                    Detecting…
                  </Text>
                </Overlay>
              ) : null}
            </Box>

            {detected.length ? (
              <>
                <Text c="dimmed" size="sm">
                  Tap an item to include or exclude it, then add to your pantry.
                </Text>
                <Group gap="xs">
                  {detected.map((item, index) => (
                    <Chip
                      key={index}
                      checked={selected.has(index)}
                      onChange={() => toggle(index)}
                      wrapperProps={{
                        onMouseEnter: () => setHovered(index),
                        onMouseLeave: () => setHovered(null),
                      }}
                    >
                      {item.raw_text || item.name}
                    </Chip>
                  ))}
                </Group>
              </>
            ) : null}

            <Group gap="sm">
              <Button type="button" onClick={confirm} disabled={isDetecting || selected.size === 0}>
                Add {selected.size || ""} to pantry
              </Button>
              <Button type="button" variant="subtle" color="gray" onClick={reset}>
                Retake
              </Button>
            </Group>
          </Stack>
        ) : null}
      </Stack>
    </Modal>
  );
}
