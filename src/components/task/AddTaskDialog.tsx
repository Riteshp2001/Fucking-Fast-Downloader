'use client';

import React, { useState } from 'react';
import { addUri } from '@/lib/tauri';
import {
  CloseCircle, AltArrowDown, AltArrowRight, AddSquare,
  TrashBinMinimalistic, ClipboardText, CheckCircle
} from '@solar-icons/react';

interface AddTaskDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ParsedUrl {
  url: string;
  isValid: boolean;
  host: string;
}

function parseUrlHost(url: string): { isValid: boolean; host: string } {
  if (url.toLowerCase().startsWith('magnet:?')) {
    return { isValid: true, host: 'magnet' };
  }

  try {
    const parsed = new URL(url);
    return { isValid: true, host: parsed.hostname };
  } catch {
    return { isValid: false, host: '' };
  }
}

function getHostBadge(host: string) {
  const h = host.toLowerCase();
  if (h === 'magnet') {
    return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-purple-500/15 text-purple-400 font-bold border border-purple-500/30 shrink-0">Magnet</span>;
  }
  if (h.includes('magnet') || h.includes('torrent')) {
    return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-purple-500/15 text-purple-400 font-bold border border-purple-500/30 shrink-0">🧲 Magnet</span>;
  }
  if (h.includes('datanodes')) {
    return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-bold border border-amber-500/30 shrink-0">📦 DataNodes</span>;
  }
  return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-neutral-500/15 text-neutral-400 font-bold border border-neutral-500/30 shrink-0">🌐 {host.length > 20 ? host.slice(0, 20) + '…' : host}</span>;
}

function parseUrlsFromText(text: string): ParsedUrl[] {
  // Split by newlines, then filter out empty/comment lines
  const lines = text
    .split(/[\n\r]+/)
    .map(l => l.trim())
    .filter(l => l.length > 0 && !l.startsWith('#'));

  return lines.map(line => {
    const { isValid, host } = parseUrlHost(line);
    return { url: line, isValid, host };
  });
}

