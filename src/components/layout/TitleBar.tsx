'use client';

import React, { useRef, useEffect } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { open as openUrl } from '@tauri-apps/plugin-shell';
import { Magnifer, Bolt, CupHot } from '@solar-icons/react';
import { isTauri } from '@/lib/tauri';

const GITHUB_URL = 'https://github.com/Riteshp2001/Fucking-Fast-Downloader';
const COFFEE_URL = 'https://buymeacoffee.com/riteshp2001/e/367661';

export default function TitleBar() {
  const inputRef = useRef<HTMLInputElement>(null);

  const minimize = () => isTauri() && getCurrentWindow().minimize();
  const toggleMaximize = () => isTauri() && getCurrentWindow().toggleMaximize();
  const close = () => isTauri() && getCurrentWindow().close();

  const openExternal = async (url: string) => {
    try {
      if (isTauri()) {
        await openUrl(url);
      } else {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
    } catch (err) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div
      data-tauri-drag-region
      className="h-11 bg-[var(--md-sys-color-surface-container)] border-b border-[var(--md-sys-color-outline-variant)] flex items-center justify-between px-4 select-none z-50 relative"
    >
      {/* Brand Identity & Quick Links */}
      <div className="flex items-center gap-2.5">
        <div className="flex items-center gap-2 pointer-events-none">
          <div className="w-6 h-6 rounded-md bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] flex items-center justify-center font-bold">
            <Bolt size={14} className="fill-current" />
          </div>
          <span className="text-xs font-semibold text-[var(--md-sys-color-on-surface)] tracking-wide">FF Downloader</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)] font-semibold border border-[var(--md-sys-color-outline-variant)]">v0.1</span>
        </div>

        {/* GitHub & Buy Me a Coffee Links */}
        <div className="flex items-center gap-1.5 ml-2" data-tauri-drag-region={false}>
          {/* GitHub Link */}
          <button
            type="button"
            onClick={() => openExternal(GITHUB_URL)}
            title="View Source on GitHub"
            className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)] text-[10px] font-medium transition-all active-press cursor-pointer"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            <span>GitHub</span>
          </button>

          {/* Buy Me a Coffee Link */}
          <button
            type="button"
            onClick={() => openExternal(COFFEE_URL)}
            title="Support Development on Buy Me a Coffee"
            className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)] border border-[var(--md-sys-color-outline-variant)] text-[10px] font-semibold transition-all active-press hover:opacity-90 cursor-pointer"
          >
            <CupHot size={12} />
            <span>Coffee</span>
          </button>
        </div>
      </div>

      {/* Global Search Bar - Material 3 Expressive Search Bar */}
      <div className="flex-1 flex justify-center max-w-md mx-4" data-tauri-drag-region={false}>
        <div className="relative w-full max-w-xs group flex items-center">
          <Magnifer size={14} className="absolute left-3 text-[var(--md-sys-color-on-surface-variant)] group-focus-within:text-[var(--md-sys-color-primary)] transition-colors duration-150 pointer-events-none" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search downloads..."
            className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-xl py-1.5 pl-9 pr-14 text-xs text-[var(--md-sys-color-on-surface)] placeholder:text-[var(--md-sys-color-on-surface-variant)] focus:outline-none focus:border-[var(--md-sys-color-primary)] focus:ring-1 focus:ring-[var(--md-sys-color-primary)]/20 transition-all duration-150"
          />
          <kbd className="absolute right-2.5 text-[10px] font-mono font-medium text-[var(--md-sys-color-on-surface-variant)] bg-[var(--md-sys-color-surface-container-lowest)] px-1.5 py-0.5 rounded-md border border-[var(--md-sys-color-outline-variant)] pointer-events-none select-none">
            Ctrl K
          </kbd>
        </div>
      </div>

      {/* Window Controls */}
      <div className="flex items-center gap-1" data-tauri-drag-region={false}>
        <button
          onClick={minimize}
          aria-label="Minimize window"
          className="w-7 h-7 rounded-md flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] hover:text-[var(--md-sys-color-on-surface)] transition-all text-xs cursor-pointer"
        >
          ⎯
        </button>
        <button
          onClick={toggleMaximize}
          aria-label="Maximize window"
          className="w-7 h-7 rounded-md flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] hover:text-[var(--md-sys-color-on-surface)] transition-all text-xs cursor-pointer"
        >
          ▢
        </button>
        <button
          onClick={close}
          aria-label="Close window"
          className="w-7 h-7 rounded-md flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-error-container)] hover:text-[var(--md-sys-color-on-error-container)] transition-all text-xs cursor-pointer"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
