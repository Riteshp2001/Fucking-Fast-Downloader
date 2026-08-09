'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  addTorrent,
  addUri,
  readClipboardText,
  resolveFuckingFastLink,
} from '@/lib/tauri';
import { formatError } from '@/lib/errors';
import {
  CloseCircle,
  AltArrowDown,
  AltArrowRight,
  AddSquare,
  TrashBinMinimalistic,
  ClipboardText,
  CheckCircle,
} from '@solar-icons/react';

interface AddTaskDialogProps {
  isOpen: boolean;
  onClose: () => void;
  initialUrls?: string[];
}

interface ParsedUrl {
  url: string;
  isValid: boolean;
  host: string;
}

interface AddFailure {
  url: string;
  message: string;
}

const MAX_TORRENT_FILE_SIZE = 32 * 1024 * 1024;
const TORRENT_PRIORITY = 'head=64M,tail=32M';

function isMagnetUrl(url: string): boolean {
  return url.trim().toLowerCase().startsWith('magnet:?');
}

function normalizeDownloadUrl(url: string): string {
  const trimmed = url.trim();
  if (!isMagnetUrl(trimmed)) {
    return trimmed;
  }

  return trimmed.replace(/\s+/g, '').replace(/&amp;/gi, '&').replace(/&#038;/gi, '&');
}

function parseUrlHost(url: string): { isValid: boolean; host: string } {
  const normalized = normalizeDownloadUrl(url);

  if (isMagnetUrl(normalized)) {
    return {
      isValid: /[?&]xt=urn:btih:/i.test(normalized),
      host: 'magnet',
    };
  }

  try {
    const parsed = new URL(normalized);
    const isSupported = parsed.protocol === 'http:' || parsed.protocol === 'https:' || parsed.protocol === 'ftp:';
    return { isValid: isSupported, host: isSupported ? parsed.hostname : '' };
  } catch {
    return { isValid: false, host: '' };
  }
}

function getHostBadge(host: string) {
  const h = host.toLowerCase();
  if (h === 'magnet') {
    return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-purple-500/15 text-purple-400 font-bold border border-purple-500/30 shrink-0">Magnet</span>;
  }
  if (h.includes('datanodes')) {
    return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-bold border border-amber-500/30 shrink-0">DataNodes</span>;
  }
  return <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-neutral-500/15 text-neutral-400 font-bold border border-neutral-500/30 shrink-0">{host.length > 20 ? host.slice(0, 20) + '…' : host}</span>;
}

function normalizeInputLines(text: string): string[] {
  const rawLines = text
    .split(/[\n\r]+/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('#'));

  const lines: string[] = [];
  for (const line of rawLines) {
    const startsNewUrl = /^[a-z][a-z0-9+.-]*:/i.test(line);
    const previous = lines[lines.length - 1];

    if (!startsNewUrl && previous && isMagnetUrl(previous)) {
      lines[lines.length - 1] = `${previous}${line}`;
      continue;
    }

    lines.push(line);
  }

  return lines.map(normalizeDownloadUrl);
}

function parseUrlsFromText(text: string): ParsedUrl[] {
  return normalizeInputLines(text).map((line) => {
    const { isValid, host } = parseUrlHost(line);
    return { url: line, isValid, host };
  });
}

function isFuckingFastShareUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    return (host === 'fuckingfast.co' || host.endsWith('.fuckingfast.co')) && !host.startsWith('dl.');
  } catch {
    return false;
  }
}

function getFuckingFastFilename(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (!parsed.hash || parsed.hash.length <= 1) return null;
    const raw = parsed.hash.slice(1);
    try {
      return decodeURIComponent(raw) || null;
    } catch {
      return raw || null;
    }
  } catch {
    return null;
  }
}

function isRemoteTorrentUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:')
      && parsed.pathname.toLowerCase().endsWith('.torrent');
  } catch {
    return false;
  }
}

function bytesToBase64(bytes: Uint8Array): string {
  const chunkSize = 0x8000;
  let binary = '';

  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    const chunk = bytes.subarray(offset, Math.min(offset + chunkSize, bytes.length));
    binary += String.fromCharCode(...chunk);
  }

  return btoa(binary);
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  return bytesToBase64(new Uint8Array(buffer));
}

function torrentUriOptions(): Record<string, unknown> {
  return {
    'file-allocation': 'none',
    'bt-prioritize-piece': TORRENT_PRIORITY,
    'bt-remove-unselected-file': 'false',
    'bt-save-metadata': 'true',
  };
}

