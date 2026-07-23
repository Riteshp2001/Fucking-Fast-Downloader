'use client';

import React from 'react';
import TaskItem from './TaskItem';
import { useTaskStore } from '@/stores/task-store';
import { pauseTask, unpauseTask, removeTask } from '@/lib/tauri';
import type { Aria2Task } from '@/types';
import { Bolt, AddSquare } from '@solar-icons/react';

interface TaskListProps {
  filter: 'all' | 'active' | 'complete' | 'error';
  onOpenAddDialog?: () => void;
}

export default function TaskList({ filter, onOpenAddDialog }: TaskListProps) {
  const tasks = useTaskStore((state) => state.tasks);
  const selectedTask = useTaskStore((state) => state.selectedTask);
  const setSelectedTask = useTaskStore((state) => state.setSelectedTask);

  const filteredTasks = tasks.filter((task) => {
    if (filter === 'all') return true;
    if (filter === 'active') return task.status === 'active' || task.status === 'waiting';
    return task.status === filter;
  });

  const handlePause = async (task: Aria2Task, e: React.MouseEvent) => {
    e.stopPropagation();
    try { await pauseTask(task.gid); }
    catch (err) { console.error('Failed to pause task:', err); }
  };

  const handleResume = async (task: Aria2Task, e: React.MouseEvent) => {
    e.stopPropagation();
    try { await unpauseTask(task.gid); }
    catch (err) { console.error('Failed to resume task:', err); }
  };

  const handleRemove = async (task: Aria2Task, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await removeTask(task.gid);
      if (selectedTask?.gid === task.gid) setSelectedTask(null);
    } catch (err) { console.error('Failed to remove task:', err); }
  };

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex-1 overflow-y-auto space-y-2.5 pb-6 pr-2">
        {filteredTasks.length > 0 ? (
          filteredTasks.map((task, idx) => (
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
              />
            </div>
          ))
        ) : (
          <div className="h-full min-h-[340px] flex flex-col items-center justify-center text-center bg-[var(--md-sys-color-surface-container)] rounded-2xl border border-[var(--md-sys-color-outline-variant)]/50 p-8 animate-scale-in-emil">
            <div className="w-16 h-16 rounded-2xl bg-[var(--md-sys-color-primary-container)] text-[var(--md-sys-color-on-primary-container)] flex items-center justify-center mb-4 border border-[var(--md-sys-color-outline-variant)] shadow-sm">
              <Bolt size={32} />
            </div>
            <h3 className="text-sm font-bold mb-1 text-[var(--md-sys-color-on-surface)] tracking-wide">
              No downloads found
            </h3>
            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] max-w-xs mb-5 leading-relaxed">
              {filter === 'all'
                ? 'Add your first download task or use the FitGirl scraper to fetch links.'
                : `No ${filter} downloads right now.`}
            </p>

            {onOpenAddDialog && (
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
