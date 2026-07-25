'use client';

import React, { useMemo, useState } from 'react';
import type { SearchResult } from '@/types/provider';
import { DownloadSquare } from '@solar-icons/react';

interface GameCardProps {
  result: SearchResult;
  onSelect: (result: SearchResult) => void;
}

export default function GameCard({ result, onSelect }: GameCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const sourceHost = useMemo(() => {
    try {
      return new URL(result.url).hostname.replace(/^www\./, '');
    } catch {
      return 'fitgirl';
    }
  }, [result.url]);
  const hasImage = Boolean(result.image && !imageFailed);

  return (
    <button
      onClick={() => onSelect(result)}
      className="w-full min-h-[104px] text-left grid grid-cols-[72px_1fr_auto] gap-3 p-3 rounded-lg bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/60 hover:bg-[var(--md-sys-color-surface-container-high)] hover:border-teal-400/50 transition-all cursor-pointer group active-press"
      aria-label={`Open ${result.title}`}
    >
      <div className="w-[72px] h-20 rounded-lg overflow-hidden bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline-variant)]/50 shrink-0">
        {hasImage ? (
          <img
            src={result.image}
            alt=""
            className="w-full h-full object-cover"
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-[var(--md-sys-color-surface-container-high)] text-teal-300">
            <DownloadSquare size={22} />
          </div>
        )}
      </div>

      <div className="min-w-0 py-0.5">
        <h3 className="text-[13px] font-bold leading-snug text-[var(--md-sys-color-on-surface)] line-clamp-2">
          {result.title}
        </h3>
        <div className="flex flex-wrap items-center gap-1.5 mt-2">
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-300 border border-teal-500/25">
            FitGirl
          </span>
          {result.size && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/25">
              {result.size}
            </span>
          )}
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--md-sys-color-surface-container-highest)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]/50">
            {sourceHost}
          </span>
        </div>
        {result.description && (
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] mt-2 leading-relaxed line-clamp-2">
            {result.description}
          </p>
        )}
      </div>

      <div className="w-8 h-8 rounded-lg self-center flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/50 group-hover:text-teal-300 group-hover:border-teal-400/40 transition-colors">
        <DownloadSquare size={16} />
      </div>
    </button>
  );
}