export default function AddTaskDialog({ isOpen, onClose, initialUrls = [] }: AddTaskDialogProps) {
  const torrentInputRef = useRef<HTMLInputElement>(null);
  const [urlsText, setUrlsText] = useState('');
  const [outName, setOutName] = useState('');
  const [connections, setConnections] = useState<number | ''>('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!isOpen) return;

    Promise.resolve().then(() => {
      setUrlsText(initialUrls.join('\n'));
      setErrorMsg('');
    });
  }, [isOpen, initialUrls]);

  if (!isOpen) return null;

  const parsedUrls = parseUrlsFromText(urlsText);
  const validUrls = parsedUrls.filter((item) => item.isValid);
  const validCount = validUrls.length;
  const invalidCount = parsedUrls.length - validCount;
  const canUseCustomFilename = validCount <= 1;

  const handleRemoveUrl = (index: number) => {
    const lines = normalizeInputLines(urlsText);
    lines.splice(index, 1);
    setUrlsText(lines.join('\n'));
  };

  const handlePaste = async () => {
    try {
      const text = await readClipboardText();
      if (!text.trim()) return;

      setUrlsText((previous) => {
        const trimmed = previous.trim();
        return trimmed ? `${trimmed}\n${text.trim()}` : text.trim();
      });
      setErrorMsg('');
    } catch (error) {
      setErrorMsg(`Could not read the clipboard: ${formatError(error)}`);
    }
  };

  const handleTorrentFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.torrent')) {
      setErrorMsg('Please select a .torrent file.');
      return;
    }
    if (file.size > MAX_TORRENT_FILE_SIZE) {
      setErrorMsg('The selected .torrent file is unusually large and was not imported.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');
    try {
      const torrentBase64 = arrayBufferToBase64(await file.arrayBuffer());
      await addTorrent(torrentBase64);
      setUrlsText('');
      setOutName('');
      onClose();
    } catch (error) {
      console.error('Failed to import torrent:', error);
      setErrorMsg(`Could not import ${file.name}: ${formatError(error)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAdd = async () => {
    if (validUrls.length === 0) {
      setErrorMsg('Please enter at least one valid HTTP(S), FTP, or magnet URL.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');

    const failures: AddFailure[] = parsedUrls
      .filter((item) => !item.isValid)
      .map((item) => ({ url: item.url, message: 'Unsupported or invalid URL' }));
    let addedCount = 0;

    for (const item of validUrls) {
      try {
        const fromFuckingFast = isFuckingFastShareUrl(item.url);
        const downloadUrl = fromFuckingFast
          ? await resolveFuckingFastLink(item.url)
          : item.url;

        // Let aria2 fetch remote torrent metainfo itself and follow it in memory.
        // This avoids treating the .torrent file as the final payload and also
        // avoids an unnecessary frontend/backend metadata download round-trip.
        if (isRemoteTorrentUrl(downloadUrl)) {
          await addUri(downloadUrl, {
            ...torrentUriOptions(),
            'follow-torrent': 'mem',
          });
          addedCount += 1;
          continue;
        }

        const options: Record<string, unknown> = isMagnetUrl(downloadUrl)
          ? torrentUriOptions()
          : {};

        if (!isMagnetUrl(downloadUrl)) {
          if (canUseCustomFilename && outName.trim()) {
            options.out = outName.trim();
          } else if (fromFuckingFast) {
            const filename = getFuckingFastFilename(item.url);
            if (filename) options.out = filename;
          }
          if (connections !== '') options['max-connection-per-server'] = String(connections);
        }

        await addUri(downloadUrl, options);
        addedCount += 1;
      } catch (error) {
        console.error('Failed to add download:', item.url, error);
        failures.push({ url: item.url, message: formatError(error) });
      }
    }

    setIsSubmitting(false);

    if (failures.length === 0) {
      setUrlsText('');
      setOutName('');
      onClose();
      return;
    }

    setUrlsText(failures.map((failure) => failure.url).join('\n'));
    const firstFailure = failures[0];
    const summary = addedCount > 0
      ? `Added ${addedCount} download${addedCount === 1 ? '' : 's'}. ${failures.length} item${failures.length === 1 ? '' : 's'} still need attention.`
      : `No downloads were added. ${failures.length} item${failures.length === 1 ? '' : 's'} failed.`;
    setErrorMsg(`${summary} ${firstFailure.message}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-neutral-950/70 backdrop-blur-md transition-opacity animate-[fade-in_150ms_ease-out]"
        onClick={onClose}
      />

      <div className="bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-3xl w-full max-w-lg shadow-2xl relative z-10 overflow-hidden flex flex-col max-h-[85vh] animate-[scale-in_200ms_ease-out]">
        <div className="px-6 py-4 border-b border-[var(--md-sys-color-outline-variant)]/60 flex items-center justify-between bg-[var(--md-sys-color-surface-container-high)]/40">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center border border-teal-500/20">
              <AddSquare size={18} />
            </div>
            <h2 className="text-sm font-bold text-[var(--md-sys-color-on-surface)] tracking-wide">Add New Download</h2>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-highest)] transition-colors cursor-pointer disabled:opacity-50"
          >
            <CloseCircle size={18} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {errorMsg && (
            <div className="p-3 bg-red-500/15 border border-red-500/30 text-red-400 text-xs rounded-xl flex items-start gap-2 font-medium">
              <CloseCircle size={16} className="shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1.5 gap-2">
              <label className="text-xs font-semibold text-[var(--md-sys-color-on-surface)]">
                Download URLs <span className="text-[var(--md-sys-color-on-surface-variant)] font-normal">(one URL per line)</span>
              </label>
              <div className="flex items-center gap-1">
                <input
                  ref={torrentInputRef}
                  type="file"
                  accept=".torrent,application/x-bittorrent"
                  className="hidden"
                  onChange={handleTorrentFile}
                />
                <button
                  type="button"
                  onClick={() => torrentInputRef.current?.click()}
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold text-[var(--md-sys-color-on-surface-variant)] hover:text-teal-300 hover:bg-teal-500/10 transition-colors cursor-pointer disabled:opacity-50"
                >
                  <AddSquare size={11} />
                  .torrent
                </button>
                <button
                  type="button"
                  onClick={handlePaste}
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold text-teal-400 hover:text-teal-300 hover:bg-teal-500/10 transition-colors cursor-pointer disabled:opacity-50"
                >
                  <ClipboardText size={11} />
                  Paste
                </button>
              </div>
            </div>
            <textarea
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              disabled={isSubmitting}
              className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-xl p-3 text-xs font-mono text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all resize-none min-h-[90px] placeholder:text-[var(--md-sys-color-on-surface-variant)]/60 disabled:opacity-60"
              placeholder={"https://example.com/file.zip\nhttps://example.com/file.torrent\nmagnet:?xt=urn:btih:..."}
            />
          </div>

          {parsedUrls.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)]">Parsed URLs</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-teal-500/15 text-teal-400 border border-teal-500/30">{validCount} valid</span>
                  {invalidCount > 0 && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">{invalidCount} invalid</span>
                  )}
                </div>
              </div>

              <div className="space-y-1.5 max-h-[180px] overflow-y-auto pr-1">
                {parsedUrls.map((item, idx) => (
                  <div
                    key={`${item.url}-${idx}`}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs transition-all ${
                      item.isValid
                        ? 'bg-[var(--md-sys-color-surface-container)] border-[var(--md-sys-color-outline-variant)] hover:bg-[var(--md-sys-color-surface-container-high)]'
                        : 'bg-red-500/5 border-red-500/20'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${item.isValid ? 'text-teal-400' : 'text-red-400'}`}>
                      {item.isValid ? <CheckCircle size={14} /> : <CloseCircle size={14} />}
                    </div>
                    <span
                      className={`flex-1 font-mono truncate min-w-0 ${item.isValid ? 'text-[var(--md-sys-color-on-surface)]' : 'text-red-400'}`}
                      title={item.url}
                    >
                      {item.url}
                    </span>
                    {item.isValid && getHostBadge(item.host)}
                    <button
                      onClick={() => handleRemoveUrl(idx)}
                      disabled={isSubmitting}
                      className="w-5 h-5 rounded-full flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer shrink-0 disabled:opacity-50"
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
                  disabled={!canUseCustomFilename || isSubmitting}
                  placeholder={canUseCustomFilename ? 'download.bin' : 'Available for a single URL only'}
                  className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-xl px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all disabled:opacity-50"
                />
                {!canUseCustomFilename && (
                  <p className="text-[10px] mt-1 text-[var(--md-sys-color-on-surface-variant)]">A shared custom filename is disabled for batch downloads to prevent file collisions.</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold text-[var(--md-sys-color-on-surface-variant)] mb-1">Max Connections Per Server</label>
                <input
                  type="number"
                  value={connections}
                  onChange={(e) => {
                    if (!e.target.value) {
                      setConnections('');
                      return;
                    }
                    setConnections(Math.min(32, Math.max(1, parseInt(e.target.value, 10) || 1)));
                  }}
                  min={1}
                  max={32}
                  placeholder="Use global setting"
                  disabled={isSubmitting}
                  className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-xl px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all disabled:opacity-50"
                />
                <p className="text-[10px] mt-1 text-[var(--md-sys-color-on-surface-variant)]">Leave blank to use the global engine preference.</p>
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-[var(--md-sys-color-outline-variant)]/60 flex items-center justify-between bg-[var(--md-sys-color-surface-container-high)]/40">
          <span className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] font-mono">
            {parsedUrls.length > 0 ? `${validCount} URL${validCount !== 1 ? 's' : ''} ready` : 'No URLs entered'}
          </span>
          <div className="flex gap-2.5">
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold rounded-xl border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] hover:text-[var(--md-sys-color-on-surface)] transition-all cursor-pointer disabled:opacity-50"
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
