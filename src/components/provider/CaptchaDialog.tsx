'use client';

import React from 'react';
import { solveProviderCaptcha } from '@/lib/tauri';
import { ShieldWarning } from '@solar-icons/react';

interface CaptchaDialogProps {
  isOpen: boolean;
  onClose: () => void;
  url: string;
}

export default function CaptchaDialog({ isOpen, onClose, url }: CaptchaDialogProps) {
  if (!isOpen) return null;

  const handleSolve = async () => {
    try {
      await solveProviderCaptcha('fitgirl', url);
      onClose();
    } catch (err) {
      console.error('Captcha solving failed:', err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-neutral-950/70 backdrop-blur-md" onClick={onClose} />
      <div className="bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-3xl p-6 max-w-md w-full relative z-10 shadow-2xl text-center">
        <div className="w-12 h-12 rounded-2xl bg-amber-500/15 text-amber-400 flex items-center justify-center mx-auto mb-4 border border-amber-500/20">
          <ShieldWarning size={24} />
        </div>
        <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)] mb-2">DDoS-Guard Verification</h3>
        <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mb-5 leading-relaxed">
          FitGirl-repacks.site is protected by DDoS-Guard. A browser window will open for you to complete the verification.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold rounded-xl border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] transition-all cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleSolve}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-teal-400 to-emerald-400 text-neutral-950 hover:from-teal-300 hover:to-emerald-300 transition-all cursor-pointer"
          >
            Open Browser
          </button>
        </div>
      </div>
    </div>
  );
}
