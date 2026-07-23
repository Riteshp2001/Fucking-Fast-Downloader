import { create } from 'zustand';

type EngineStatus = 'stopped' | 'starting' | 'running' | 'error';
type Theme = 'dark' | 'light';

interface Preferences {
  download_dir: string;
  temp_dir: string;
  max_concurrent_downloads: number;
  max_connections_per_server: number;
  aria2_enable_rpc_auth: boolean;
  aria2_rpc_secret?: string;
  proxy_enabled?: boolean;
  proxy_url?: string;
}

interface Appearance {
  compact_mode: boolean;
  show_speed_graph: boolean;
  show_badges: boolean;
  minimize_to_tray: boolean;
}

interface AppState {
  engineStatus: EngineStatus;
  downloadSpeed: string;
  uploadSpeed: string;
  activeCount: number;
  waitingCount: number;
  stoppedCount: number;
  theme: Theme;
  sidebarCollapsed: boolean;
  preferences: Preferences;
  appearance: Appearance;
  setEngineStatus: (status: EngineStatus) => void;
  setStats: (stats: { downloadSpeed: string; uploadSpeed: string; activeCount: number; waitingCount: number; stoppedCount: number }) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  updatePreferences: (partial: Partial<Preferences>) => void;
  setAppearance: (partial: Partial<Appearance>) => void;
}

const defaultPreferences: Preferences = {
  download_dir: '',
  temp_dir: '',
  max_concurrent_downloads: 5,
  max_connections_per_server: 16,
  aria2_enable_rpc_auth: false,
};

const defaultAppearance: Appearance = {
  compact_mode: false,
  show_speed_graph: true,
  show_badges: true,
  minimize_to_tray: true,
};

export const useAppStore = create<AppState>((set) => ({
  engineStatus: 'stopped',
  downloadSpeed: '0',
  uploadSpeed: '0',
  activeCount: 0,
  waitingCount: 0,
  stoppedCount: 0,
  theme: 'dark',
  sidebarCollapsed: false,
  preferences: defaultPreferences,
  appearance: defaultAppearance,
  setEngineStatus: (status) => set({ engineStatus: status }),
  setStats: (stats) => set(stats),
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  updatePreferences: (partial) => set((state) => ({ preferences: { ...state.preferences, ...partial } })),
  setAppearance: (partial) => set((state) => ({ appearance: { ...state.appearance, ...partial } })),
}));
