'use client';

import React from 'react';
import { useAppStore } from '@/stores/app-store';
import { useTaskStore } from '@/stores/task-store';
import { SIcon } from '@/components/ui/SIcon';
import {
  DownloadMinimalistic,
  Bolt,
  CheckCircle,
  CloseCircle,
  Link,
  Settings,
  InfoCircle,
  AltArrowDown,
  AltArrowUp,
} from '@solar-icons/react';

interface SidebarProps {
  activeView: string;
  onSelectView: (view: string) => void;
}

const navItems = [
  { id: 'downloads', label: 'All Downloads', icon: DownloadMinimalistic },
  { id: 'active', label: 'Active', icon: Bolt },
  { id: 'completed', label: 'Completed', icon: CheckCircle },
  { id: 'errors', label: 'Errors', icon: CloseCircle },
  { id: 'scraper', label: 'FitGirl Scraper', icon: Link },
  { id: 'preferences', label: 'Preferences', icon: Settings },
  { id: 'about', label: 'About', icon: InfoCircle },
];

export default function Sidebar({ activeView, onSelectView }: SidebarProps) {
  const { engineStatus, downloadSpeed, uploadSpeed } = useAppStore();
  const tasks = useTaskStore((state) => state.tasks);

  const getBadgeCount = (id: string) => {
    if (id === 'downloads') return tasks.length;
    if (id === 'active') return tasks.filter(t => t.status === 'active' || t.status === 'waiting').length;
    if (id === 'completed') return tasks.filter(t => t.status === 'complete').length;
    if (id === 'errors') return tasks.filter(t => t.status === 'error').length;
    return null;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-[var(--md-sys-color-primary)]';
      case 'starting': return 'text-[var(--md-sys-color-tertiary)]';
      case 'error': return 'text-[var(--md-sys-color-error)]';
      default: return 'text-[var(--md-sys-color-on-surface-variant)]';
    }
  };

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'running': return 'bg-[var(--md-sys-color-primary)]';
      case 'starting': return 'bg-[var(--md-sys-color-tertiary)]';
      case 'error': return 'bg-[var(--md-sys-color-error)]';
      default: return 'bg-[var(--md-sys-color-outline-variant)]';
    }
  };

  return (
    <aside className="w-60 h-full flex flex-col bg-[var(--md-sys-color-surface-container)] border-r border-[var(--md-sys-color-outline-variant)] relative z-10 select-none">
      {/* Navigation Links - Material 3 Expressive Navigation Drawer with Tactile Feedback */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = activeView === item.id;
          const count = getBadgeCount(item.id);

          return (
            <button
              key={item.id}
              onClick={() => onSelectView(item.id)}
              className={`w-full flex items-center justify-between px-4 py-2.5 rounded-full active-press transition-all duration-200 [transition-timing-function:var(--ease-emil-out)] group cursor-pointer ${
                isActive
                  ? 'bg-[var(--md-sys-color-secondary-container)] text-[var(--md-sys-color-on-secondary-container)] font-semibold shadow-sm'
                  : 'text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-high)] hover:text-[var(--md-sys-color-on-surface)]'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="flex items-center justify-center w-5 h-5 transition-transform duration-200 group-hover:scale-110">
                  <SIcon icon={item.icon} size={20} />
                </span>
                <span className="text-xs font-medium">{item.label}</span>
              </div>

              {count !== null && count > 0 && (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold transition-all duration-200 ${
                  isActive
                    ? 'bg-[var(--md-sys-color-on-secondary-container)] text-[var(--md-sys-color-secondary-container)]'
                    : 'bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)]'
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Engine & Stats Card */}
      <div className="p-3.5 m-3 bg-[var(--md-sys-color-surface-container-high)] rounded-[var(--md-sys-shape-corner-medium)] border border-[var(--md-sys-color-outline-variant)]">
        <div className="flex items-center justify-between mb-2.5">
          <span className="text-[10px] font-bold text-[var(--md-sys-color-on-surface-variant)] tracking-wider uppercase">Engine</span>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${getStatusDot(engineStatus)}`} />
            <span className={`text-[11px] font-semibold capitalize ${getStatusColor(engineStatus)}`}>{engineStatus}</span>
          </div>
        </div>

        <div className="space-y-1.5 pt-2 border-t border-[var(--md-sys-color-outline-variant)]">
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--md-sys-color-on-surface-variant)] text-[11px] flex items-center gap-1">
              <AltArrowDown size={13} className="text-[var(--md-sys-color-primary)]" /> Down
            </span>
            <span className="font-mono text-[11px] text-[var(--md-sys-color-primary)] font-semibold">{downloadSpeed || '0 KB/s'}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[var(--md-sys-color-on-surface-variant)] text-[11px] flex items-center gap-1">
              <AltArrowUp size={13} className="text-[var(--md-sys-color-secondary)]" /> Up
            </span>
            <span className="font-mono text-[11px] text-[var(--md-sys-color-secondary)] font-semibold">{uploadSpeed || '0 KB/s'}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
