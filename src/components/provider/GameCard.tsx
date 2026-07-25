'use client';

import React from 'react';
import Image from 'next/image';
import type { SearchResult } from '@/types/provider';
import { DownloadSquare } from '@solar-icons/react';

interface GameCardProps {
  result: SearchResult;
  onSelect: (result: SearchResult) => void;
}

export default function GameCard({ result, onSelect }: GameCardProps) {
  return (
    <button
      onClick={() => onSelect(result)}
      className="w-full text-left flex gap-3 p-3 rounded-xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/60 hover:bg-[var(--md-sys-color-surface-container-high)] transition-all cursor-pointer group"
    >
      {result.image && (
        <div className="w-16 h-16 rounded-lg overflow-hidden shrink-0 bg-[var(--md-sys-color-surface-container-highest)]">
          <Image
            src={result.image}
            alt=""
            width={64}
            height={64}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <h3 className="text-xs font-bold text-[var(--md-sys-color-on-surface)] truncate">
          {result.title}
        </h3>
        {result.description && (
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] mt-0.5 line-clamp-2">
            {result.description}
          </p>
        )}
        <div className="flex items-center gap-2 mt-1">
          {result.size && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-teal-500/15 text-teal-400 border border-teal-500/30">
              {result.size}
            </span>
          )}
        </div>
      </div>
      <div className="shrink-0 self-center opacity-0 group-hover:opacity-100 transition-opacity">
        <DownloadSquare size={18} className="text-teal-400" />
      </div>
    </button>
  );
}
