'use client';

import React, { useEffect, useState } from 'react';
import { open as openDialog } from '@tauri-apps/plugin-dialog';
import { load } from '@tauri-apps/plugin-store';
import { useAppStore } from '@/stores/app-store';
import {
  getSystemConfig,
  isTauri,
  restartEngine,
  saveSystemConfig,
  waitForEngine,
} from '@/lib/tauri';
import { formatError } from '@/lib/errors';
import {
  Settings,
  Tuning2,
  ArrowToDownLeft,
  Download,
  Folder2,
  Link,
} from '@solar-icons/react';
import { MdSwitch } from '@/components/MdComponents';

type Tab = 'general' | 'downloads' | 'advanced';
type SaveState = 'idle' | 'saving' | 'saved' | 'error';

type StoredRecord = Record<string, unknown>;

const TABS: { id: Tab; label: string; Icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { id: 'general', label: 'General', Icon: Settings },
  { id: 'downloads', label: 'Downloads', Icon: ArrowToDownLeft },
  { id: 'advanced', label: 'Advanced', Icon: Tuning2 },
];

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function asNumber(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = parseInt(value, 10);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function asBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function clampInteger(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, Math.round(value)));
}

function validateProxyUrl(value: string): string | null {
  if (!value.trim()) return 'Enter a proxy URL or turn proxy usage off.';

  try {
    const url = new URL(value.trim());
    if (!['http:', 'https:', 'ftp:'].includes(url.protocol)) {
      return 'The download engine supports HTTP, HTTPS, or FTP proxy URLs.';
    }
    if (!url.hostname) return 'Enter a valid proxy host.';
  } catch {
    return 'Enter a valid proxy URL, for example http://127.0.0.1:8080.';
  }

  return null;
}

