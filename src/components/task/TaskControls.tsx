'use client';

import React from 'react';
import { useAppStore } from '@/stores/app-store';
import { pauseAll, unpauseAll } from '@/lib/tauri';
import { Pause, Play, AddSquare, AltArrowDown, AltArrowUp } from '@solar-icons/react';

interface TaskControlsProps {
  onOpenAddDialog: () => void;
}

export default function TaskControls({ onOpenAddDialog }: TaskControlsProps) {
  const { downloadSpeed, uploadSpeed } = useAppStore();

  const handlePauseAll = async () => {
    try { await pauseAll(); }
    catch (err) { console.error('Failed to pause all:', err); }
  };

  const handleResumeAll = async () => {
    try { await unpauseAll(); }
    catch (err) { console.error('Failed to resume all:', err); }
  };

  return (
    <div className="flex items-center justify-between bg-[var(--md-sys-color-surface-container)] p-3 px-4 rounded-[var(--md-sys-shape-corner-extra-large)] border border-[var(--md-sys-color-outline-variant)]">
      {/* Left controls: Add Task + Global Actions */}
      <div className="flex items-center gap-3">
        {/* Material 3 Expressive Filled Button with Tactile Active Press */}
        <button
          onClick={onOpenAddDialog}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] hover:opacity-95 active-press transition-all cursor-pointer shadow-sm"
        >
          <AddSquare size={18} />
          <span>Add Task</span>
        </button>

        <div className="w-px h-6 bg-[var(--md-sys-color-outline-variant)] mx-1" />

        {/* Material 3 Expressive Tonal Action Buttons */}
        <div className="flex items-center gap-1.5 bg-[var(--md-sys-color-surface-container-high)] p-1 rounded-full border border-[var(--md-sys-color-outline-variant)]">
          <button
            onClick={handlePauseAll}
            title="Pause All Downloads"
            className="w-9 h-9 rounded-full flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-highest)] active-press cursor-pointer"
          >
            <Pause size={18} />
          </button>
          <button
            onClick={handleResumeAll}
            title="Resume All Downloads"
            className="w-9 h-9 rounded-full flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-highest)] active-press cursor-pointer"
          >
            <Play size={18} />
          </button>
        </div>
      </div>

      {/* Right side: Material 3 Tonal Telemetry Container */}
      <div className="flex items-center gap-3 bg-[var(--md-sys-color-surface-container-high)] px-4 py-2 rounded-[var(--md-sys-shape-corner-medium)] border border-[var(--md-sys-color-outline-variant)]">
        {/* Down Speed */}
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] flex items-center justify-center">
            <AltArrowDown size={15} />
          </div>
          <div className="flex flex-col text-right">
            <span className="text-[9px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider">Down</span>
            <span className="text-xs font-mono font-semibold text-[var(--md-sys-color-primary)]">{downloadSpeed || '0 KB/s'}</span>
          </div>
        </div>

        <div className="w-px h-5 bg-[var(--md-sys-color-outline-variant)]" />

        {/* Up Speed */}
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] flex items-center justify-center">
            <AltArrowUp size={15} />
          </div>
          <div className="flex flex-col text-right">
            <span className="text-[9px] font-semibold text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider">Up</span>
            <span className="text-xs font-mono font-semibold text-[var(--md-sys-color-secondary)]">{uploadSpeed || '0 KB/s'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
