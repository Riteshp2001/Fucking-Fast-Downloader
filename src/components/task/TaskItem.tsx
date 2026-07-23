'use client';

import React from 'react';
import type { Aria2Task } from '@/types';
import { bytesToSize, formatSpeed, formatEta, formatProgress } from '@/lib/utils';
import { SIcon } from '@/components/ui/SIcon';
import { FileText, ArchiveDownMinimalistic, Clapperboard, Pause, Play, TrashBinTrash, Widget } from '@solar-icons/react';

interface TaskItemProps {
  task: Aria2Task;
  isSelected: boolean;
  onClick: () => void;
  onPause: (e: React.MouseEvent) => void;
  onResume: (e: React.MouseEvent) => void;
  onRemove: (e: React.MouseEvent) => void;
}

function FileTypeIcon({ extension }: { extension: string }) {
  const iconProps = { size: 20, className: 'text-[var(--md-sys-color-on-surface-variant)]' };
  let icon = <FileText {...iconProps} />;
  if (['iso', 'zip', 'rar', 'gz', '7z', 'tar'].includes(extension)) icon = <ArchiveDownMinimalistic {...iconProps} />;
  if (['mp4', 'mkv', 'avi', 'mov'].includes(extension)) icon = <Clapperboard {...iconProps} />;
  if (['exe', 'msi', 'apk'].includes(extension)) icon = <Widget {...iconProps} />;

  return (
    <div className="w-10 h-10 rounded-[var(--md-sys-shape-corner-medium)] bg-[var(--md-sys-color-surface-container-high)] flex items-center justify-center border border-[var(--md-sys-color-outline-variant)] shrink-0 transition-transform duration-200 group-hover:scale-105">
      {icon}
    </div>
  );
}

function getProgressColor(status: string) {
  switch (status) {
    case 'complete': return 'bg-[var(--md-sys-color-primary)]';
    case 'error': return 'bg-[var(--md-sys-color-error)]';
    case 'paused':
    case 'waiting': return 'bg-[var(--md-sys-color-tertiary)]';
    default: return 'bg-[var(--md-sys-color-primary)]';
  }
}

function getBadgeColor(status: string) {
  switch (status) {
    case 'complete': return 'bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)]';
    case 'error': return 'bg-[var(--md-sys-color-error-container)] text-[var(--md-sys-color-on-error-container)]';
    case 'paused':
    case 'waiting': return 'bg-[var(--md-sys-color-tertiary-container)] text-[var(--md-sys-color-on-tertiary-container)]';
    default: return 'bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)]';
  }
}

export default function TaskItem({ task, isSelected, onClick, onPause, onResume, onRemove }: TaskItemProps) {
  const isActive = task.status === 'active';

  const total = parseInt(task.totalLength, 10) || 0;
  const completed = parseInt(task.completedLength, 10) || 0;
  const speed = parseInt(task.downloadSpeed, 10) || 0;

  const progress = formatProgress(completed, total);
  const sizeFormatted = total > 0 ? `${bytesToSize(completed)} / ${bytesToSize(total)}` : bytesToSize(completed);
  const speedFormatted = formatSpeed(speed);
  const etaFormatted = formatEta(total, completed, speed);

  const name = task.bittorrent?.info?.name || task.title ||
    (task.files && task.files[0]?.path ? task.files[0].path.split(/[/\\]/).pop() : null) || 'Unnamed Download';

  const ext = name.split('.').pop()?.toLowerCase() || '';

  return (
    <div
      onClick={onClick}
      className={`group relative p-4 rounded-[var(--md-sys-shape-corner-medium)] border cursor-pointer hover-lift select-none ${
        isSelected
          ? 'bg-[var(--md-sys-color-secondary-container)] border-[var(--md-sys-color-outline)] shadow-sm'
          : 'bg-[var(--md-sys-color-surface-container)] border-[var(--md-sys-color-outline-variant)] hover:bg-[var(--md-sys-color-surface-container-high)]'
      }`}
    >
      <div className="flex items-center gap-3.5">
        <FileTypeIcon extension={ext} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-medium text-[var(--md-sys-color-on-surface)] truncate pr-4" title={name}>
              {name}
            </h4>
            <div className="flex items-center gap-2.5 shrink-0">
              {isActive && <span className="text-xs font-mono text-[var(--md-sys-color-primary)] font-bold">{speedFormatted}</span>}
              {isActive && <span className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] font-mono">{etaFormatted}</span>}
              <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-[var(--md-sys-shape-corner-extra-small)] ${getBadgeColor(task.status)} tracking-wider transition-colors duration-150`}>
                {task.status}
              </span>
            </div>
          </div>

          {/* Progress Bar & Percentage */}
          <div className="flex items-center gap-3 mb-1.5">
            <div className="flex-1 h-1.5 bg-[var(--md-sys-color-surface-container-highest)] rounded-full overflow-hidden">
              <div
                className={`h-full ${getProgressColor(task.status)} transition-all duration-300 [transition-timing-function:var(--ease-emil-out)] rounded-full`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs font-mono font-medium text-[var(--md-sys-color-on-surface)] w-10 text-right">{progress}%</span>
          </div>

          <div className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] font-mono flex items-center justify-between">
            <span>{sizeFormatted}</span>
            {task.connections && parseInt(task.connections, 10) > 0 && (
              <span className="text-[var(--md-sys-color-outline)]">Conns: {task.connections}</span>
            )}
          </div>
        </div>
      </div>

      {/* Floating Hover Action Toolbar with Emil Kowalski Spring Transitions */}
      <div className={`absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 p-1 bg-[var(--md-sys-color-surface-container-high)] rounded-[var(--md-sys-shape-corner-small)] border border-[var(--md-sys-color-outline-variant)] transition-all duration-200 [transition-timing-function:var(--ease-emil-out)] ${
        isSelected ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-3 group-hover:opacity-100 group-hover:translate-x-0'
      }`}>
        {isActive ? (
          <button
            onClick={onPause}
            className="w-7 h-7 rounded-[var(--md-sys-shape-corner-small)] flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)] hover:text-[var(--md-sys-color-on-surface)] active-press cursor-pointer"
            title="Pause"
          >
            <SIcon icon={Pause} size={16} />
          </button>
        ) : (
          <button
            onClick={onResume}
            className="w-7 h-7 rounded-[var(--md-sys-shape-corner-small)] flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)] hover:text-[var(--md-sys-color-on-surface)] active-press cursor-pointer"
            title="Resume"
          >
            <SIcon icon={Play} size={16} />
          </button>
        )}
        <button
          onClick={onRemove}
          className="w-7 h-7 rounded-[var(--md-sys-shape-corner-small)] flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-error-container)] hover:text-[var(--md-sys-color-on-error-container)] active-press cursor-pointer"
          title="Remove"
        >
          <SIcon icon={TrashBinTrash} size={16} />
        </button>
      </div>
    </div>
  );
}
