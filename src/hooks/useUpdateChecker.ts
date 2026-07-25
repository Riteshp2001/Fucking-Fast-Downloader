import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { UpdateMetadata, UpdateProgressPayload } from "@/types";
import { isTauri } from "@/lib/tauri";

export function useUpdateChecker() {
  const [available, setAvailable] = useState<UpdateMetadata | null>(null);
  const [checking, setChecking] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isTauri()) return;

    let disposed = false;
    let cleanup: (() => void) | undefined;

    listen<UpdateProgressPayload>("update-progress", (e) => {
      const p = e.payload;
      if (p.event === "Started") {
        setProgress(0);
      } else if (p.event === "Progress") {
        setProgress(p.data.downloaded);
      } else if (p.event === "Finished") {
        setProgress(100);
      }
    })
      .then((unlisten) => {
        if (disposed) {
          unlisten();
        } else {
          cleanup = unlisten;
        }
      })
      .catch((error) => {
        console.warn("Failed to listen for update progress:", error);
      });

    return () => {
      disposed = true;
      cleanup?.();
    };
  }, []);

  const check = useCallback(async () => {
    if (!isTauri()) return;
    setChecking(true);
    try {
      const result = await invoke<UpdateMetadata | null>("check_for_update", {
        channel: "stable",
        proxy: null,
      });
      setAvailable(result);
    } catch { /* ignore */ }
    setChecking(false);
  }, []);

  const download = useCallback(async () => {
    if (!isTauri()) return;
    setDownloading(true);
    try {
      const r = await invoke<{ status: string }>("download_update", {
        channel: "stable",
        proxy: null,
      });
      if (r.status === "downloaded") {
        await invoke("apply_update", { channel: "stable", proxy: null });
      }
    } catch { /* ignore */ }
    setDownloading(false);
  }, []);

  return { available, checking, downloading, progress, check, download };
}
