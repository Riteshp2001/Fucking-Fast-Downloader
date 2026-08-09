import { create } from 'zustand';
import type { Aria2Task, DownloadTask } from '@/types';
import { bytesToSize, formatSpeed, formatEta } from '@/lib/utils';

type FilterType = 'all' | 'active' | 'waiting' | 'stopped';

interface TaskState {
  tasks: DownloadTask[];
  filter: FilterType;
  searchQuery: string;
  selectedTask: DownloadTask | null;
  setTasks: (tasks: Aria2Task[]) => void;
  setFilter: (filter: FilterType) => void;
  setSearchQuery: (query: string) => void;
  setSelectedTask: (task: DownloadTask | null) => void;
  updateTask: (task: Aria2Task) => void;
  removeTask: (gid: string) => void;
  addTask: (task: Aria2Task) => void;
}

const mapTask = (task: Aria2Task): DownloadTask => {
  const displayName = task.bittorrent?.info?.name || task.title || task.files[0]?.path.split(/[\/\\]/).pop() || 'Unknown';
  const total = BigInt(task.totalLength || '0');
  const completed = BigInt(task.completedLength || '0');
  const progress = total > 0 ? Number((completed * BigInt(100)) / total) : 0;

  return {
    ...task,
    displayName,
    progress,
    speedFormatted: formatSpeed(task.downloadSpeed),
    etaFormatted: formatEta(task.totalLength, task.completedLength, task.downloadSpeed),
    sizeFormatted: bytesToSize(task.totalLength),
  };
};

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  filter: 'all',
  searchQuery: '',
  selectedTask: null,
  setTasks: (ariaTasks) => set((state) => {
    const tasks = ariaTasks.map(mapTask);
    const selectedTask = state.selectedTask
      ? tasks.find((task) => task.gid === state.selectedTask?.gid) ?? null
      : null;

    return { tasks, selectedTask };
  }),
  setFilter: (filter) => set({ filter }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setSelectedTask: (selectedTask) => set({ selectedTask }),
  updateTask: (task) => set((state) => {
    const updated = mapTask(task);
    return {
      tasks: state.tasks.map((current) => current.gid === task.gid ? updated : current),
      selectedTask: state.selectedTask?.gid === task.gid ? updated : state.selectedTask,
    };
  }),
  removeTask: (gid) => set((state) => ({
    tasks: state.tasks.filter((task) => task.gid !== gid),
    selectedTask: state.selectedTask?.gid === gid ? null : state.selectedTask,
  })),
  addTask: (task) => set((state) => {
    if (state.tasks.some((current) => current.gid === task.gid)) return state;
    return { tasks: [...state.tasks, mapTask(task)] };
  }),
}));
