'use client';

import React, { useEffect, useState } from 'react';
import { fetchGameDetail } from '@/lib/tauri';
import type { SearchResult, GameDetail } from '@/types/provider';
import { CloseCircle, Magnet, DownloadSquare } from '@solar-icons/react';

interface GameDetailPanelProps {
  result: SearchResult;
  onClose: () => void;
  onAddDownload: (url: string) => void;
}

export default function GameDetailPanel({ result, onClose, onAddDownload }: GameDetailPanelProps) {
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.resolve()
      .then(() => {
        if (cancelled) return null;
        setLoading(true);
        setError(null);
        setDetail(null);
        return fetchGameDetail('fitgirl', result.url);
      })
      .then((d) => { if (!cancelled && d) setDetail(d); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : String(err)); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [result.url]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-neutral-950/70 backdrop-blur-md" onClick={onClose} />
      <div className="bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-3xl w-full max-w-2xl max-h-[85vh] overflow-y-auto relative z-10 shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-[var(--md-sys-color-surface-container)] px-6 py-4 border-b border-[var(--md-sys-color-outline-variant)]/60 flex items-center justify-between z-10">
          <h2 className="text-sm font-bold text-[var(--md-sys-color-on-surface)] truncate pr-4">
            {result.title}
          </h2>
          <button onClick={onClose} className="shrink-0 text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] cursor-pointer">
            <CloseCircle size={18} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-teal-400 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-500/15 border border-red-500/30 text-red-400 text-xs rounded-xl">
              {error}
            </div>
          )}

          {detail && (
            <>
              {/* Screenshots */}
              {detail.images.length > 0 && (
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {detail.images.map((img, i) => (
                    <img
                      key={i}
                      src={img}
                      alt=""
                      className="h-32 rounded-xl object-cover shrink-0"
                      loading="lazy"
                    />
                  ))}
                </div>
              )}

              {/* Description */}
              {detail.description && (
                <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                  {detail.description}
                </p>
              )}

              {/* Features */}
              {detail.features.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-[var(--md-sys-color-on-surface)] mb-2">Features</h3>
                  <ul className="space-y-1">
                    {detail.features.map((f, i) => (
                      <li key={i} className="text-xs text-[var(--md-sys-color-on-surface-variant)] flex gap-2">
                        <span className="text-teal-400 shrink-0">·</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Magnet Links */}
              {detail.magnet_links.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-[var(--md-sys-color-on-surface)] mb-2">Download</h3>
                  <div className="space-y-2">
                    {detail.magnet_links.map((link, i) => (
                      <button
                        key={i}
                        onClick={() => onAddDownload(link)}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 hover:bg-purple-500/20 text-xs transition-all cursor-pointer"
                      >
                        <Magnet size={14} />
                        <span className="truncate">Magnet Link {i + 1}</span>
                        <DownloadSquare size={14} className="ml-auto shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {detail.direct_links.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-[var(--md-sys-color-on-surface)] mb-2">Direct Links</h3>
                  <div className="space-y-2">
                    {detail.direct_links.map((link, i) => (
                      <button
                        key={i}
                        onClick={() => onAddDownload(link)}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-400 hover:bg-teal-500/20 text-xs transition-all cursor-pointer"
                      >
                        <DownloadSquare size={14} />
                        <span className="truncate">Direct Link {i + 1}</span>
                        <DownloadSquare size={14} className="ml-auto shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {detail.raw_fuckingfast_links.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-[var(--md-sys-color-on-surface)] mb-2">FuckingFast Links</h3>
                  <div className="space-y-2">
                    {detail.raw_fuckingfast_links.map((link, i) => (
                      <button
                        key={i}
                        onClick={() => onAddDownload(link)}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400 hover:bg-sky-500/20 text-xs transition-all cursor-pointer"
                      >
                        <DownloadSquare size={14} />
                        <span className="truncate">Resolve Part {i + 1}</span>
                        <DownloadSquare size={14} className="ml-auto shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