export default function PreferencePanel() {
  const [activeTab, setActiveTab] = useState<Tab>('general');
  const [loading, setLoading] = useState(() => isTauri());
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const {
    preferences,
    updatePreferences,
    appearance,
    setAppearance,
    setEngineStatus,
  } = useAppStore();

  useEffect(() => {
    if (!isTauri()) return;

    let cancelled = false;

    const loadPreferences = async () => {
      try {
        const [systemConfig, store] = await Promise.all([
          getSystemConfig(),
          load('config.json'),
        ]);
        const storedPreferences = await store.get<StoredRecord>('ffDownloaderPreferences') ?? {};
        const storedAppearance = await store.get<StoredRecord>('ffDownloaderAppearance') ?? {};
        const enginePreferences = await store.get<StoredRecord>('preferences') ?? {};

        if (cancelled) return;

        const rpcSecret = asString(systemConfig['rpc-secret']);
        const proxyUrl = asString(systemConfig['all-proxy']);

        updatePreferences({
          download_dir: asString(systemConfig.dir) || asString(storedPreferences.download_dir),
          temp_dir: asString(enginePreferences.tempFilesDir) || asString(storedPreferences.temp_dir),
          max_concurrent_downloads: clampInteger(
            asNumber(systemConfig['max-concurrent-downloads'], asNumber(storedPreferences.max_concurrent_downloads, preferences.max_concurrent_downloads)),
            1,
            50,
          ),
          max_connections_per_server: clampInteger(
            asNumber(systemConfig['max-connection-per-server'], asNumber(storedPreferences.max_connections_per_server, preferences.max_connections_per_server)),
            1,
            32,
          ),
          aria2_enable_rpc_auth: rpcSecret.length > 0 || asBoolean(storedPreferences.aria2_enable_rpc_auth, false),
          aria2_rpc_secret: rpcSecret || asString(storedPreferences.aria2_rpc_secret),
          proxy_enabled: proxyUrl.length > 0 || asBoolean(storedPreferences.proxy_enabled, false),
          proxy_url: proxyUrl || asString(storedPreferences.proxy_url),
        });

        setAppearance({
          compact_mode: asBoolean(storedAppearance.compact_mode, appearance.compact_mode),
          show_speed_graph: asBoolean(storedAppearance.show_speed_graph, appearance.show_speed_graph),
          show_badges: asBoolean(storedAppearance.show_badges, appearance.show_badges),
          minimize_to_tray: asBoolean(
            enginePreferences.minimizeToTrayOnClose,
            asBoolean(storedAppearance.minimize_to_tray, appearance.minimize_to_tray),
          ),
        });
      } catch (error) {
        console.error('Failed to load preferences:', error);
        if (!cancelled) {
          setSaveState('error');
          setStatusMessage(`Could not load saved settings: ${formatError(error)}`);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadPreferences();
    return () => {
      cancelled = true;
    };
    // This is intentionally a one-time hydration of persisted settings.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const chooseDirectory = async (kind: 'download' | 'temp') => {
    if (!isTauri()) return;
    try {
      const selected = await openDialog({
        directory: true,
        multiple: false,
        title: kind === 'download' ? 'Choose Download Directory' : 'Choose Temporary Directory',
      });
      if (typeof selected === 'string') {
        if (kind === 'download') updatePreferences({ download_dir: selected });
        else updatePreferences({ temp_dir: selected });
        setSaveState('idle');
        setStatusMessage('');
      }
    } catch (error) {
      setSaveState('error');
      setStatusMessage(`Could not open the folder picker: ${formatError(error)}`);
    }
  };

  const handleSave = async () => {
    if (!isTauri()) {
      setSaveState('error');
      setStatusMessage('Settings can only be applied in the desktop application.');
      return;
    }

    if (preferences.proxy_enabled) {
      const proxyError = validateProxyUrl(preferences.proxy_url ?? '');
      if (proxyError) {
        setSaveState('error');
        setStatusMessage(proxyError);
        setActiveTab('advanced');
        return;
      }
    }

    if (preferences.aria2_enable_rpc_auth && !(preferences.aria2_rpc_secret ?? '').trim()) {
      setSaveState('error');
      setStatusMessage('RPC authentication is enabled but the RPC secret is empty.');
      setActiveTab('advanced');
      return;
    }

    setSaveState('saving');
    setStatusMessage('Saving settings and restarting the download engine…');
    setEngineStatus('starting');

    try {
      const normalizedPreferences = {
        ...preferences,
        max_concurrent_downloads: clampInteger(preferences.max_concurrent_downloads, 1, 50),
        max_connections_per_server: clampInteger(preferences.max_connections_per_server, 1, 32),
        download_dir: preferences.download_dir.trim(),
        temp_dir: preferences.temp_dir.trim(),
        aria2_rpc_secret: (preferences.aria2_rpc_secret ?? '').trim(),
        proxy_url: (preferences.proxy_url ?? '').trim(),
      };
      updatePreferences(normalizedPreferences);

      await saveSystemConfig({
        dir: normalizedPreferences.download_dir,
        'max-concurrent-downloads': String(normalizedPreferences.max_concurrent_downloads),
        'max-connection-per-server': String(normalizedPreferences.max_connections_per_server),
        'rpc-secret': normalizedPreferences.aria2_enable_rpc_auth ? normalizedPreferences.aria2_rpc_secret : '',
        'all-proxy': normalizedPreferences.proxy_enabled ? normalizedPreferences.proxy_url : '',
      });

      const store = await load('config.json');
      const existingEnginePreferences = await store.get<StoredRecord>('preferences') ?? {};
      await store.set('preferences', {
        ...existingEnginePreferences,
        tempFilesDir: normalizedPreferences.temp_dir,
        minimizeToTrayOnClose: appearance.minimize_to_tray,
      });
      await store.set('ffDownloaderPreferences', normalizedPreferences);
      await store.set('ffDownloaderAppearance', appearance);
      await store.save();

      await restartEngine();
      const ready = await waitForEngine();
      if (!ready) {
        throw new Error('The download engine did not become ready after applying the new settings.');
      }

      setEngineStatus('running');
      setSaveState('saved');
      setStatusMessage('Settings applied. The download engine is running with the new configuration.');
    } catch (error) {
      console.error('Failed to apply preferences:', error);
      setEngineStatus('error');
      setSaveState('error');
      setStatusMessage(`Could not apply settings: ${formatError(error)}`);
    }
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'general':
        return (
          <div className="space-y-4">
            <Section title="Appearance" Icon={Settings}>
              <ToggleRow label="Compact Mode" value={appearance.compact_mode} onChange={(value) => { setAppearance({ compact_mode: value }); setSaveState('idle'); }} />
              <ToggleRow label="Show Notification Badges" value={appearance.show_badges} onChange={(value) => { setAppearance({ show_badges: value }); setSaveState('idle'); }} />
              <ToggleRow label="Minimize to Tray" value={appearance.minimize_to_tray} onChange={(value) => { setAppearance({ minimize_to_tray: value }); setSaveState('idle'); }} />
            </Section>
          </div>
        );

      case 'downloads':
        return (
          <div className="space-y-4">
            <Section title="Directories" Icon={Folder2}>
              <DirectoryRow
                label="Download Directory"
                value={preferences.download_dir}
                onChange={(value) => { updatePreferences({ download_dir: value }); setSaveState('idle'); }}
                onBrowse={() => void chooseDirectory('download')}
              />
              <DirectoryRow
                label="Temp Directory"
                value={preferences.temp_dir}
                onChange={(value) => { updatePreferences({ temp_dir: value }); setSaveState('idle'); }}
                onBrowse={() => void chooseDirectory('temp')}
              />
            </Section>
            <Section title="Limits" Icon={Download}>
              <div className="grid grid-cols-2 gap-2">
                <NumberRow
                  label="Max Concurrent"
                  value={preferences.max_concurrent_downloads}
                  min={1}
                  max={50}
                  onChange={(value) => { updatePreferences({ max_concurrent_downloads: value }); setSaveState('idle'); }}
                />
                <NumberRow
                  label="Max Connections"
                  value={preferences.max_connections_per_server}
                  min={1}
                  max={32}
                  onChange={(value) => { updatePreferences({ max_connections_per_server: value }); setSaveState('idle'); }}
                />
              </div>
            </Section>
          </div>
        );

      case 'advanced':
        return (
          <div className="space-y-4">
            <Section title="Aria2 Settings" Icon={Tuning2}>
              <ToggleRow
                label="Enable RPC Auth"
                value={preferences.aria2_enable_rpc_auth}
                onChange={(value) => { updatePreferences({ aria2_enable_rpc_auth: value }); setSaveState('idle'); }}
              />
              {preferences.aria2_enable_rpc_auth && (
                <div>
                  <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">RPC Secret</label>
                  <input
                    type="password"
                    value={preferences.aria2_rpc_secret || ''}
                    onChange={(e) => { updatePreferences({ aria2_rpc_secret: e.target.value }); setSaveState('idle'); }}
                    autoComplete="off"
                    className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors"
                  />
                </div>
              )}
            </Section>
            <Section title="Proxy" Icon={Link}>
              <ToggleRow
                label="Use Proxy"
                value={Boolean(preferences.proxy_enabled)}
                onChange={(value) => { updatePreferences({ proxy_enabled: value }); setSaveState('idle'); }}
              />
              {preferences.proxy_enabled && (
                <div>
                  <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">Proxy URL</label>
                  <input
                    type="text"
                    value={preferences.proxy_url || ''}
                    onChange={(e) => { updatePreferences({ proxy_url: e.target.value }); setSaveState('idle'); }}
                    placeholder="http://127.0.0.1:8080"
                    className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors"
                  />
                  <p className="text-[10px] mt-1 text-[var(--md-sys-color-on-surface-variant)]">HTTP, HTTPS, and FTP proxies are supported by the bundled engine.</p>
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
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--md-sys-color-primary)]">Preferences</h3>
            <p className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] mt-1">Changes are persisted and applied to the bundled download engine.</p>
          </div>
          <button
            onClick={handleSave}
            disabled={loading || saveState === 'saving'}
            className="px-4 py-2 rounded-full text-xs font-semibold bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] hover:opacity-95 active-press transition-all cursor-pointer disabled:opacity-50"
          >
            {saveState === 'saving' ? 'Applying…' : 'Apply Settings'}
          </button>
        </div>

        <div className="flex gap-2 -mb-px">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                activeTab === id
                  ? 'border-[var(--md-sys-color-primary)] text-[var(--md-sys-color-primary)]'
                  : 'border-transparent text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:border-[var(--md-sys-color-outline-variant)]'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {statusMessage && (
        <div className={`mb-4 rounded-xl border px-3 py-2 text-xs ${
          saveState === 'error'
            ? 'bg-red-500/10 border-red-500/30 text-red-400'
            : saveState === 'saved'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-[var(--md-sys-color-surface-container-high)] border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)]'
        }`}>
          {statusMessage}
        </div>
      )}

      <div className="flex-1 overflow-y-auto pr-1">
        {loading ? (
          <div className="h-full flex items-center justify-center text-xs text-[var(--md-sys-color-on-surface-variant)]">Loading saved settings…</div>
        ) : renderTab()}
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

function DirectoryRow({ label, value, onChange, onBrowse }: { label: string; value: string; onChange: (value: string) => void; onBrowse: () => void }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">{label}</label>
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 min-w-0 bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors"
        />
        <button
          type="button"
          onClick={onBrowse}
          className="px-3 py-2 rounded-[var(--md-sys-shape-corner-medium)] border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container-high)] text-xs font-semibold text-[var(--md-sys-color-on-surface-variant)] hover:text-[var(--md-sys-color-on-surface)] hover:bg-[var(--md-sys-color-surface-container-highest)] cursor-pointer"
        >
          Browse
        </button>
      </div>
    </div>
  );
}

function ToggleRow({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) {
  return (
    <div className="flex items-center justify-between min-h-[36px]">
      <span className="text-xs text-[var(--md-sys-color-on-surface)]">{label}</span>
      <MdSwitch selected={value} onChange={onChange} />
    </div>
  );
}

function NumberRow({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--md-sys-color-on-surface-variant)] mb-1">{label}</label>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(clampInteger(parseInt(e.target.value, 10) || min, min, max))}
        className="w-full bg-[var(--md-sys-color-surface-container-high)] border border-[var(--md-sys-color-outline-variant)] rounded-[var(--md-sys-shape-corner-medium)] px-3 py-2 text-xs text-[var(--md-sys-color-on-surface)] focus:outline-none focus:border-[var(--md-sys-color-primary)] transition-colors"
      />
    </div>
  );
}
