'use client';

import React, { useState } from 'react';
import type { Aria2Task } from '@/types';
import { bytesToSize, formatSpeed, formatEta, formatProgress } from '@/lib/utils';
import { pauseTask, prepareTorrentStream, removeTask, unpauseTask } from '@/lib/tauri';
import { CloseCircle, Pause, Play, TrashBinTrash, FileText, Clapperboard } from '@solar-icons/react';

const aria2ErrorMessages: Record<string, string> = {
  '1': 'Unknown error occurred',
  '2': 'Timeout — the server did not respond',
  '3': 'Resource not found (404)',
  '4': 'Forbidden — access denied (403)',
  '5': 'File not found on server',
  '6': 'Too many redirects',
  '7': 'Server returned an error',
  '8': 'Connection was reset',
  '9': 'Disk full — not enough space',
  '10': 'File write permission denied',
  '11': 'Name resolution failed',
  '12': 'TLS/SSL handshake failed',
  '13': 'Connection refused by server',
  '20': 'Invalid torrent file',
  '21': 'Magnet link could not be parsed',
  '22': 'No peers found for torrent',
};

const VIDEO_EXTENSIONS = new Set(['mp4', 'm4v', 'webm', 'mkv', 'mov', 'avi']);
const AUDIO_EXTENSIONS = new Set(['mp3', 'm4a', 'aac', 'ogg', 'oga', 'opus', 'flac', 'wav']);

function getAria2ErrorMessage(errorCode?: string): string | null {
  if (!errorCode) return null;
  return aria2ErrorMessages[errorCode] || `Error code: ${errorCode}`;
}

function basename(path: string): string {
  return path.split(/[/\\]/).pop() || path;
}

function extension(path: string): string {
  const name = basename(path);
  const dot = name.lastIndexOf('.');
  return dot >= 0 ? name.slice(dot + 1).toLowerCase() : '';
}

function isStreamableMedia(path: string): boolean {
  const ext = extension(path);
  return VIDEO_EXTENSIONS.has(ext) || AUDIO_EXTENSIONS.has(ext);
}

interface TaskDetailProps {
  task: Aria2Task;
  onClose: () => void;
}

interface StreamState {
  gid: string;
  url: string;
  path: string;
}

interface StreamErrorState {
  gid: string;
  message: string;
}

interface StreamLoadingState {
  gid: string;
  index: string;
}

