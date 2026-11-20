import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { api, ApiError } from "../lib/api";
import { useSession } from "../lib/session";
import { Button, Icon, Spinner } from "./ui";

function dataUrlToBlob(dataUrl: string): Blob {
  const parts = dataUrl.split(",");
  const mime = parts[0].match(/:(.*?);/)?.[1] || "image/jpeg";
  const binary = atob(parts[1]);
  const array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    array[i] = binary.charCodeAt(i);
  }
  return new Blob([array], { type: mime });
}

interface UnitView {
  id: number;
  side: string;
  image: { id: number; width: number; height: number; bytes: number } | null;
}

interface Unit {
  id: number;
  garment_code: string;
  views: UnitView[];
}

interface MobileCameraModalProps {
  lotId: number;
  lotCode: string;
  units: Unit[];
  cloudinaryConfigured?: boolean;
  lanIp?: string;
  publicBaseUrl?: string;
  isTunnel?: boolean;
  sessionToken?: string;
  initialMode?: "camera" | "qr";
  onClose: () => void;
  onUploadSuccess: () => Promise<void> | void;
}

export function MobileCameraModal({
  lotId,
  lotCode,
  units,
  cloudinaryConfigured = false,
  lanIp,
  publicBaseUrl,
  isTunnel = false,
  sessionToken,
  initialMode = "camera",
  onClose,
  onUploadSuccess,
}: MobileCameraModalProps) {
  const { t, lang } = useSession();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Tab mode: "camera" or "qr"
  const [mode, setMode] = useState<"camera" | "qr">(initialMode);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [streamActive, setStreamActive] = useState(false);
  const [cameraError, setCameraError] = useState("");

  // Target view
  const allViews = units.flatMap((u) =>
    u.views.map((v) => ({
      unitId: u.id,
      garmentCode: u.garment_code,
      viewId: v.id,
      side: v.side,
      hasImage: !!v.image,
    }))
  );

  const firstPending = allViews.find((v) => !v.hasImage) || allViews[0];
  const [selectedViewId, setSelectedViewId] = useState<number>(firstPending?.viewId || 0);

  // Sync selectedViewId whenever units / allViews load or change
  useEffect(() => {
    if ((!selectedViewId || !allViews.some((v) => v.viewId === selectedViewId)) && allViews.length > 0) {
      const pending = allViews.find((v) => !v.hasImage) || allViews[0];
      if (pending) {
        setSelectedViewId(pending.viewId);
      }
    }
  }, [allViews, selectedViewId]);

  const currentTarget = allViews.find((v) => v.viewId === selectedViewId);

  // Captured frame preview URL
  const [capturedPreviewUrl, setCapturedPreviewUrl] = useState<string | null>(null);

  // Clean up object URL on unmount or preview reset
  useEffect(() => {
    return () => {
      if (capturedPreviewUrl) {
        URL.revokeObjectURL(capturedPreviewUrl);
      }
    };
  }, [capturedPreviewUrl]);

  // Uploading state & feedback
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [uploadType, setUploadType] = useState<"info" | "success" | "error">("info");
  const [flash, setFlash] = useState(false);
  const lastCaptureTimeRef = useRef<number>(0);

  // Initialize camera stream
  useEffect(() => {
    if (mode !== "camera") return;
    let stream: MediaStream | null = null;

    async function initCamera() {
      setCameraError("");
      try {
        const constraints: MediaStreamConstraints = {
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1920, min: 640 },
            height: { ideal: 1080, min: 480 },
          },
          audio: false,
        };
        try {
          stream = await navigator.mediaDevices.getUserMedia(constraints);
        } catch (cErr) {
          console.warn("Detailed constraints failed, falling back to basic facingMode:", cErr);
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: facingMode },
            audio: false,
          });
        }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.setAttribute("autoplay", "");
          videoRef.current.setAttribute("muted", "");
          videoRef.current.setAttribute("playsinline", "true");
          videoRef.current.muted = true;
          try {
            await videoRef.current.play();
          } catch (playErr) {
            console.warn("Video play error:", playErr);
          }
          setStreamActive(true);
        }
      } catch (err) {
        console.warn("Camera stream access failed:", err);
        setCameraError(
          lang === "en"
            ? "Camera permission denied or unavailable. Use the Native button below."
            : "ক্যামেরা পারমিশন পাওয়া যায়নি। নিচের নেটিভ বাটনটি ব্যবহার করুন।"
        );
        setStreamActive(false);
      }
    }

    if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
      initCamera();
    } else {
      setCameraError(
        lang === "en"
          ? "Camera API not supported in this browser environment."
          : "এই ব্রাউজারে সরাসরি ক্যামেরা সমর্থন করে না।"
      );
    }

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [facingMode, mode, lang]);

  const toggleFacingMode = () => {
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  };

  const handleShutterTrigger = (e?: React.SyntheticEvent) => {
    if (e && e.type === "touchend") {
      e.preventDefault(); // Prevent synthetic click duplication on mobile
    }
    const now = Date.now();
    if (now - lastCaptureTimeRef.current < 400) {
      return;
    }
    lastCaptureTimeRef.current = now;
    handleCapture(e);
  };

  const handleCapture = async (e?: React.SyntheticEvent) => {
    console.log("[MobileCamera] CAPTURE_CLICKED", {
      eventType: e?.type || "direct",
      target: (e?.target as HTMLElement)?.tagName,
      isUploading,
      selectedViewId,
      allViewsCount: allViews.length,
    });

    if (isUploading) {
      console.warn("[MobileCamera] CAPTURE_IGNORED_UPLOADING");
      return;
    }

    const video = videoRef.current;
    if (!video) {
      console.error("[MobileCamera] VIDEO_REF_MISSING");
      setUploadStatus(lang === "en" ? "Camera element not found." : "ক্যামেরা এলিমেন্ট পাওয়া যায়নি।");
      setUploadType("error");
      return;
    }

    console.log("[MobileCamera] VIDEO_READY", {
      readyState: video.readyState,
      videoWidth: video.videoWidth,
      videoHeight: video.videoHeight,
    });

    if (video.paused || !video.videoWidth || !video.videoHeight || video.readyState < 2) {
      try {
        await video.play();
      } catch (_) {}
      let waited = 0;
      while ((!video.videoWidth || !video.videoHeight) && waited < 900) {
        await new Promise((r) => setTimeout(r, 100));
        waited += 100;
      }
    }

    if (!video.videoWidth || !video.videoHeight) {
      console.warn("[MobileCamera] VIDEO_NOT_READY after waiting, triggering native fallback");
      const nativeInput = document.getElementById("nativeFallbackInput") as HTMLInputElement | null;
      if (nativeInput) {
        setUploadStatus(lang === "en" ? "Opening native camera..." : "ডিভাইসের ক্যামেরা খোলা হচ্ছে...");
        setUploadType("info");
        nativeInput.click();
        return;
      }
      setUploadStatus(
        lang === "en"
          ? "Camera feed initializing, please wait a moment..."
          : "ক্যামেরা প্রস্তুত হচ্ছে, কিছুক্ষণ পর চেষ্টা করুন..."
      );
      setUploadType("error");
      return;
    }

    const targetId = selectedViewId || (allViews.length > 0 ? allViews[0].viewId : 0);
    if (!targetId || allViews.length === 0) {
      console.error("[MobileCamera] NO_TARGET_VIEW", { selectedViewId, allViews });
      setUploadStatus(
        lang === "en"
          ? "No garment inspection view available. Please register garments first."
          : "কোনো গার্মেন্ট ভিউ পাওয়া যায়নি। প্রথমে গার্মেন্ট যুক্ত করুন।"
      );
      setUploadType("error");
      return;
    }

    // Trigger visual flash & haptic
    setFlash(true);
    setTimeout(() => setFlash(false), 120);
    if (navigator.vibrate) {
      try {
        navigator.vibrate(60);
      } catch {
        // quiet ignore
      }
    }

    // Prepare Canvas
    const canvas = canvasRef.current || document.createElement("canvas");
    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      console.error("[MobileCamera] CANVAS_CONTEXT_FAILED");
      setUploadStatus(lang === "en" ? "Failed to initialize canvas context." : "ক্যানভাস কনটেক্সট পাওয়া যায়নি।");
      setUploadType("error");
      return;
    }

    try {
      ctx.drawImage(video, 0, 0, width, height);
      console.log("[MobileCamera] CANVAS_DRAW_SUCCESS", { canvasWidth: width, canvasHeight: height });
    } catch (drawErr) {
      console.error("[MobileCamera] CANVAS_DRAW_FAILED", drawErr);
      setUploadStatus(lang === "en" ? "Failed to capture video frame." : "ফ্রেম ড্র করতে ব্যর্থ হয়েছে।");
      setUploadType("error");
      return;
    }

    const processBlob = async (blob: Blob | null) => {
      let finalBlob = blob;
      if (!finalBlob) {
        console.warn("[MobileCamera] canvas.toBlob returned null, attempting dataUrl fallback");
        try {
          const dataUrl = canvas.toDataURL("image/jpeg", 0.90);
          finalBlob = dataUrlToBlob(dataUrl);
        } catch (fbErr) {
          console.error("[MobileCamera] dataUrl fallback failed:", fbErr);
        }
      }

      if (!finalBlob) {
        console.error("[MobileCamera] IMAGE_BLOB_CREATION_FAILED");
        setUploadStatus(lang === "en" ? "Failed to process captured image." : "ছবি প্রসেস ব্যর্থ হয়েছে।");
        setUploadType("error");
        return;
      }

      console.log("[MobileCamera] IMAGE_BLOB_CREATED", {
        size: finalBlob.size,
        type: finalBlob.type,
      });

      try {
        const previewUrl = URL.createObjectURL(finalBlob);
        setCapturedPreviewUrl(previewUrl);
        console.log("[MobileCamera] IMAGE_PREVIEW_UPDATED", { previewUrl });
      } catch (prevErr) {
        console.warn("[MobileCamera] createObjectURL error:", prevErr);
      }

      await uploadImageFile(finalBlob, targetId);
    };

    try {
      canvas.toBlob(
        (blob) => {
          processBlob(blob);
        },
        "image/jpeg",
        0.90
      );
    } catch (toBlobErr) {
      console.warn("[MobileCamera] canvas.toBlob threw exception, using synchronous toDataURL:", toBlobErr);
      try {
        const dataUrl = canvas.toDataURL("image/jpeg", 0.90);
        const fbBlob = dataUrlToBlob(dataUrl);
        processBlob(fbBlob);
      } catch (err) {
        console.error("[MobileCamera] Synchronous dataUrl fallback also failed:", err);
        setUploadStatus(lang === "en" ? "Image processing exception." : "ছবি প্রক্রিয়াকরণে সমস্যা।");
        setUploadType("error");
      }
    }
  };

  const handleNativeFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try {
      const previewUrl = URL.createObjectURL(file);
      setCapturedPreviewUrl(previewUrl);
      console.log("[MobileCamera] IMAGE_PREVIEW_UPDATED", { previewUrl, source: "native" });
    } catch (prevErr) {
      console.warn("[MobileCamera] createObjectURL error:", prevErr);
    }
    await uploadImageFile(file);
    e.target.value = "";
  };

  const uploadImageFile = async (fileOrBlob: Blob | File, viewIdToUpload?: number) => {
    const targetId = viewIdToUpload || selectedViewId || (allViews.length > 0 ? allViews[0].viewId : 0);
    if (!targetId) {
      setUploadType("error");
      setUploadStatus(lang === "en" ? "Please select a target view first." : "অনুগ্রহ করে একটি ভিউ নির্বাচন করুন।");
      return;
    }

    setIsUploading(true);
    setUploadType("info");
    setUploadStatus(lang === "en" ? "Processing image..." : "ছবি প্রসেস হচ্ছে...");
    console.log("[MobileCamera] IMAGE_UPLOAD_STARTED", { viewId: targetId, bytes: fileOrBlob.size, cloudinaryConfigured });

    try {
      if (cloudinaryConfigured) {
        // 1. Direct Cloudinary Signed Upload
        setUploadStatus(lang === "en" ? "Uploading to Cloudinary..." : "ক্লাউডিনারিতে আপলোড হচ্ছে...");
        const signData = await api.get<{
          configured: boolean;
          upload_url: string;
          api_key: string;
          timestamp: number;
          signature: string;
          folder: string;
          tags: string;
        }>(`/api/lots/${lotId}/views/${targetId}/cloudinary-sign`);

        if (signData.configured) {
          const cldForm = new FormData();
          cldForm.append("file", fileOrBlob, "mobile_cam.jpg");
          cldForm.append("api_key", signData.api_key);
          cldForm.append("timestamp", String(signData.timestamp));
          cldForm.append("signature", signData.signature);
          cldForm.append("folder", signData.folder);
          cldForm.append("tags", signData.tags);

          const cldResp = await fetch(signData.upload_url, { method: "POST", body: cldForm });
          if (!cldResp.ok) throw new Error(`Cloudinary upload failed: HTTP ${cldResp.status}`);
          const cldJson = await cldResp.json();

          // 2. Register receipt with backend
          setUploadStatus(lang === "en" ? "Running AI Defect Detection..." : "এআই শনাক্তকরণ চলছে...");
          const result = await api.post<{
            ok: boolean;
            image_id: number;
            next_view: { view_id: number; garment_code: string; side: string } | null;
            lot_complete: boolean;
          }>(`/api/lots/${lotId}/views/${targetId}/register-cloudinary`, {
            public_id: cldJson.public_id,
            secure_url: cldJson.secure_url,
            width: cldJson.width,
            height: cldJson.height,
            bytes: cldJson.bytes,
            captured_at: new Date().toISOString(),
          });

          console.log("[MobileCamera] IMAGE_UPLOAD_SUCCESS", result);
          handleSuccess(result);
          return;
        }
      }

      // Fallback: Standard Server Upload
      setUploadStatus(lang === "en" ? "Uploading to Lotline..." : "লটলাইনে আপলোড হচ্ছে...");
      const formData = new FormData();
      formData.append("file", fileOrBlob, "capture.jpg");
      const uploadRes = await api.postForm<{
        ok: boolean;
        image_id: number;
        next_view?: { view_id: number; garment_code: string; side: string } | null;
      }>(`/api/lots/${lotId}/views/${targetId}/upload`, formData);

      console.log("[MobileCamera] IMAGE_UPLOAD_SUCCESS", uploadRes);
      // Auto-advance
      handleSuccess({ next_view: findNextPending(targetId) });
    } catch (err) {
      console.error("[MobileCamera] IMAGE_UPLOAD_FAILED", err);
      const msg = err instanceof ApiError ? String(err.detail) : (err as Error).message;
      setUploadType("error");
      setUploadStatus(lang === "en" ? `Upload failed: ${msg}` : `আপলোড ব্যর্থ: ${msg}`);
    } finally {
      setIsUploading(false);
    }
  };

  const findNextPending = (currentId: number) => {
    const next = allViews.find((v) => v.viewId !== currentId && !v.hasImage);
    return next ? { view_id: next.viewId, garment_code: next.garmentCode, side: next.side } : null;
  };

  const handleSuccess = (res?: {
    next_view?: { view_id: number; garment_code: string; side: string } | null;
    lot_complete?: boolean;
  }) => {
    setUploadType("success");
    setUploadStatus(lang === "en" ? "Captured & Saved! ✓" : "সংরক্ষিত ও এআই বিশ্লেষণ সম্পন্ন! ✓");
    onUploadSuccess();

    if (res?.next_view) {
      setTimeout(() => {
        setCapturedPreviewUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return null;
        });
        setSelectedViewId(res.next_view!.view_id);
        setUploadStatus("");
      }, 700);
    } else {
      setTimeout(() => {
        setCapturedPreviewUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return null;
        });
        setUploadStatus(lang === "en" ? "All views complete! 🎉" : "সকল ভিউয়ের কাজ সম্পন্ন! 🎉");
      }, 500);
    }
  };

  const initialBase =
    publicBaseUrl ||
    (lanIp && lanIp !== "127.0.0.1"
      ? `http://${lanIp}:8077`
      : window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? "http://192.168.0.102:8077"
      : `${window.location.protocol}//${window.location.host}`);

  const [activeBaseUrl, setActiveBaseUrl] = useState<string>(initialBase);
  const [tunnelActive, setTunnelActive] = useState<boolean>(!!isTunnel);
  const [activeSessionToken, setActiveSessionToken] = useState<string>(sessionToken || "");
  const [qrDataUrl, setQrDataUrl] = useState<string>("");
  const [editingUrl, setEditingUrl] = useState(false);
  const [copied, setCopied] = useState(false);

  // Sync with prop updates
  useEffect(() => {
    if (publicBaseUrl) {
      setActiveBaseUrl(publicBaseUrl);
      setTunnelActive(!!isTunnel);
    }
  }, [publicBaseUrl, isTunnel]);

  useEffect(() => {
    if (sessionToken) {
      setActiveSessionToken(sessionToken);
    }
  }, [sessionToken]);

  // Periodic poll for dynamic tunnel detection while QR screen is open
  useEffect(() => {
    if (mode !== "qr") return;
    const pollStatus = async () => {
      try {
        const res = await api.get<{ active: boolean; public_base_url: string; session_token?: string }>("/api/tunnel-status");
        if (res && res.public_base_url) {
          setActiveBaseUrl(res.public_base_url);
          setTunnelActive(res.active);
          if (res.session_token) {
            setActiveSessionToken(res.session_token);
          }
        }
      } catch {
        // quiet fallback
      }
    };
    pollStatus();
    const interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, [mode]);

  const qrUrl = `${activeBaseUrl.replace(/\/+$/, "")}/lots/${lotId}/mobile-cam${
    activeSessionToken ? `?session_token=${encodeURIComponent(activeSessionToken)}` : ""
  }`;

  // Generate QR code locally in memory
  useEffect(() => {
    if (!qrUrl) return;
    QRCode.toDataURL(qrUrl, {
      width: 260,
      margin: 1,
      color: { dark: "#0f172a", light: "#ffffff" },
    })
      .then((url) => setQrDataUrl(url))
      .catch((err) => {
        console.error("Local QR generation failed", err);
        setQrDataUrl("");
      });
  }, [qrUrl]);

  const copyQrLink = () => {
    navigator.clipboard.writeText(qrUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "#080c15",
        display: "flex",
        flexDirection: "column",
        color: "var(--text-light, #fff)",
        overflow: "hidden",
      }}
    >
      {/* Top Bar */}
      <div
        style={{
          padding: "12px 18px",
          background: "#0f172a",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          zIndex: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "rgba(255,255,255,0.1)",
              border: "none",
              color: "#fff",
              borderRadius: "6px",
              padding: "6px 10px",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 600,
            }}
          >
            ← {lang === "en" ? "Gallery" : "গ্যালারি"}
          </button>
          <span style={{ fontWeight: 700, fontSize: "14px", color: "var(--lime, #86efac)" }}>
            {lotCode}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            type="button"
            onClick={() => setMode(mode === "camera" ? "qr" : "camera")}
            style={{
              background: mode === "qr" ? "#2563eb" : "rgba(255,255,255,0.1)",
              border: "none",
              color: "#fff",
              borderRadius: "6px",
              padding: "6px 12px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <Icon name={mode === "camera" ? "scan-line" : "camera"} size={14} />
            <span>{mode === "camera" ? (lang === "en" ? "Scan Phone QR" : "ফোন কিউআর") : (lang === "en" ? "Live Camera" : "লাইভ ক্যামেরা")}</span>
          </button>
        </div>
      </div>

      {mode === "qr" ? (
        /* QR Code Screen */
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            textAlign: "center",
            background: "#0b0f19",
          }}
        >
          <div
            style={{
              background: "#ffffff",
              padding: "18px",
              borderRadius: "14px",
              boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
              marginBottom: "16px",
              minWidth: "220px",
              minHeight: "220px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {qrDataUrl ? (
              <img
                src={qrDataUrl}
                alt="Lotline Phone Camera QR"
                style={{ width: "220px", height: "220px", display: "block" }}
              />
            ) : (
              <div style={{ width: "220px", height: "220px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Spinner />
              </div>
            )}
          </div>

          <div style={{ marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 700,
                padding: "4px 10px",
                borderRadius: "999px",
                background: tunnelActive ? "rgba(34, 197, 94, 0.2)" : "rgba(148, 163, 184, 0.2)",
                color: tunnelActive ? "#4ade80" : "#94a3b8",
                border: `1px solid ${tunnelActive ? "rgba(34, 197, 94, 0.4)" : "rgba(148, 163, 184, 0.3)"}`,
              }}
            >
              {tunnelActive ? "🔒 HTTPS Tunnel Active" : "📶 Local Network (LAN)"}
            </span>
          </div>

          <h3 style={{ fontSize: "18px", fontWeight: 700, margin: "0 0 6px" }}>
            {lang === "en" ? "Scan with Smartphone Camera" : "মোবাইল ক্যামেরা দিয়ে স্ক্যান করুন"}
          </h3>
          <p style={{ maxWidth: "420px", color: "var(--text-muted, #94a3b8)", fontSize: "13px", lineHeight: 1.5, margin: "0 0 12px" }}>
            {tunnelActive
              ? (lang === "en" ? "Secure HTTPS active. Chrome on Android and Safari on iOS will grant instant camera access." : "নিরাপদ HTTPS সক্রিয়। অ্যান্ড্রয়েড ক্রোম এবং আইওএস সাফারি সরাসরি ক্যামেরা ওপেন করবে।")
              : (lang === "en" ? "Ensure your phone is on the same Wi-Fi. (Android Chrome camera requires HTTPS tunnel)." : "আপনার ফোনটি একই ওয়াইফাই নেটওয়ার্কে কানেক্ট রাখুন। (অ্যান্ড্রয়েড ক্রোমে ক্যামেরা পেতে HTTPS টানেল প্রয়োজন)।")}
          </p>

          {/* Direct Link Pill & Copy */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "#1e293b",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: "8px",
              padding: "6px 12px",
              maxWidth: "480px",
              marginBottom: "14px",
            }}
          >
            {editingUrl ? (
              <input
                type="text"
                value={activeBaseUrl}
                onChange={(e) => setActiveBaseUrl(e.target.value)}
                style={{
                  background: "#0f172a",
                  color: "#fff",
                  border: "1px solid #3b82f6",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontFamily: "monospace",
                  flex: 1,
                }}
              />
            ) : (
              <span style={{ fontFamily: "monospace", fontSize: "12.5px", color: "var(--sky, #38bdf8)", flex: 1, wordBreak: "break-all" }}>
                {qrUrl}
              </span>
            )}
            <button
              type="button"
              onClick={copyQrLink}
              style={{
                background: copied ? "#16a34a" : "rgba(255,255,255,0.1)",
                border: "none",
                color: "#fff",
                borderRadius: "4px",
                padding: "4px 8px",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {copied ? "Copied! ✓" : "Copy"}
            </button>
            <button
              type="button"
              onClick={() => setEditingUrl(!editingUrl)}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted, #94a3b8)",
                fontSize: "11px",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              {editingUrl ? "Done" : "Edit URL"}
            </button>
          </div>

          <div>
            <Button size="sm" variant="subtle" onClick={() => setMode("camera")}>
              {lang === "en" ? "← Back to Browser Camera" : "← ব্রাউজার ক্যামেরায় ফিরুন"}
            </Button>
          </div>
        </div>
      ) : (
        /* Camera Viewfinder Screen */
        <>
          {/* Target Banner */}
          <div
            style={{
              background: "#111827",
              padding: "10px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "17px", fontWeight: 800 }}>
                {currentTarget?.garmentCode || "All Views"}
              </span>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  padding: "3px 8px",
                  borderRadius: "6px",
                  background: currentTarget?.side === "back" ? "#9333ea" : "#2563eb",
                  color: "var(--text-light, #fff)",
                }}
              >
                {currentTarget?.side || "DONE"}
              </span>
            </div>

            <select
              value={selectedViewId}
              onChange={(e) => setSelectedViewId(Number(e.target.value))}
              style={{
                background: "#1e293b",
                color: "var(--text-light, #fff)",
                border: "1px solid rgba(255,255,255,0.2)",
                padding: "6px 10px",
                borderRadius: "6px",
                fontSize: "12.5px",
                maxWidth: "180px",
              }}
            >
              {allViews.map((v) => (
                <option key={v.viewId} value={v.viewId}>
                  {v.garmentCode} · {v.side} {v.hasImage ? "✓" : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Video Preview */}
          <div
            style={{
              flex: 1,
              position: "relative",
              background: "#000",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
            }}
          >
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />

            {/* Grid Overlay */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                pointerEvents: "none",
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gridTemplateRows: "1fr 1fr 1fr",
              }}
            >
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
              <div style={{ border: "1px solid rgba(255,255,255,0.07)" }}></div>
            </div>

            {/* Guide Box */}
            <div
              style={{
                position: "absolute",
                top: "12%",
                bottom: "12%",
                left: "10%",
                right: "10%",
                border: "2px dashed rgba(134,239,172,0.6)",
                borderRadius: "12px",
                pointerEvents: "none",
                boxShadow: "0 0 0 9999px rgba(0,0,0,0.35)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span
                style={{
                  background: "rgba(0,0,0,0.75)",
                  color: "var(--text-light, #f1f5f9)",
                  fontSize: "12px",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  backdropFilter: "blur(4px)",
                }}
              >
                {lang === "en" ? "Fit garment panel in frame" : "পোশাকের প্যানেল ফ্রেমে রাখুন"}
              </span>
            </div>

            {/* Flash Effect */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "#ffffff",
                opacity: flash ? 0.85 : 0,
                transition: "opacity 0.1s ease-out",
                pointerEvents: "none",
                zIndex: 30,
              }}
            />

            {/* Captured Preview Overlay */}
            {capturedPreviewUrl ? (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  zIndex: 25,
                  background: "#000000",
                }}
              >
                <img
                  src={capturedPreviewUrl}
                  alt="Captured frame preview"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: "16px",
                    left: "16px",
                    background: "rgba(0,0,0,0.75)",
                    color: "var(--green-light, #86efac)",
                    padding: "4px 10px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <Icon name="check" size={14} />
                  <span>{lang === "en" ? "Captured Frame" : "ক্যাপচারকৃত ছবি"}</span>
                </div>
                {!isUploading && (
                  <button
                    type="button"
                    onClick={() => {
                      if (capturedPreviewUrl) {
                        URL.revokeObjectURL(capturedPreviewUrl);
                        setCapturedPreviewUrl(null);
                      }
                      setUploadStatus("");
                    }}
                    style={{
                      position: "absolute",
                      bottom: "16px",
                      right: "16px",
                      background: "rgba(15,23,42,0.85)",
                      border: "1px solid rgba(255,255,255,0.2)",
                      color: "var(--text-light, #f1f5f9)",
                      padding: "6px 14px",
                      borderRadius: "8px",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                      zIndex: 35,
                    }}
                  >
                    {lang === "en" ? "↺ Retake" : "↺ পুনরায় তুলুন"}
                  </button>
                )}
              </div>
            ) : null}

            {/* Toast Status */}
            {uploadStatus ? (
              <div
                style={{
                  position: "absolute",
                  top: "20px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  background:
                    uploadType === "success"
                      ? "#065f46"
                      : uploadType === "error"
                      ? "#991b1b"
                      : "rgba(15,23,42,0.92)",
                  color: "#fff",
                  padding: "8px 18px",
                  borderRadius: "999px",
                  fontSize: "13px",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                  zIndex: 40,
                }}
              >
                {isUploading && <Spinner />}
                <span>{uploadStatus}</span>
              </div>
            ) : null}

            {cameraError ? (
              <div
                style={{
                  position: "absolute",
                  background: "rgba(15,23,42,0.95)",
                  padding: "16px 20px",
                  borderRadius: "10px",
                  maxWidth: "320px",
                  textAlign: "center",
                  color: "var(--red-light, #f87171)",
                  fontSize: "13px",
                  zIndex: 35,
                }}
              >
                {cameraError}
              </div>
            ) : null}
          </div>

          <canvas ref={canvasRef} style={{ display: "none" }} />

          {/* Controls */}
          <div
            style={{
              background: "#0b0f19",
              padding: "18px 20px 24px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
              borderTop: "1px solid rgba(255,255,255,0.1)",
              position: "relative",
              zIndex: 50,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "36px" }}>
              {/* Native file upload fallback */}
              <label
                style={{
                  cursor: "pointer",
                  color: "var(--text-muted, #94a3b8)",
                  fontSize: "11.5px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <Icon name="upload" size={20} />
                <span>{lang === "en" ? "Native" : "নেটিভ"}</span>
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleNativeFileSelect}
                  style={{ display: "none" }}
                />
              </label>

              {/* Shutter Button */}
              <button
                type="button"
                disabled={isUploading}
                onClick={handleShutterTrigger}
                onTouchEnd={handleShutterTrigger}
                aria-label="Capture photo"
                style={{
                  width: "74px",
                  height: "74px",
                  borderRadius: "50%",
                  background: "#ffffff",
                  border: "5px solid #3b82f6",
                  boxShadow: "0 0 0 4px rgba(255,255,255,0.25), 0 8px 24px rgba(0,0,0,0.5)",
                  cursor: isUploading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: isUploading ? 0.6 : 1,
                  transition: "transform 0.1s",
                  touchAction: "manipulation",
                  WebkitTapHighlightColor: "transparent",
                  userSelect: "none",
                  WebkitUserSelect: "none",
                  padding: 0,
                  outline: "none",
                }}
              >
                <div
                  style={{
                    width: "56px",
                    height: "56px",
                    borderRadius: "50%",
                    background: "#2563eb",
                    pointerEvents: "none",
                  }}
                />
              </button>

              {/* Flip camera */}
              <button
                type="button"
                onClick={toggleFacingMode}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-muted, #94a3b8)",
                  fontSize: "11.5px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "4px",
                  touchAction: "manipulation",
                }}
              >
                <Icon name="rotate-ccw" size={20} />
                <span>{lang === "en" ? "Flip" : "ক্যামেরা"}</span>
              </button>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text-dim, #64748b)" }}>
              {cloudinaryConfigured ? (
                <span style={{ color: "var(--success, #10b981)" }}>● Cloudinary Direct Sync Active</span>
              ) : (
                <span style={{ color: "var(--warning, #f59e0b)" }}>● Local Storage Active</span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
