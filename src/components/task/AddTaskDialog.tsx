'use client';

import React, { useState } from 'react';
import { addUri } from '@/lib/tauri';
import { CloseCircle, AltArrowDown, AltArrowRight, AddSquare } from '@solar-icons/react';

interface AddTaskDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AddTaskDialog({ isOpen, onClose }: AddTaskDialogProps) {
  const [urlsText, setUrlsText] = useState('');
  const [outName, setOutName] = useState('');
  const [connections, setConnections] = useState(16);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const handleAdd = async () => {
    const urls = urlsText.split('\n').map((u) => u.trim()).filter((u) => u.length > 0 && !u.startsWith('#'));
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

          <div>
            <label className="block text-xs font-semibold text-[var(--md-sys-color-on-surface)] mb-1.5">
              Download URLs <span className="text-[var(--md-sys-color-on-surface-variant)] font-normal">(one URL per line)</span>
            </label>
            <textarea
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)]/60 rounded-xl p-3 text-xs font-mono text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500/30 transition-all resize-none min-h-[110px] placeholder:text-[var(--md-sys-color-on-surface-variant)]/60"
              placeholder="https://fuckingfast.co/download/..."
            />
          </div>

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
        <div className="px-6 py-4 border-t border-[var(--md-sys-color-outline-variant)]/60 flex justify-end gap-2.5 bg-[var(--md-sys-color-surface-container-high)]/40">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold rounded-xl border border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] hover:text-[var(--md-sys-color-on-surface)] transition-all cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleAdd}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-teal-400 to-emerald-400 hover:from-teal-300 hover:to-emerald-300 text-neutral-950 shadow-md shadow-teal-500/20 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isSubmitting ? 'Adding...' : 'Start Download'}
          </button>
        </div>
      </div>
    </div>
  );
}
