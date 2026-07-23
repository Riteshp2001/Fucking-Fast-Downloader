'use client';

import { useEffect } from "react";
import { useUpdateChecker } from "@/hooks/useUpdateChecker";

export default function UpdateBanner() {
  const { available, checking, downloading, progress, check, download } = useUpdateChecker();

  useEffect(() => {
    check();
  }, [check]);

  if (!available || checking) return null;

  const mb = progress > 0 && progress < 100 ? (progress / 1024 / 1024).toFixed(1) : "";

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-[#2d1b69] border-b border-[#3d2b79] text-sm">
      <span className="text-[#c084fc] font-medium">Update {available.version} available</span>
      <span className="text-[#a78bfa] text-xs truncate flex-1">{available.body}</span>
      {downloading ? (
        <span className="text-[#a78bfa] text-xs">{mb ? `${mb} MB downloaded` : "Downloading..."}</span>
      ) : (
        <button
          onClick={download}
          className="px-3 py-1 rounded bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-xs font-medium transition-colors"
        >
          Download & Install
        </button>
      )}
    </div>
  );
}
