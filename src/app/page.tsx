'use client';

import React, { useState } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import TaskList from '@/components/task/TaskList';
import TaskControls from '@/components/task/TaskControls';
import TaskDetail from '@/components/task/TaskDetail';
import AddTaskDialog from '@/components/task/AddTaskDialog';
import ScraperPanel from '@/components/fitgirl/ScraperPanel';
import PreferencePanel from '@/components/preference/PreferencePanel';
import AboutPanel from '@/components/about/AboutPanel';
import { useEngine } from '@/hooks/useEngine';
import { useTaskPolling } from '@/hooks/useTaskPolling';
import { useTaskStore } from '@/stores/task-store';

export default function Home() {
  useEngine();
  useTaskPolling();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const selectedTask = useTaskStore((state) => state.selectedTask);
  const setSelectedTask = useTaskStore((state) => state.setSelectedTask);

  return (
    <AppLayout>
      {({ activeView }) => {
        if (activeView === 'scraper') {
          return <ScraperPanel />;
        }

        if (activeView === 'preferences') {
          return <PreferencePanel />;
        }

        if (activeView === 'about') {
          return <AboutPanel />;
        }

        const statusFilterMap: Record<string, 'all' | 'active' | 'complete' | 'error'> = {
          downloads: 'all',
          active: 'active',
          completed: 'complete',
          errors: 'error',
        };

        const filter = statusFilterMap[activeView] || 'all';

        return (
          <div className="flex flex-col h-full gap-4 relative">
            <TaskControls onOpenAddDialog={() => setIsAddOpen(true)} />
            <div className="flex-1 flex gap-4 overflow-hidden relative">
              <div className="flex-1 overflow-hidden">
                <TaskList filter={filter} onOpenAddDialog={() => setIsAddOpen(true)} />
              </div>
              {selectedTask && (
                <div className="w-80 shrink-0 border-l border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] rounded-[var(--md-sys-shape-corner-large)] p-4 overflow-y-auto z-10">
                  <TaskDetail task={selectedTask} onClose={() => setSelectedTask(null)} />
                </div>
              )}
            </div>
            <AddTaskDialog isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} />
          </div>
        );
      }}
    </AppLayout>
  );
}
