export interface Aria2Task {
  gid: string;
  status: 'active' | 'waiting' | 'paused' | 'error' | 'complete' | 'removed';
  title?: string;
  totalLength: string;
  completedLength: string;
  downloadSpeed: string;
  uploadSpeed: string;
  connections: string;
  dir: string;
  bittorrent?: {
    info?: {
      name?: string;
    };
  };
  files: Array<{
    completedLength: string;
    index: string;
    length: string;
    path: string;
    selected: string;
    uris: Array<{ status: string; uri: string }>;
  }>;
}

export interface Aria2GlobalStat {
  downloadSpeed: string;
  uploadSpeed: string;
  numActive: string;
  numWaiting: string;
  numStopped: string;
  numStoppedTotal: string;
}

export interface ScrapeResult {
  original_url: string;
  file_links: string[];
  resolved_links: ResolvedLink[];
}

export interface ResolvedLink {
  original: string;
  direct_url?: string;
  file_id?: string;
  file_name?: string;
  source_name?: string;
  success: boolean;
  error?: string;
}

export interface ScrapedItem {
  link: string;
  name: string;
  size: string;
  gid?: string;
  success: boolean;
  error?: string;
}

export interface DownloadTask extends Aria2Task {
  displayName: string;
  progress: number;
  speedFormatted: string;
  etaFormatted: string;
  sizeFormatted: string;
}
