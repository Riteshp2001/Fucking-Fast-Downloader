'use client';

import React from 'react';
import TaskItem from './TaskItem';
import { useTaskStore } from '@/stores/task-store';
import { addUri, pauseTask, removeTask as removeAria2Task, unpauseTask } from '@/lib/tauri';
import type { Aria2Task, DownloadTask } from '@/types';
import { Bolt, AddSquare } from '@solar-icons/react';

interface TaskListProps {
  filter: 'all' | 'active' | 'complete' | 'error';
  onOpenAddDialog?: () => void;
}

function getTaskSourceUri(task: Aria2Task): string | null {
  for (const file of task.files ?? []) {
    for (const source of file.uris ?? []) {
      if (source.uri?.trim()) return source.uri.trim();
    }
  }
  return null;
}

function getTaskOutputName(task: Aria2Task): string | null {
  const path = task.files?.[0]?.path;
  if (!path) return null;
  return path.split(/[/\\]/).pop() || null;
}

function matchesSearch(task: DownloadTask, query: string): boolean {
  if (!query) return true;
  const fileText = task.files
    .flatMap((file) => [file.path, ...file.uris.map((source) => source.uri)])
    .join(' ');
  const searchable = [
    task.displayName,
    task.title ?? '',
    task.dir,
    task.errorMessage ?? '',
    fileText,
  ].join(' ').toLowerCase();

  return searchable.includes(query);
}

export default function TaskList({ filter, onOpenAddDialog }: TaskListProps) {
  const tasks = useTaskStore((state) => state.tasks);
  const searchQuery = useTaskStore((state) => state.searchQuery);
  const selectedTask = useTaskStore((state) => state.selectedTask);
  const setSelectedTask = useTaskStore((state) => state.setSelectedTask);
  const removeFromStore = useTaskStore((state) => state.removeTask);
  const normalizedQuery = searchQuery.trim().toLowerCase();

  const filteredTasks = tasks.filter((task) => {
    if (filter === 'all') return matchesSearch(task, normalizedQuery);
    if (filter === 'active') {
      return (task.status === 'active' || task.status === 'waiting') && matchesSearch(task, normalizedQuery);
    }
    return task.status === filter && matchesSearch(task, normalizedQuery);
  });

  const handlePause = async (task: Aria2Task, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await pauseTask(task.gid);
    } catch (err) {
      console.error('Failed to pause task:', err);
    }
  };

  const handleResume = async (task: Aria2Task, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await unpauseTask(task.gid);
    } catch (err) {
      console.error('Failed to resume task:', err);
    }
  };

  const handleRemove = async (task: Aria2Task, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await removeAria2Task(task.gid, task.status);
      removeFromStore(task.gid);
      if (selectedTask?.gid === task.gid) setSelectedTask(null);
    } catch (err) {
      console.error('Failed to remove task:', err);
    }
  };

  const handleRetry = async (task: Aria2Task, e: React.MouseEvent) => {
    e.stopPropagation();
    const sourceUri = getTaskSourceUri(task);
    if (!sourceUri) return;

    const options: Record<string, unknown> = {};
    if (task.dir?.trim()) options.dir = task.dir.trim();
    const out = getTaskOutputName(task);
    if (out) options.out = out;

    try {
      await addUri(sourceUri, options);
      await removeAria2Task(task.gid, task.status);
      removeFromStore(task.gid);
    } catch (err) {
      console.error('Failed to retry task:', err);
    }
  };

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex-1 overflow-y-auto space-y-2.5 pb-6 pr-2">
        {filteredTasks.length > 0 ? (
          filteredTasks.map((task, idx) => {
            const canRetry = task.status === 'error' && Boolean(getTaskSourceUri(task));

            return (
              <div
                key={task.gid}
                className="animate-slide-up-emil"
                style={{ animationDelay: `${Math.min(idx * 40, 240)}ms` }}
              >
                <TaskItem
                  task={task}
                  isSelected={selectedTask?.gid === task.gid}
                  onClick={() => setSelectedTask(selectedTask?.gid === task.gid ? null : task)}
                  onPause={(e) => handlePause(task, e)}
                  onResume={(e) => handleResume(task, e)}
                  onRemove={(e) => handleRemove(task, e)}
                  onRetry={canRetry ? (e) => handleRetry(task, e) : undefined}
                />
              </div>
            );
          })
        ) : (
          <div className="h-full min-h-[340px] flex flex-col items-center justify-center text-center bg-[var(--md-sys-color-surface-container)] rounded-2xl border border-[var(--md-sys-color-outline-variant)]/50 p-8 animate-scale-in-emil">
            <div className="w-16 h-16 rounded-2xl bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] flex items-center justify-center mb-4 border border-[var(--md-sys-color-outline-variant)] shadow-sm">
              <Bolt size={32} />
            </div>
            <h3 className="text-sm font-bold mb-1 text-[var(--md-sys-color-on-surface)] tracking-wide">
              {normalizedQuery ? 'No matching downloads' : 'No downloads found'}
            </h3>
            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-xs mb-5 leading-relaxed">
              {normalizedQuery
                ? `Nothing in this view matches “${searchQuery.trim()}”.`
                : filter === 'all'
                  ? 'Add your first download task with a direct URL, magnet URI, or torrent file.'
                  : `No ${filter} downloads right now.`}
            </p>

            {onOpenAddDialog && !normalizedQuery && (
              <button
                onClick={onOpenAddDialog}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] hover:bg-[var(--md-sys-color-primary)] hover:text-[var(--md-sys-color-on-primary)] active-press transition-all cursor-pointer"
              >
                <AddSquare size={16} />
                <span>Add New Task</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
