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
  errorCode?: string;
  errorMessage?: string;
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

export interface DownloadTask extends Aria2Task {
  displayName: string;
  progress: number;
  speedFormatted: string;
  etaFormatted: string;
  sizeFormatted: string;
}

export interface UpdateMetadata {
  version: string;
  body?: string;
  date?: string;
  channel: string;
  requestedChannel: string;
  isRollback: boolean;
}

export type UpdateProgressPayload =
  | { event: "Started"; data: { content_length: number } }
  | { event: "Progress"; data: { chunk_length: number; downloaded: number } }
  | { event: "Finished"; data: null };
