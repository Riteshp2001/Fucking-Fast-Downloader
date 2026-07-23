'use client';

import React from 'react';
import { open as openUrl } from '@tauri-apps/plugin-shell';
import { useAppStore } from '@/stores/app-store';
import { isTauri } from '@/lib/tauri';
import {
  Bolt, CupHot, Global, Widget, ShieldCheck,
  AltArrowRight, Layers, SpeedometerMax, CodeSquare,
  UserCheck, ClipboardText, Server, Monitor
} from '@solar-icons/react';

const GITHUB_URL = 'https://github.com/Riteshp2001/Fucking-Fast-Downloader';
const COFFEE_URL = 'https://buymeacoffee.com/riteshp2001/e/367661';
const PORTFOLIO_URL = 'https://riteshdpandit.vercel.app';

export default function AboutPanel() {
  const { engineStatus } = useAppStore();

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

  const stackItems = [
    { label: 'Desktop Framework', value: 'Tauri v2 (Rust)', icon: Widget },
    { label: 'Download Engine', value: 'Aria2 RPC', icon: Bolt },
    { label: 'UI Framework', value: 'Next.js 16 + React 19', icon: Global },
    { label: 'Design System', value: 'Material 3 Expressive', icon: Layers },
  ];

  const systemStats = [
    { label: 'RPC Protocol', value: 'JSON-RPC over HTTP', icon: Server },
    { label: 'Engine Status', value: engineStatus.toUpperCase(), icon: Bolt },
    { label: 'OS Platform', value: 'Windows x64 / Multi-OS', icon: Monitor },
    { label: 'Open Source', value: 'MIT License', icon: ShieldCheck },
  ];

  return (
    <div className="h-full flex flex-col justify-between overflow-hidden text-[var(--md-sys-color-on-surface)] select-none gap-4 p-1 animate-slide-up-emil">
      {/* 1. Brand Hero Banner */}
      <div className="bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] rounded-2xl p-4 px-5 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] flex items-center justify-center font-bold shrink-0 border border-[var(--md-sys-color-outline-variant)] shadow-sm">
              <Bolt size={24} className="fill-current" />
            </div>

            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <h1 className="text-base font-bold tracking-tight text-[var(--md-sys-color-on-surface)]">
                  Fucking Fast Downloader
                </h1>
                <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-primary)] border border-[var(--md-sys-color-outline-variant)]">
                  v0.1.0-alpha
                </span>
              </div>
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                A modern, blazingly fast download manager & repack scraper built with Next.js, Rust & Aria2.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => openExternal(GITHUB_URL)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface)] border border-[var(--md-sys-color-outline-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)] active-press transition-all cursor-pointer shadow-sm"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
              </svg>
              <span>GitHub</span>
            </button>

            <button
              onClick={() => openExternal(COFFEE_URL)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)] border border-[var(--md-sys-color-outline-variant)] hover:opacity-90 active-press transition-all cursor-pointer shadow-sm"
            >
              <CupHot size={16} />
              <span>Coffee</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Key Capabilities Grid (4 Columns) */}
      <div className="flex-1 flex flex-col justify-center">
        <h2 className="text-[10px] font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)] mb-2.5">
          Key Features & Capabilities
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 flex-1">
          <div className="bg-[var(--md-sys-color-surface-container)] p-3.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)] hover-lift flex flex-col justify-between">
            <div>
              <div className="w-8 h-8 rounded-xl bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] flex items-center justify-center mb-2.5">
                <SpeedometerMax size={18} />
              </div>
              <h3 className="text-xs font-bold mb-1 text-[var(--md-sys-color-on-surface)]">Multi-Segment Speed</h3>
              <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                Accelerates downloads using 16–32 parallel TCP streams per host.
              </p>
            </div>
          </div>

          <div className="bg-[var(--md-sys-color-surface-container)] p-3.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)] hover-lift flex flex-col justify-between">
            <div>
              <div className="w-8 h-8 rounded-xl bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] flex items-center justify-center mb-2.5">
                <Widget size={18} />
              </div>
              <h3 className="text-xs font-bold mb-1 text-[var(--md-sys-color-on-surface)]">Magnet & BitTorrent</h3>
              <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                Native peer-to-peer downloading for magnet URIs, torrent files & metalinks.
              </p>
            </div>
          </div>

          <div className="bg-[var(--md-sys-color-surface-container)] p-3.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)] hover-lift flex flex-col justify-between">
            <div>
              <div className="w-8 h-8 rounded-xl bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)] flex items-center justify-center mb-2.5">
                <Layers size={18} />
              </div>
              <h3 className="text-xs font-bold mb-1 text-[var(--md-sys-color-on-surface)]">FitGirl Scraper</h3>
              <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                Integrated mirror resolver for FuckingFast, DataNodes & game hosts.
              </p>
            </div>
          </div>

          <div className="bg-[var(--md-sys-color-surface-container)] p-3.5 rounded-2xl border border-[var(--md-sys-color-outline-variant)] hover-lift flex flex-col justify-between">
            <div>
              <div className="w-8 h-8 rounded-xl bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-primary)] flex items-center justify-center mb-2.5 border border-[var(--md-sys-color-outline-variant)]">
                <ClipboardText size={18} />
              </div>
              <h3 className="text-xs font-bold mb-1 text-[var(--md-sys-color-on-surface)]">Smart Auto-Detect</h3>
              <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                Automatically detects copied repack links from your clipboard for 1-click scraping.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Bottom 3-Column Equal Height Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-stretch flex-1">
        {/* Architecture & Tech Stack Card */}
        <div className="bg-[var(--md-sys-color-surface-container)] p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-lg bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] flex items-center justify-center">
                <CodeSquare size={14} />
              </div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)]">
                Technology Stack
              </h3>
            </div>

            <div className="space-y-2">
              {stackItems.map((item, idx) => {
                const IconComponent = item.icon;
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 px-2.5 rounded-xl bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/40"
                  >
                    <div className="flex items-center gap-2">
                      <IconComponent size={13} className="text-[var(--md-sys-color-on-surface-variant)]" />
                      <span className="text-xs font-medium text-[var(--md-sys-color-on-surface)]">
                        {item.label}
                      </span>
                    </div>

                    <span className="text-[10px] font-mono font-semibold text-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-surface-container-lowest)] px-2 py-0.5 rounded-full border border-[var(--md-sys-color-outline-variant)]/50">
                      {item.value}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Engine Telemetry Card */}
        <div className="bg-[var(--md-sys-color-surface-container)] p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-lg bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] flex items-center justify-center">
                <Server size={14} />
              </div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)]">
                Engine Telemetry
              </h3>
            </div>

            <div className="space-y-2">
              {systemStats.map((item, idx) => {
                const IconComponent = item.icon;
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 px-2.5 rounded-xl bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/40"
                  >
                    <div className="flex items-center gap-2">
                      <IconComponent size={13} className="text-[var(--md-sys-color-on-surface-variant)]" />
                      <span className="text-xs font-medium text-[var(--md-sys-color-on-surface)]">
                        {item.label}
                      </span>
                    </div>

                    <span className="text-[10px] font-mono font-semibold text-[var(--md-sys-color-secondary)] bg-[var(--md-sys-color-surface-container-lowest)] px-2 py-0.5 rounded-full border border-[var(--md-sys-color-outline-variant)]/50">
                      {item.value}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Developer & Credits Card */}
        <div className="bg-[var(--md-sys-color-surface-container)] p-4 rounded-2xl border border-[var(--md-sys-color-outline-variant)] flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-lg bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)] flex items-center justify-center">
                <UserCheck size={14} />
              </div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)]">
                Developer & Open Source
              </h3>
            </div>

            {/* Author Profile Highlight */}
            <div className="flex items-center gap-3 p-2.5 px-3 rounded-xl bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/40 mb-3">
              <div className="w-9 h-9 rounded-full bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] font-bold text-xs flex items-center justify-center border border-[var(--md-sys-color-outline-variant)] shrink-0">
                RP
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-[var(--md-sys-color-on-surface)]">Ritesh Pandit</span>
                  <span className="text-[9px] font-mono font-bold px-2 py-0.2 rounded-full bg-[var(--md-sys-color-surface-container-lowest)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]">Creator</span>
                </div>
                <span className="text-[10px] text-[var(--md-sys-color-on-surface-variant)]">Lead Engineer & Architect</span>
              </div>
            </div>

            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              Released as open-source software under the permissive MIT License. Contributions and feedback are welcome!
            </p>
          </div>

          {/* Card Footer Actions */}
          <div className="pt-2.5 border-t border-[var(--md-sys-color-outline-variant)]/50 flex items-center justify-between mt-2">
            <button
              onClick={() => openExternal(PORTFOLIO_URL)}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-surface-container-highest)] active-press transition-all cursor-pointer border border-[var(--md-sys-color-outline-variant)]/50"
            >
              <Global size={13} />
              <span>Developer Portfolio</span>
              <AltArrowRight size={13} />
            </button>

            <div className="flex items-center gap-1.5 text-[10px] font-mono font-semibold text-[var(--md-sys-color-on-surface-variant)] bg-[var(--md-sys-color-surface-container-high)] px-2.5 py-1 rounded-full border border-[var(--md-sys-color-outline-variant)]/50">
              <ShieldCheck size={13} className="text-[var(--md-sys-color-primary)]" />
              <span>MIT License</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