export default function TaskDetail({ task, onClose }: TaskDetailProps) {
  const [streamState, setStreamState] = useState<StreamState>({ gid: '', url: '', path: '' });
  const [streamErrorState, setStreamErrorState] = useState<StreamErrorState>({ gid: '', message: '' });
  const [streamLoadingState, setStreamLoadingState] = useState<StreamLoadingState | null>(null);

  const streamUrl = streamState.gid === task.gid ? streamState.url : '';
  const streamPath = streamState.gid === task.gid ? streamState.path : '';
  const streamError = streamErrorState.gid === task.gid ? streamErrorState.message : '';
  const streamLoadingIndex = streamLoadingState?.gid === task.gid ? streamLoadingState.index : null;

  const name = task.bittorrent?.info?.name || task.title ||
    (task.files && task.files[0]?.path ? basename(task.files[0].path) : null) || 'Unnamed Task';

  const dir = task.dir || (task.files && task.files[0]?.path ? task.files[0].path : 'N/A');

  const total = parseInt(task.totalLength, 10) || 0;
  const completed = parseInt(task.completedLength, 10) || 0;
  const speed = parseInt(task.downloadSpeed, 10) || 0;

  const progress = formatProgress(completed, total);
  const sizeFormatted = total > 0 ? `${bytesToSize(completed)} / ${bytesToSize(total)}` : bytesToSize(completed);
  const speedFormatted = formatSpeed(speed);
  const etaFormatted = formatEta(total, completed, speed);

  const canPause = task.status === 'active' || task.status === 'waiting';
  const canResume = task.status === 'paused';
  const hasTorrentMedia = Boolean(task.bittorrent) && task.files.some((file) => isStreamableMedia(file.path));

  const handlePauseResume = async () => {
    try {
      if (canPause) await pauseTask(task.gid);
      else if (canResume) await unpauseTask(task.gid);
    } catch (err) {
      console.error('Failed toggle pause/resume:', err);
    }
  };

  const handleRemove = async () => {
    try {
      await removeTask(task.gid, task.status);
      onClose();
    } catch (err) {
      console.error('Failed to remove task:', err);
    }
  };

  const handleStream = async (file: Aria2Task['files'][number]) => {
    const gid = task.gid;
    setStreamLoadingState({ gid, index: file.index });
    setStreamErrorState({ gid, message: '' });
    try {
      const url = await prepareTorrentStream(gid, file.index);
      setStreamState({ gid, url, path: file.path });
    } catch (error) {
      console.error('Failed to prepare torrent stream:', error);
      setStreamErrorState({
        gid,
        message: error instanceof Error ? error.message : String(error),
      });
    } finally {
      setStreamLoadingState((current) =>
        current?.gid === gid && current.index === file.index ? null : current,
      );
    }
  };

  const infoCard = (label: string, value: string, color = 'text-[var(--md-sys-color-on-surface)]') => (
    <div className="bg-[var(--md-sys-color-surface-container-high)]/60 p-3 rounded-xl border border-[var(--md-sys-color-outline-variant)]/50">
      <span className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold mb-0.5 block">{label}</span>
      <span className={`text-xs font-mono font-bold ${color}`}>{value}</span>
    </div>
  );

  return (
    <div className="flex flex-col h-full text-[var(--md-sys-color-on-surface)]">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--md-sys-color-outline-variant)]/60">
        <h3 className="text-xs font-bold uppercase tracking-wider text-teal-400">Task Details</h3>
        <button
          onClick={onClose}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)] hover:text-[var(--md-sys-color-on-surface)] transition-colors cursor-pointer"
        >
          <CloseCircle size={16} />
        </button>
      </div>

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

        {task.status === 'error' && (() => {
          const errMsg = getAria2ErrorMessage(task.errorCode);
          const detail = errMsg || task.errorMessage || null;
          if (!detail) return null;
          return (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3">
              <label className="text-[9px] text-red-400 uppercase tracking-wider font-bold mb-1 block">Error</label>
              <p className="text-xs font-mono text-red-300/90 break-all">{detail}</p>
            </div>
          );
        })()}

        {streamError && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-xs text-red-300">
            Could not start torrent stream: {streamError}
          </div>
        )}

        {streamUrl && streamPath && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-teal-400">
              <Clapperboard size={14} />
              Streaming {basename(streamPath)}
            </div>
            {AUDIO_EXTENSIONS.has(extension(streamPath)) ? (
              <audio
                key={streamUrl}
                src={streamUrl}
                controls
                autoPlay
                preload="metadata"
                className="w-full"
              />
            ) : (
              <video
                key={streamUrl}
                src={streamUrl}
                controls
                autoPlay
                preload="metadata"
                className="w-full rounded-xl bg-black border border-[var(--md-sys-color-outline-variant)]/50"
              />
            )}
            <p className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              Playback is served from verified aria2 pieces over a loopback-only HTTP Range stream. The selected media file is prioritized while it downloads.
            </p>
          </div>
        )}

        {task.files && task.files.length > 0 && (
          <div>
            <label className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] uppercase tracking-wider font-bold mb-1 block">Files ({task.files.length})</label>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {task.files.map((file) => {
                const streamable = Boolean(task.bittorrent) && isStreamableMedia(file.path);
                return (
                  <div
                    key={file.index}
                    className="bg-[var(--md-sys-color-surface-container-high)]/60 p-2 rounded-lg border border-[var(--md-sys-color-outline-variant)]/40 text-[11px] font-mono flex items-center gap-2"
                    title={file.path}
                  >
                    <FileText size={14} className="text-teal-400 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate">{basename(file.path)}</div>
                      <div className="text-[9px] text-[var(--md-sys-color-on-surface-variant)] mt-0.5">
                        {bytesToSize(parseInt(file.completedLength, 10) || 0)} / {bytesToSize(parseInt(file.length, 10) || 0)}
                      </div>
                    </div>
                    {streamable && (
                      <button
                        type="button"
                        onClick={() => void handleStream(file)}
                        disabled={streamLoadingIndex !== null || task.status === 'error' || task.status === 'removed'}
                        className="shrink-0 inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-bold bg-teal-500/15 text-teal-400 border border-teal-500/30 hover:bg-teal-500/25 disabled:opacity-50 transition-colors cursor-pointer"
                        title="Stream this torrent file while downloading"
                      >
                        <Play size={11} />
                        {streamLoadingIndex === file.index ? 'Buffering' : 'Stream'}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
            {hasTorrentMedia && !streamUrl && (
              <p className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] mt-2">
                Choose Stream on a media file to prioritize it and start playback before the torrent finishes.
              </p>
            )}
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-[var(--md-sys-color-outline-variant)]/60 mt-3 flex flex-col gap-2">
        {(canPause || canResume) && (
          <button
            onClick={handlePauseResume}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              canPause
                ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25'
                : 'bg-teal-500/15 text-teal-400 border border-teal-500/30 hover:bg-teal-500/25'
            }`}
          >
            {canPause ? <Pause size={16} /> : <Play size={16} />}
            <span>{canPause ? 'Pause Download' : 'Resume Download'}</span>
          </button>
        )}

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
