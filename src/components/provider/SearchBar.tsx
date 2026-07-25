'use client';

import React, { useState, useCallback } from 'react';
import { searchProvider } from '@/lib/tauri';
import type { SearchResult } from '@/types/provider';
import { MinimalisticMagnifier as SearchIcon, CloseCircle } from '@solar-icons/react';

interface SearchBarProps {
  onResults: (results: SearchResult[]) => void;
  onLoading: (loading: boolean) => void;
  onError: (error: string | null) => void;
}

export default function SearchBar({ onResults, onLoading, onError }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearch = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      onResults([]);
      return;
    }

    onLoading(true);
    onError(null);

    try {
      const results = await searchProvider('fitgirl', q.trim());
      onResults(results);
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
      onResults([]);
    } finally {
      onLoading(false);
    }
  }, [onResults, onLoading, onError]);

  const handleChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => handleSearch(value), 400);
  };

  const handleClear = () => {
    setQuery('');
    onResults([]);
  };

  return (
    <div className="relative">
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60">
        <SearchIcon size={16} className="text-[var(--md-sys-color-on-surface-variant)] shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Search games..."
          className="flex-1 bg-transparent text-xs text-[var(--md-sys-color-on-surface)] placeholder:text-[var(--md-sys-color-on-surface-variant)]/60 focus:outline-none"
        />
        {query && (
          <button onClick={handleClear} className="text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] cursor-pointer">
            <CloseCircle size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
