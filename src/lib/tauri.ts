import { getVersion } from '@tauri-apps/api/app';
import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { readText } from '@tauri-apps/plugin-clipboard-manager';
import type { Aria2GlobalStat, Aria2Task } from '@/types';
import type { SearchResult, GameDetail, ProviderStatus } from '@/types/provider';

export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

function requireTauri(feature: string): void {
  if (!isTauri()) {
    throw new Error(`${feature} is only available in the desktop application.`);
  }
}

// Engine commands
export const startEngine = async (): Promise<void> => {
  requireTauri('The download engine');
  await invoke('start_engine_command');
};

export const stopEngine = async (): Promise<void> => {
  requireTauri('The download engine');
  await invoke('stop_engine_command');
};

export const restartEngine = async (): Promise<void> => {
  requireTauri('The download engine');
  await invoke('restart_engine_command');
};

/**
 * Wait until the bundled aria2 sidecar is accepting RPC requests.
 *
 * The Rust command also refreshes RPC credentials and synchronizes runtime
 * options. A successful process spawn is therefore not considered "running"
 * until this returns true.
 */
export const waitForEngine = async (): Promise<boolean> => {
  requireTauri('The download engine');
  return invoke<boolean>('wait_for_engine');
};

// Aria2 commands (forwarded through Rust backend)
export const fetchGlobalStat = async (): Promise<Aria2GlobalStat | null> =>
  isTauri() ? invoke<Aria2GlobalStat>('aria2_get_global_stat') : null;

export const fetchActiveTasks = async (): Promise<Aria2Task[]> =>
  isTauri() ? invoke<Aria2Task[]>('aria2_fetch_active_task_list') : [];

export const fetchAllTasks = async (): Promise<Aria2Task[]> =>
  isTauri()
    ? Promise.all([
        invoke<Aria2Task[]>('aria2_fetch_task_list', { type: 'active', limit: 1000 }),
        invoke<Aria2Task[]>('aria2_fetch_task_list', { type: 'stopped', limit: 1000 }),
      ]).then(([active, stopped]) => [...active, ...stopped])
    : [];

export const addUri = async (
  uri: string,
  options: Record<string, unknown> = {},
): Promise<string> => {
  requireTauri('Downloads');
  return invoke<string>('aria2_add_uri', { uris: [uri], options });
};

export const addTorrent = async (
  torrentBase64: string,
  options: Record<string, unknown> = {},
): Promise<string> => {
  requireTauri('Torrent import');
  return invoke<string>('aria2_add_torrent', { torrent: torrentBase64, options });
};

export const changeTaskOptions = async (
  gid: string,
  options: Record<string, unknown>,
): Promise<string> => {
  requireTauri('Task options');
  return invoke<string>('aria2_change_option', { gid, options });
};

/**
 * Select and prioritize one BitTorrent file and return a loopback-only HTTP
 * Range URL backed by verified aria2 pieces. The backend does not expose an
 * arbitrary filesystem path: it resolves the file from aria2's own task state.
 */
export const prepareTorrentStream = async (gid: string, fileIndex: string): Promise<string> =>
  changeTaskOptions(gid, { '__ff-stream-file': fileIndex });

export const pauseTask = async (gid: string): Promise<string> => {
  requireTauri('Task controls');
  return invoke<string>('aria2_pause', { gid });
};

export const unpauseTask = async (gid: string): Promise<string> => {
  requireTauri('Task controls');
  return invoke<string>('aria2_unpause', { gid });
};

/**
 * Active/waiting/paused tasks must be removed from the live queue, while
 * completed/error tasks are aria2 download-result records and need the
 * dedicated removeDownloadResult RPC call.
 */
export const removeTask = async (gid: string, status?: Aria2Task['status']): Promise<string> => {
  requireTauri('Task controls');
  if (status === 'complete' || status === 'error' || status === 'removed') {
    return invoke<string>('aria2_remove_download_result', { gid });
  }
  return invoke<string>('aria2_force_remove', { gid });
};

export const pauseAll = async (): Promise<string> => {
  requireTauri('Task controls');
  return invoke<string>('aria2_pause_all');
};

export const unpauseAll = async (): Promise<string> => {
  requireTauri('Task controls');
  return invoke<string>('aria2_unpause_all');
};

// Config commands
export const getSystemConfig = async (): Promise<Record<string, unknown>> =>
  isTauri() ? invoke<Record<string, unknown>>('get_system_config') : {};

export const saveSystemConfig = async (config: Record<string, unknown>): Promise<void> => {
  requireTauri('Settings persistence');
  await invoke('save_system_config', { config });
};

// Desktop utilities
export const readClipboardText = async (): Promise<string> => {
  if (isTauri()) {
    return readText();
  }

  if (typeof navigator !== 'undefined' && navigator.clipboard?.readText) {
    return navigator.clipboard.readText();
  }

  throw new Error('Clipboard access is unavailable in this environment.');
};

export const getAppVersion = async (): Promise<string> => {
  if (!isTauri()) return 'dev';
  return getVersion();
};

// Provider commands
export const listProviders = async (): Promise<ProviderStatus[]> =>
  isTauri() ? invoke<ProviderStatus[]>('list_providers') : [];

export const searchProvider = async (provider: string, query: string): Promise<SearchResult[]> =>
  isTauri() ? invoke<SearchResult[]>('search_provider', { provider, query }) : [];

export const fetchGameDetail = async (provider: string, url: string): Promise<GameDetail> =>
  isTauri()
    ? invoke<GameDetail>('fetch_game_detail', { provider, url })
    : {
        title: '',
        images: [],
        description: '',
        features: [],
        dlcs: [],
        magnet_links: [],
        direct_links: [],
        raw_fuckingfast_links: [],
      };

export const resolveFuckingFastLink = async (url: string): Promise<string> =>
  isTauri() ? invoke<string>('resolve_fuckingfast_link', { url }) : url;

export const solveProviderCaptcha = async (provider: string, url: string) =>
  isTauri() && invoke('solve_provider_captcha', { provider, url });

// Events
export const onEngineEvent = async (
  callback: (payload: unknown) => void,
): Promise<UnlistenFn | null> => {
  if (!isTauri()) return null;
  return listen('engine-event', (event) => callback(event.payload));
};

export const EVENTS = {
  ENGINE_STATUS: 'engine-status',
  STAT_UPDATE: 'stat:update',
  TASK_COMPLETE: 'task-monitor:complete',
  TASK_ERROR: 'task-monitor:error',
};
