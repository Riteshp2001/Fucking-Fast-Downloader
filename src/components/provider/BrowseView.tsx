'use client';

import React, { useState, useCallback } from 'react';
import { SearchBar, GameCard, GameDetailPanel, ProviderStatus, CaptchaDialog } from '@/components/provider';
import { listProviders } from '@/lib/tauri';
import type { SearchResult, ProviderStatus as ProviderStatusType } from '@/types/provider';
import { useEffect } from 'react';

interface BrowseViewProps {
  onOpenAddDialog: (urls?: string[]) => void;
}

export default function BrowseView({ onOpenAddDialog }: BrowseViewProps) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SearchResult | null>(null);
  const [providers, setProviders] = useState<ProviderStatusType[]>([]);
  const [captchaUrl, setCaptchaUrl] = useState<string | null>(null);

  useEffect(() => {
    listProviders().then(setProviders).catch(console.error);
  }, []);

  const handleAddDownload = useCallback((url: string) => {
    setSelected(null);
    onOpenAddDialog([url]);
  }, [onOpenAddDialog]);

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">Browse Games</h2>
        <ProviderStatus providers={providers} />
      </div>

      <SearchBar
        onResults={setResults}
        onLoading={setLoading}
        onError={setError}
      />

      {error && (
        <div className="p-3 bg-red-500/15 border border-red-500/30 text-red-400 text-xs rounded-xl">
          {error}
          <button
            onClick={() => setCaptchaUrl('https://fitgirl-repacks.site')}
            className="ml-2 underline"
          >
            Solve Captcha
          </button>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-teal-400 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && results.length === 0 && !error && (
        <div className="flex-1 flex items-center justify-center text-center p-8">
          <div>
            <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface-variant)] mb-1">Search for games</h3>
            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]/60">
              Search FitGirl-repacks.site for repacked games
            </p>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2 pr-2">
        {results.map((result, i) => (
          <GameCard
            key={`${result.url}-${i}`}
            result={result}
            onSelect={setSelected}
          />
        ))}
      </div>

      {selected && (
        <GameDetailPanel
          result={selected}
          onClose={() => setSelected(null)}
          onAddDownload={handleAddDownload}
        />
      )}

      {captchaUrl && (
        <CaptchaDialog
          isOpen={true}
          onClose={() => setCaptchaUrl(null)}
          url={captchaUrl}
        />
      )}
    </div>
  );
}