export default function AddTaskDialog({ isOpen, onClose }: AddTaskDialogProps) {
  const [urlsText, setUrlsText] = useState('');
  const [outName, setOutName] = useState('');
  const [connections, setConnections] = useState(16);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const parsedUrls = parseUrlsFromText(urlsText);
  const validCount = parsedUrls.filter(p => p.isValid).length;
  const invalidCount = parsedUrls.filter(p => !p.isValid).length;

  const handleRemoveUrl = (index: number) => {
    const lines = urlsText.split(/[\n\r]+/).map(l => l.trim()).filter(l => l.length > 0 && !l.startsWith('#'));
    lines.splice(index, 1);
    setUrlsText(lines.join('\n'));
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        // Smart merge: if there's already text, append on new lines
        setUrlsText(prev => {
          const trimmed = prev.trim();
          if (trimmed) return trimmed + '\n' + text.trim();
          return text.trim();
        });
      }
    } catch {
      // Clipboard unavailable in Tauri — handled by platform paste
    }
  };

  const handleAdd = async () => {
    const urls = parsedUrls.filter(p => p.isValid).map(p => p.url);
    if (urls.length === 0) { setErrorMsg('Please enter at least one valid download URL.'); return; }

    setIsSubmitting(true);
    setErrorMsg('');

    try {
      for (const url of urls) {
        const options: Record<string, unknown> = {};
        if (outName.trim()) options['out'] = outName.trim();
        if (connections) options['max-connection-per-server'] = String(connections);
        await addUri(url, options);
      }
      setUrlsText('');
      setOutName('');
      onClose();
    } catch (err: unknown) {
      console.error('Failed to add tasks:', err);
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Glass Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-950/70 backdrop-blur-md transition-opacity animate-[fade-in_150ms_ease-out]"
        onClick={onClose}
      />

      {/* Dialog Card */}
      <div className="bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-3xl w-full max-w-lg shadow-2xl relative z-10 overflow-hidden flex flex-col max-h-[85vh] animate-[scale-in_200ms_ease-out]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[var(--md-sys-color-outline-variant)]/60 flex items-center justify-between bg-[var(--md-sys-color-surface-container-high)]/40">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center border border-teal-500/20">
              <AddSquare size={18} />
            </div>
            <h2 className="text-sm font-bold text-[var(--md-sys-color-on-surface)] tracking-wide">Add New Download</h2>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-highest)] transition-colors cursor-pointer"
          >
            <CloseCircle size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {errorMsg && (
            <div className="p-3 bg-red-500/15 border border-red-500/30 text-red-400 text-xs rounded-xl flex items-center gap-2 font-medium">
              <CloseCircle size={16} className="shrink-0" />
              {errorMsg}
            </div>
          )}

          {/* URL Input Area */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-[var(--md-sys-color-on-surface)]">
                Download URLs <span className="text-[var(--md-sys-color-on-surface-variant)] font-normal">(one URL per line)</span>
              </label>
              <button
                type="button"
                onClick={handlePaste}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold text-teal-400 hover:text-teal-300 hover:bg-teal-500/10 transition-colors cursor-pointer"
              >
                <ClipboardText size={11} />
                Paste
              </button>
            </div>
            <textarea
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-xl p-3 text-xs font-mono text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all resize-none min-h-[90px] placeholder:text-[var(--md-sys-color-on-surface-variant)]/60"
              placeholder={"https://example.com/file.zip\nmagnet:?xt=urn:btih:...\nhttps://example.com/file.torrent"}
            />
          </div>

          {/* Parsed URL List */}
          {parsedUrls.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)]">
                    Parsed URLs
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-teal-500/15 text-teal-400 border border-teal-500/30">
                    {validCount} valid
                  </span>
                  {invalidCount > 0 && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
                      {invalidCount} invalid
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-1.5 max-h-[180px] overflow-y-auto pr-1">
                {parsedUrls.map((item, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs transition-all ${
                      item.isValid
                        ? 'bg-[var(--md-sys-color-surface-container)] border-[var(--md-sys-color-outline-variant)] hover:bg-[var(--md-sys-color-surface-container-high)]'
                        : 'bg-red-500/5 border-red-500/20'
                    }`}
                  >
                    {/* Status Icon */}
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                      item.isValid ? 'text-teal-400' : 'text-red-400'
                    }`}>
                      {item.isValid ? <CheckCircle size={14} /> : <CloseCircle size={14} />}
                    </div>

                    {/* URL text */}
                    <span
                      className={`flex-1 font-mono truncate min-w-0 ${
                        item.isValid ? 'text-[var(--md-sys-color-on-surface)]' : 'text-red-400'
                      }`}
                      title={item.url}
                    >
                      {item.url}
                    </span>

                    {/* Host Badge */}
                    {item.isValid && getHostBadge(item.host)}

                    {/* Remove button */}
                    <button
                      onClick={() => handleRemoveUrl(idx)}
                      className="w-5 h-5 rounded-full flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer shrink-0"
                      title="Remove URL"
                    >
                      <TrashBinMinimalistic size={12} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1.5 text-xs text-teal-400 hover:text-teal-300 transition-colors font-bold cursor-pointer"
          >
            {showAdvanced ? <AltArrowDown size={14} /> : <AltArrowRight size={14} />}
            Advanced Options
          </button>

          {showAdvanced && (
            <div className="space-y-3 pt-3 border-t border-[var(--md-sys-color-outline-variant)]/60 animate-[slide-up_150ms_ease-out]">
              <div>
                <label className="block text-xs font-semibold text-[var(--md-sys-color-on-surface-variant)] mb-1">Custom Filename (optional)</label>
                <input
                  type="text"
                  value={outName}
                  onChange={(e) => setOutName(e.target.value)}
                  placeholder="game_installer.part1.rar"
                  className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-xl px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[var(--md-sys-color-on-surface-variant)] mb-1">Max Connections Per Server</label>
                <input
                  type="number"
                  value={connections}
                  onChange={(e) => setConnections(parseInt(e.target.value, 10) || 16)}
                  min={1} max={32}
                  className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-xl px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--md-sys-color-outline-variant)]/60 flex items-center justify-between bg-[var(--md-sys-color-surface-container-high)]/40">
          <span className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] font-mono">
            {parsedUrls.length > 0
              ? `${validCount} URL${validCount !== 1 ? 's' : ''} ready`
              : 'No URLs entered'}
          </span>
          <div className="flex gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold rounded-xl border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] hover:text-[var(--md-sys-color-on-surface)] transition-all cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={isSubmitting || validCount === 0}
              className="px-4 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-teal-400 to-emerald-400 hover:from-teal-300 hover:to-emerald-300 text-neutral-950 shadow-md shadow-teal-500/20 disabled:opacity-50 transition-all cursor-pointer"
            >
              {isSubmitting ? 'Adding...' : `Start Download${validCount > 1 ? ` (${validCount})` : ''}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
