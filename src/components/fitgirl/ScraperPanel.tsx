'use client';

import React, { useState, useEffect } from 'react';
import { SIcon } from '@/components/ui/SIcon';
import { scraperFind, scraperAddTask, isTauri } from '@/lib/tauri';
import type { ScrapedItem } from '@/types';
import { readText } from '@tauri-apps/plugin-clipboard-manager';
import {
  Magnifer, Download, DownloadMinimalistic,
  CloseCircle, Global, SafeSquare, ArchiveDownMinimalistic as ArchiveIcon,
  ClipboardText, CheckCircle, Refresh, DoubleAltArrowRight, Widget
} from '@solar-icons/react';

const HISTORY_KEY = 'ff_scraper_recent_history';

export default function ScraperPanel() {
  const [link, setLink] = useState('');
  const [scraping, setScraping] = useState(false);
  const [results, setResults] = useState<ScrapedItem[]>([]);
  const [error, setError] = useState('');
  const [selectedGids, setSelectedGids] = useState<Set<string>>(new Set());
  const [clipboardUrl, setClipboardUrl] = useState<string | null>(null);
  const [recentHistory, setRecentHistory] = useState<string[]>([]);
  const [filterText, setFilterText] = useState('');

  // Read saved recent history on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(HISTORY_KEY);
      if (saved) setRecentHistory(JSON.parse(saved));
    } catch (e) { console.error('Failed reading history:', e); }
  }, []);

  // Clipboard Auto-Detection
  const checkClipboard = async () => {
    try {
      let text = '';
      if (isTauri()) {
        text = await readText();
      } else if (typeof navigator !== 'undefined' && navigator.clipboard) {
        text = await navigator.clipboard.readText();
      }

      if (text && text.trim().startsWith('http') && (text.includes('fitgirl-repacks') || text.includes('fitgirl'))) {
        setClipboardUrl(text.trim());
      } else {
        setClipboardUrl(null);
      }
    } catch (err) {
      // Clipboard permission denied or unavailable silently ignored
    }
  };

  useEffect(() => {
    checkClipboard();
    window.addEventListener('focus', checkClipboard);
    return () => window.removeEventListener('focus', checkClipboard);
  }, []);

  const saveToHistory = (url: string) => {
    const updated = [url, ...recentHistory.filter(u => u !== url)].slice(0, 5);
    setRecentHistory(updated);
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(updated)); } catch (e) {}
  };

  const handleFind = async (targetUrl?: string) => {
    const urlToScrape = (targetUrl || link).trim();
    if (!urlToScrape) return;

    setError('');
    setScraping(true);
    setLink(urlToScrape);
    saveToHistory(urlToScrape);

    try {
      const items = await scraperFind(urlToScrape);
      setResults(items);
      
      // QOL: Automatically pre-select all valid links for 1-click batch download
      const validGids = new Set<string>();
      items.forEach(item => {
        if (item.success && item.link) {
          validGids.add(item.gid || item.link);
        }
      });
      setSelectedGids(validGids);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setResults([]);
    } finally {
      setScraping(false);
    }
  };

  const handlePasteClipboardAndScrape = () => {
    if (clipboardUrl) {
      handleFind(clipboardUrl);
      setClipboardUrl(null);
    }
  };

  const handlePasteInput = async () => {
    try {
      let text = '';
      if (isTauri()) text = await readText();
      else if (navigator.clipboard) text = await navigator.clipboard.readText();
      if (text) setLink(text.trim());
    } catch (e) {}
  };

  const handleDownload = async (item: ScrapedItem) => {
    setError('');
    try {
      await scraperAddTask(item);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleDownloadAllSelected = async () => {
    setError('');
    const toDownload = results.filter((item) => item.success && item.link && selectedGids.has(item.gid || item.link));
    if (toDownload.length === 0) return;
    try {
      for (const item of toDownload) await scraperAddTask(item);
      setSelectedGids(new Set());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const toggleSelectAll = () => {
    if (selectedGids.size === results.filter(i => i.success).length) {
      setSelectedGids(new Set());
    } else {
      const validGids = new Set<string>();
      results.forEach(i => { if (i.success && i.link) validGids.add(i.gid || i.link); });
      setSelectedGids(validGids);
    }
  };

  const getHostBadge = (url: string, name: string) => {
    const combined = `${url} ${name}`.toLowerCase();
    if (combined.includes('fuckingfast')) {
      return <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-400 font-bold border border-teal-500/30">⚡ FuckingFast</span>;
    }
    if (combined.includes('magnet:') || combined.includes('torrent')) {
      return <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 font-bold border border-purple-500/30">🧲 Magnet/Torrent</span>;
    }
    if (combined.includes('datanodes')) {
      return <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-bold border border-amber-500/30">📦 DataNodes</span>;
    }
    return <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]">🌐 Direct Mirror</span>;
  };

  const filteredResults = results.filter(item => item.name.toLowerCase().includes(filterText.toLowerCase()));

  return (
    <div className="flex flex-col h-full text-[var(--md-sys-color-on-surface)] select-none">
      {/* Title & Top Search Input */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)]">FitGirl Repacks Scraper</h3>
          {recentHistory.length > 0 && (
            <div className="flex items-center gap-1 overflow-x-auto max-w-md">
              <span className="text-[10px] font-bold text-[var(--md-sys-color-on-surface-variant)] uppercase mr-1 shrink-0">Recent:</span>
              {recentHistory.map((url, idx) => {
                const slug = url.replace(/\/$/, '').split('/').pop() || url;
                return (
                  <button
                    key={idx}
                    onClick={() => handleFind(url)}
                    className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-highest)] active-press cursor-pointer truncate max-w-[120px]"
                    title={url}
                  >
                    {slug}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Input Bar with Paste & Find Buttons */}
        <div className="flex gap-2">
          <div className="flex-1 relative flex items-center">
            <Global size={16} className="absolute left-3.5 text-[var(--md-sys-color-on-surface-variant)] pointer-events-none" />
            <input
              type="text"
              value={link}
              onChange={(e) => setLink(e.target.value)}
              placeholder="Paste FitGirl repack page URL..."
              disabled={scraping}
              onKeyDown={(e) => e.key === 'Enter' && handleFind()}
              className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-full pl-10 pr-24 py-2 text-xs text-[var(--md-sys-color-on-surface)] placeholder:text-[var(--md-sys-color-on-surface-variant)] focus:outline-none focus:border-[var(--md-sys-color-primary)] focus:ring-1 focus:ring-[var(--md-sys-color-primary)]/20 transition-all disabled:opacity-50"
            />
            {/* Quick Paste Button inside input */}
            <button
              type="button"
              onClick={handlePasteInput}
              title="Paste from Clipboard"
              className="absolute right-2.5 px-2 py-1 rounded-full text-[10px] font-semibold bg-[var(--md-sys-color-surface-container-lowest)] text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] border border-[var(--md-sys-color-outline-variant)] active-press flex items-center gap-1 cursor-pointer"
            >
              <ClipboardText size={12} />
              Paste
            </button>
          </div>

          <button
            onClick={() => handleFind()}
            disabled={scraping || !link.trim()}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-full text-xs font-semibold bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] hover:opacity-95 active-press disabled:opacity-40 transition-all cursor-pointer shadow-sm shrink-0"
          >
            <Magnifer size={16} />
            <span>Scrape</span>
          </button>
        </div>
      </div>

      {/* QOL: Clipboard Auto-Detect Banner */}
      {clipboardUrl && !scraping && link !== clipboardUrl && (
        <div className="p-3 bg-[var(--md-sys-color-secondary-container)] border border-[var(--md-sys-color-outline)] rounded-2xl mb-3 flex items-center justify-between animate-slide-up-emil shadow-sm">
          <div className="flex items-center gap-2.5 min-w-0 pr-3">
            <div className="w-7 h-7 rounded-full bg-[var(--md-sys-color-on-secondary-container)]/10 text-[var(--md-sys-color-on-secondary-container)] flex items-center justify-center shrink-0">
              <ClipboardText size={16} />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--md-sys-color-on-secondary-container)]">FitGirl Link Detected in Clipboard</span>
              <span className="text-xs font-mono text-[var(--md-sys-color-on-secondary-container)]/80 truncate">{clipboardUrl}</span>
            </div>
          </div>
          <button
            onClick={handlePasteClipboardAndScrape}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold bg-[var(--md-sys-color-on-secondary-container)] text-[var(--md-sys-color-secondary-container)] hover:opacity-90 active-press transition-all cursor-pointer shrink-0"
          >
            <span>Paste & Scrape</span>
            <DoubleAltArrowRight size={14} />
          </button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-[var(--md-sys-color-error-container)] text-[var(--md-sys-color-on-error-container)] text-xs font-medium rounded-xl mb-3 flex items-center gap-2 animate-scale-in-emil">
          <CloseCircle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      {/* Scraping Loading View */}
      {scraping && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-[var(--md-sys-color-on-surface-variant)]">
            <div className="w-8 h-8 border-3 border-[var(--md-sys-color-primary)] border-t-transparent rounded-full animate-spin" />
            <span className="text-xs font-semibold">Scraping repack download links...</span>
          </div>
        </div>
      )}

      {/* Results Section */}
      {!scraping && results.length > 0 && (
        <>
          {/* Controls & Filter Bar */}
          <div className="flex items-center justify-between mb-3 bg-[var(--md-sys-color-surface-container)] p-2 px-3.5 rounded-xl border border-[var(--md-sys-color-outline-variant)]">
            <div className="flex items-center gap-3">
              <button
                onClick={toggleSelectAll}
                className="text-xs font-semibold text-[var(--md-sys-color-primary)] hover:underline active-press cursor-pointer flex items-center gap-1"
              >
                <CheckCircle size={14} />
                {selectedGids.size === results.filter(i => i.success).length ? 'Deselect All' : 'Select All'}
              </button>
              <span className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] font-mono">
                {selectedGids.size} of {results.filter(i => i.success).length} selected
              </span>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                placeholder="Filter parts..."
                className="bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-lg px-2.5 py-1 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] w-32"
              />

              <button
                onClick={handleDownloadAllSelected}
                disabled={selectedGids.size === 0}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] hover:opacity-90 active-press disabled:opacity-40 transition-all cursor-pointer shadow-sm"
              >
                <Download size={14} />
                <span>Download Selected ({selectedGids.size})</span>
              </button>
            </div>
          </div>

          {/* Scraped Items List with Staggered Entrance */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredResults.map((item, idx) => {
              const itemId = item.gid || item.link;
              const isSelected = item.success && selectedGids.has(itemId);

              return (
                <div
                  key={idx}
                  className="animate-slide-up-emil"
                  style={{ animationDelay: `${Math.min(idx * 30, 200)}ms` }}
                >
                  <div
                    onClick={() => {
                      if (!item.success) return;
                      const newSet = new Set(selectedGids);
                      if (newSet.has(itemId)) newSet.delete(itemId);
                      else newSet.add(itemId);
                      setSelectedGids(newSet);
                    }}
                    className={`flex items-center gap-3 p-3 rounded-xl border transition-all hover-lift cursor-pointer ${
                      isSelected
                        ? 'bg-[var(--md-sys-color-secondary-container)] border-[var(--md-sys-color-outline)] shadow-sm'
                        : item.success
                          ? 'bg-[var(--md-sys-color-surface-container)] border-[var(--md-sys-color-outline-variant)] hover:bg-[var(--md-sys-color-surface-container-high)]'
                          : 'bg-[var(--md-sys-color-surface-container)] border-[var(--md-sys-color-outline-variant)] opacity-60 cursor-not-allowed'
                    }`}
                  >
                    <div className="w-8 h-8 rounded-lg bg-[var(--md-sys-color-surface-container-high)] flex items-center justify-center border border-[var(--md-sys-color-outline-variant)] shrink-0">
                      <SafeSquare size={18} className="text-[var(--md-sys-color-on-surface-variant)]" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-xs font-bold text-[var(--md-sys-color-on-surface)] truncate">{item.name}</p>
                        {item.link && getHostBadge(item.link, item.name)}
                      </div>
                      <p className={item.success ? 'text-xs text-[var(--md-sys-color-primary)] font-mono font-semibold' : 'text-xs text-[var(--md-sys-color-error)] font-mono truncate'}>
                        {item.success ? item.size : item.error || item.size}
                      </p>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {item.success && item.link && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDownload(item); }}
                          title="Download Task"
                          className="w-8 h-8 rounded-full flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-primary-container)] hover:text-[var(--md-sys-color-on-primary-container)] active-press transition-colors cursor-pointer"
                        >
                          <SIcon icon={DownloadMinimalistic} size={18} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Empty State */}
      {!scraping && results.length === 0 && !error && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center p-8 text-[var(--md-sys-color-on-surface-variant)] animate-scale-in-emil max-w-sm">
            <div className="w-14 h-14 rounded-2xl bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-primary)] flex items-center justify-center mb-3 mx-auto border border-[var(--md-sys-color-outline-variant)]">
              <ArchiveIcon size={30} />
            </div>
            <h3 className="text-sm font-bold mb-1 text-[var(--md-sys-color-on-surface)] tracking-wide">FitGirl Repacks Scraper</h3>
            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              Paste a FitGirl game repack page URL above, or copy a URL to your clipboard for instant auto-detection!
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
