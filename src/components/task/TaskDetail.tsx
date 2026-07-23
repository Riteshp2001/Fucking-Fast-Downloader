'use client';

import React from 'react';
import type { Aria2Task } from '@/types';
import { bytesToSize, formatSpeed, formatEta, formatProgress } from '@/lib/utils';
import { pauseTask, unpauseTask, removeTask } from '@/lib/tauri';
import { CloseCircle, Pause, Play, TrashBinTrash, FileText } from '@solar-icons/react';

interface TaskDetailProps {
  task: Aria2Task;
  onClose: () => void;
}

export default function TaskDetail({ task, onClose }: TaskDetailProps) {
  const name = task.bittorrent?.info?.name || task.title ||
    (task.files && task.files[0]?.path ? task.files[0].path.split(/[/\\]/).pop() : null) || 'Unnamed Task';

  const dir = task.dir || (task.files && task.files[0]?.path ? task.files[0].path : 'N/A');

  const total = parseInt(task.totalLength, 10) || 0;
  const completed = parseInt(task.completedLength, 10) || 0;
  const speed = parseInt(task.downloadSpeed, 10) || 0;

  const progress = formatProgress(completed, total);
  const sizeFormatted = total > 0 ? `${bytesToSize(completed)} / ${bytesToSize(total)}` : bytesToSize(completed);
  const speedFormatted = formatSpeed(speed);
  const etaFormatted = formatEta(total, completed, speed);

  const isActive = task.status === 'active';

  const handlePauseResume = async () => {
    try {
      if (isActive) await pauseTask(task.gid);
      else await unpauseTask(task.gid);
    } catch (err) { console.error('Failed toggle pause/resume:', err); }
  };

  const handleRemove = async () => {
    try {
      await removeTask(task.gid);
      onClose();
    } catch (err) { console.error('Failed to remove task:', err); }
  };

  const infoCard = (label: string, value: string, color = 'text-[var(--md-sys-color-on-surface)]') => (
    <div className="bg-[var(--md-sys-color-surface-container-high)]/60 p-3 rounded-xl border border-[var(--md-sys-color-outline-variant)]/50">
      <span className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold mb-0.5 block">{label}</span>
      <span className={`text-xs font-mono font-bold ${color}`}>{value}</span>
    </div>
  );

  return (
    <div className="flex flex-col h-full text-[var(--md-sys-color-on-surface)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--md-sys-color-outline-variant)]/60">
        <h3 className="text-xs font-bold uppercase tracking-wider text-teal-400">Task Details</h3>
        <button
          onClick={onClose}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)] hover:text-[var(--md-sys-color-on-surface)] transition-colors cursor-pointer"
        >
          <CloseCircle size={16} />
        </button>
      </div>

      {/* Details Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-3.5 pr-1">
        <div>
          <label className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold mb-1 block">Filename</label>
          <p className="text-xs break-all bg-[var(--md-sys-color-surface-container-high)]/60 p-3 rounded-xl border border-[var(--md-sys-color-outline-variant)]/50 font-bold leading-relaxed">{name}</p>
        </div>

        <div>
          <label className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold mb-1 block">Save Location</label>
          <p className="text-[11px] break-all bg-[var(--md-sys-color-surface-container-high)]/60 p-3 rounded-xl border border-[var(--md-sys-color-outline-variant)]/50 font-mono leading-relaxed text-[var(--md-sys-color-on-surface-variant)]">{dir}</p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {infoCard('Progress', `${progress}%`, 'text-teal-400')}
          {infoCard('Status', task.status, 'text-teal-400 capitalize')}
          {infoCard('Speed', speedFormatted)}
          {infoCard('ETA', etaFormatted)}
        </div>

        <div>
          <label className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold mb-1 block">Total Size</label>
          <p className="text-xs font-mono text-[var(--md-sys-color-on-surface-variant)] bg-[var(--md-sys-color-surface-container-high)]/60 p-3 rounded-xl border border-[var(--md-sys-color-outline-variant)]/50 font-semibold">{sizeFormatted}</p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {infoCard('GID', task.gid)}
          {infoCard('Connections', task.connections || '0')}
        </div>

        {task.files && task.files.length > 0 && (
          <div>
            <label className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold mb-1 block">Files ({task.files.length})</label>
            <div className="space-y-1.5 max-h-36 overflow-y-auto">
              {task.files.map((file, idx) => (
                <div key={idx} className="bg-[var(--md-sys-color-surface-container-high)]/60 p-2 rounded-lg border border-[var(--md-sys-color-outline-variant)]/40 text-[11px] font-mono truncate flex items-center gap-2" title={file.path}>
                  <FileText size={14} className="text-teal-400 shrink-0" />
                  {file.path.split(/[/\\]/).pop()}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="pt-3 border-t border-[var(--md-sys-color-outline-variant)]/60 mt-3 flex flex-col gap-2">
        <button
          onClick={handlePauseResume}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            isActive
              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25'
              : 'bg-teal-500/15 text-teal-400 border border-teal-500/30 hover:bg-teal-500/25'
          }`}
        >
          {isActive ? <Pause size={16} /> : <Play size={16} />}
          <span>{isActive ? 'Pause Download' : 'Resume Download'}</span>
        </button>

        <button
          onClick={handleRemove}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25 transition-all cursor-pointer"
        >
          <TrashBinTrash size={16} />
          <span>Remove Task</span>
        </button>
      </div>
    </div>
  );
}
