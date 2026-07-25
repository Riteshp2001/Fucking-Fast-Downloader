import { invoke } from '@tauri-apps/api/core';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { Aria2GlobalStat, Aria2Task } from '@/types';
import type { SearchResult, GameDetail, ProviderStatus } from '@/types/provider';

export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

// Engine commands
export const startEngine = async () => isTauri() && invoke('start_engine_command');
export const stopEngine = async () => isTauri() && invoke('stop_engine_command');
export const restartEngine = async () => isTauri() && invoke('restart_engine_command');

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

export const addUri = async (uri: string, options?: Record<string, unknown>) =>
  isTauri() && invoke('aria2_add_uri', { uris: [uri], options: options || {} });

export const pauseTask = async (gid: string) => isTauri() && invoke('aria2_pause', { gid });
export const unpauseTask = async (gid: string) => isTauri() && invoke('aria2_unpause', { gid });
export const removeTask = async (gid: string) => isTauri() && invoke('aria2_force_remove', { gid });
export const pauseAll = async () => isTauri() && invoke('aria2_pause_all');
export const unpauseAll = async () => isTauri() && invoke('aria2_unpause_all');

// Config commands
export const getSystemConfig = async (): Promise<Record<string, unknown>> =>
  isTauri() ? invoke<Record<string, unknown>>('get_system_config') : {};

export const saveSystemConfig = async (config: Record<string, unknown>) =>
  isTauri() && invoke('save_system_config', { config });

// Provider commands
export const listProviders = async (): Promise<ProviderStatus[]> =>
  isTauri() ? invoke<ProviderStatus[]>('list_providers') : [];

export const searchProvider = async (provider: string, query: string): Promise<SearchResult[]> =>
  isTauri() ? invoke<SearchResult[]>('search_provider', { provider, query }) : [];

export const fetchGameDetail = async (provider: string, url: string): Promise<GameDetail> =>
  isTauri()
    ? invoke<GameDetail>('fetch_game_detail', { provider, url })
    : { title: '', images: [], description: '', features: [], dlcs: [], magnet_links: [], direct_links: [], raw_fuckingfast_links: [] };

export const resolveFuckingFastLink = async (url: string): Promise<string> =>
  isTauri() ? invoke<string>('resolve_fuckingfast_link', { url }) : url;

export const solveProviderCaptcha = async (provider: string, url: string) =>
  isTauri() && invoke('solve_provider_captcha', { provider, url });

// Events
export const onEngineEvent = async (callback: (payload: unknown) => void): Promise<UnlistenFn | null> => {
  if (!isTauri()) return null;
  return listen('engine-event', (event) => callback(event.payload));
};

export const EVENTS = {
  ENGINE_STATUS: 'engine-status',
  STAT_UPDATE: 'stat:update',
  TASK_COMPLETE: 'task-monitor:complete',
  TASK_ERROR: 'task-monitor:error',
};
