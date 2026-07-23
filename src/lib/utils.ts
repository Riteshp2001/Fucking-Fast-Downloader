import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function bytesToSize(bytes: number | string): string {
  const b = typeof bytes === 'string' ? parseInt(bytes, 10) : bytes;
  if (isNaN(b) || b === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return parseFloat((b / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatSpeed(bytesPerSecond: number | string): string {
  const b = typeof bytesPerSecond === 'string' ? parseInt(bytesPerSecond, 10) : bytesPerSecond;
  if (isNaN(b) || b === 0) return '0 B/s';
  const k = 1024;
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return parseFloat((b / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatEta(totalBytes: number | string, completedBytes: number | string, speed: number | string): string {
  const t = typeof totalBytes === 'string' ? parseInt(totalBytes, 10) : totalBytes;
  const c = typeof completedBytes === 'string' ? parseInt(completedBytes, 10) : completedBytes;
  const s = typeof speed === 'string' ? parseInt(speed, 10) : speed;
  
  if (isNaN(t) || isNaN(c) || isNaN(s) || s === 0) return '∞';
  if (c >= t) return '0s';
  
  const remainingBytes = t - c;
  const remainingSeconds = Math.floor(remainingBytes / s);
  
  const h = Math.floor(remainingSeconds / 3600);
  const m = Math.floor((remainingSeconds % 3600) / 60);
  const secs = remainingSeconds % 60;
  
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${secs}s`;
  return `${secs}s`;
}

export function formatProgress(completed: number | string, total: number | string): number {
  const c = typeof completed === 'string' ? parseInt(completed, 10) : completed;
  const t = typeof total === 'string' ? parseInt(total, 10) : total;
  
  if (isNaN(c) || isNaN(t) || t === 0) return 0;
  if (c >= t) return 100;
  return Math.floor((c / t) * 10000) / 100;
}
