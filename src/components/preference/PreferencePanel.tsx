'use client';

import React, { useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import {
  Settings, Tuning2,
  ArrowToDownLeft, Download, Folder2, Link,
} from '@solar-icons/react';
import { MdSwitch } from '@/components/MdComponents';

type Tab = 'general' | 'downloads' | 'advanced';

const TABS: { id: Tab; label: string; Icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { id: 'general', label: 'General', Icon: Settings },
  { id: 'downloads', label: 'Downloads', Icon: ArrowToDownLeft },
  { id: 'advanced', label: 'Advanced', Icon: Tuning2 },
];

export default function PreferencePanel() {
  const [activeTab, setActiveTab] = useState<Tab>('general');
  const { preferences, updatePreferences, appearance, setAppearance } = useAppStore();

  const renderTab = () => {
    switch (activeTab) {
      case 'general':
        return (
          <div className="space-y-4">
            <Section title="Appearance" Icon={Settings}>
              <ToggleRow label="Compact Mode" value={appearance.compact_mode} onChange={(v) => setAppearance({ compact_mode: v })} />
              <ToggleRow label="Show Speed Graph" value={appearance.show_speed_graph} onChange={(v) => setAppearance({ show_speed_graph: v })} />
              <ToggleRow label="Show Notification Badges" value={appearance.show_badges} onChange={(v) => setAppearance({ show_badges: v })} />
              <ToggleRow label="Minimize to Tray" value={appearance.minimize_to_tray} onChange={(v) => setAppearance({ minimize_to_tray: v })} />
            </Section>
          </div>
        );

      case 'downloads':
        return (
          <div className="space-y-4">
            <Section title="Directories" Icon={Folder2}>
              <div>
                <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">Download Directory</label>
                <input type="text" value={preferences.download_dir} onChange={(e) => updatePreferences({ download_dir: e.target.value })}
                  className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">Temp Directory</label>
                <input type="text" value={preferences.temp_dir} onChange={(e) => updatePreferences({ temp_dir: e.target.value })}
                  className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors" />
              </div>
            </Section>
            <Section title="Limits" Icon={Download}>
              <div className="grid grid-cols-2 gap-2">
                <NumberRow label="Max Concurrent" value={preferences.max_concurrent_downloads} min={1} max={50}
                  onChange={(v) => updatePreferences({ max_concurrent_downloads: v })} />
                <NumberRow label="Max Connections" value={preferences.max_connections_per_server} min={1} max={32}
                  onChange={(v) => updatePreferences({ max_connections_per_server: v })} />
              </div>
            </Section>
          </div>
        );

      case 'advanced':
        return (
          <div className="space-y-4">
            <Section title="Aria2 Settings" Icon={Tuning2}>
              <ToggleRow label="Enable RPC Auth" value={preferences.aria2_enable_rpc_auth} onChange={(v) => updatePreferences({ aria2_enable_rpc_auth: v })} />
              {preferences.aria2_enable_rpc_auth && (
                <div>
                  <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">RPC Secret</label>
                  <input type="password" value={preferences.aria2_rpc_secret || ''} onChange={(e) => updatePreferences({ aria2_rpc_secret: e.target.value })}
                    className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors" />
                </div>
              )}
            </Section>
            <Section title="Proxy" Icon={Link}>
              <ToggleRow label="Use Proxy" value={!!preferences.proxy_enabled} onChange={(v) => updatePreferences({ proxy_enabled: v })} />
              {preferences.proxy_enabled && (
                <div>
                  <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">Proxy URL</label>
                  <input type="text" value={preferences.proxy_url || ''} onChange={(e) => updatePreferences({ proxy_url: e.target.value })}
                    placeholder="http://127.0.0.1:1080"
                    className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors" />
                </div>
              )}
            </Section>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full text-[var(--md-sys-color-on-surface)] animate-slide-up-emil select-none">
      <div className="border-b border-[var(--md-sys-color-outline-variant)] mb-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)] mb-3">Preferences</h3>
        <div className="flex gap-2 -mb-px">
          {TABS.map(({ id, label, Icon }) => (
            <button key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                activeTab === id
                  ? 'border-[var(--md-sys-color-primary)] text-[var(--md-sys-color-primary)]'
                  : 'border-transparent text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:border-[var(--md-sys-color-outline-variant)]'
              }`}>
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto pr-1">
        {renderTab()}
      </div>
    </div>
  );
}

function Section({ title, Icon, children }: { title: string; Icon: React.ComponentType<{ size?: number; className?: string }>; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={15} className="text-[var(--md-sys-color-primary)]" />
        <h4 className="text-[10px] font-bold uppercase tracking-wider text-[var(--md-sys-color-on-surface-variant)]">{title}</h4>
      </div>
      <div className="bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] rounded-xl p-3.5 space-y-3">
        {children}
      </div>
    </div>
  );
}

function ToggleRow({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between min-h-[36px]">
      <span className="text-xs text-[var(--md-sys-color-on-surface)]">{label}</span>
      <MdSwitch selected={value} onChange={(val) => onChange(val)} />
    </div>
  );
}

function NumberRow({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (v: number) => void }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">{label}</label>
      <input type="number" value={value} min={min} max={max}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || min)}
        className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors" />
    </div>
  );
}
