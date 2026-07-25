'use client';

import React, { useState } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import TaskList from '@/components/task/TaskList';
import TaskControls from '@/components/task/TaskControls';
import TaskDetail from '@/components/task/TaskDetail';
import AddTaskDialog from '@/components/task/AddTaskDialog';
import PreferencePanel from '@/components/preference/PreferencePanel';
import AboutPanel from '@/components/about/AboutPanel';
import BrowseView from '@/components/provider/BrowseView';
import { useEngine } from '@/hooks/useEngine';
import { useTaskPolling } from '@/hooks/useTaskPolling';
import { useTaskStore } from '@/stores/task-store';

export default function Home() {
  useEngine();
  useTaskPolling();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [pendingAddUrls, setPendingAddUrls] = useState<string[]>([]);
  const selectedTask = useTaskStore((state) => state.selectedTask);
  const setSelectedTask = useTaskStore((state) => state.setSelectedTask);

  const openAddDialog = (urls: string[] = []) => {
    setPendingAddUrls(urls);
    setIsAddOpen(true);
  };

  const closeAddDialog = () => {
    setIsAddOpen(false);
    setPendingAddUrls([]);
  };

  return (
    <AppLayout>
      {({ activeView }) => {
        let content: React.ReactNode;

        if (activeView === 'preferences') {
          content = <PreferencePanel />;
        } else if (activeView === 'about') {
          content = <AboutPanel />;
        } else if (activeView === 'browse') {
          content = <BrowseView onOpenAddDialog={openAddDialog} />;
        } else {
          const statusFilterMap: Record<string, 'all' | 'active' | 'complete' | 'error'> = {
            downloads: 'all',
            active: 'active',
            completed: 'complete',
            errors: 'error',
          };

          const filter = statusFilterMap[activeView] || 'all';

          content = (
            <div className="flex flex-col h-full gap-4 relative">
              <TaskControls onOpenAddDialog={() => openAddDialog()} />
              <div className="flex-1 flex gap-4 overflow-hidden relative">
                <div className="flex-1 overflow-hidden">
                  <TaskList filter={filter} onOpenAddDialog={() => openAddDialog()} />
                </div>
                {selectedTask && (
                  <div className="w-80 shrink-0 border-l border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] rounded-[var(--md-sys-shape-corner-large)] p-4 overflow-y-auto z-10">
                    <TaskDetail task={selectedTask} onClose={() => setSelectedTask(null)} />
                  </div>
                )}
              </div>
            </div>
          );
        }

        return (
          <>
            {content}
            <AddTaskDialog
              isOpen={isAddOpen}
              onClose={closeAddDialog}
              initialUrls={pendingAddUrls}
            />
          </>
        );
      }}
    </AppLayout>
  );
}
