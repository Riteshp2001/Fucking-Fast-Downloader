import { invoke } from '@tauri-apps/api/core';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { Aria2GlobalStat, Aria2Task, ScrapeResult, ResolvedLink, ScrapedItem } from '@/types';

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

// Scraper commands
export const scrapeFitgirlPage = async (url: string): Promise<ScrapeResult | null> =>
  isTauri() ? invoke<ScrapeResult>('scrape_fitgirl_page', { url }) : null;

export const resolveFuckingfastLink = async (link: string): Promise<ResolvedLink | null> =>
  isTauri() ? invoke<ResolvedLink>('resolve_fuckingfast_link', { link }) : null;

export const scrapeAndResolve = async (url: string): Promise<ScrapeResult | null> =>
  isTauri() ? invoke<ScrapeResult>('scrape_and_resolve', { url }) : null;

export const scraperFind = async (url: string): Promise<ScrapedItem[]> => {
  if (!isTauri()) throw new Error('The scraper is available only in the desktop app.');

  const result = await invoke<ScrapeResult>('scrape_and_resolve', { url });
  return result.file_links.map((link, index) => {
    const resolved = result.resolved_links[index];
    const name = resolved?.file_name || resolved?.source_name || resolved?.file_id || `Part ${index + 1}`;
    const directUrl = resolved?.direct_url;
    return {
      link: directUrl || link,
      name,
      size: directUrl ? 'Ready to download' : 'Could not resolve',
      gid: resolved?.file_id || link,
      success: Boolean(resolved?.success && directUrl),
      error: resolved?.error || (!directUrl ? 'No direct download URL was returned.' : undefined),
    };
  });
};

export const scraperAddTask = async (item: ScrapedItem) => {
  if (!isTauri()) return;
  if (!item.success || !item.link) throw new Error(item.error || 'This link could not be resolved.');
  await invoke('aria2_add_uri', { uris: [item.link], options: { out: item.name } });
};

// Config commands
export const getSystemConfig = async (): Promise<Record<string, unknown>> =>
  isTauri() ? invoke<Record<string, unknown>>('get_system_config') : {};

export const saveSystemConfig = async (config: Record<string, unknown>) =>
  isTauri() && invoke('save_system_config', { config });

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
