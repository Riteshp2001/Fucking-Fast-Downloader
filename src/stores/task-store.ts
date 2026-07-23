import { create } from 'zustand';
import { Aria2Task, DownloadTask } from '@/types';
import { bytesToSize, formatSpeed, formatEta, formatProgress } from '@/lib/utils';

type FilterType = 'all' | 'active' | 'waiting' | 'stopped';

interface TaskState {
  tasks: DownloadTask[];
  filter: FilterType;
  selectedTask: DownloadTask | null;
  setTasks: (tasks: Aria2Task[]) => void;
  setFilter: (filter: FilterType) => void;
  setSelectedTask: (task: DownloadTask | null) => void;
  updateTask: (task: Aria2Task) => void;
  removeTask: (gid: string) => void;
  addTask: (task: Aria2Task) => void;
}

const mapTask = (task: Aria2Task): DownloadTask => {
  const displayName = task.bittorrent?.info?.name || task.title || task.files[0]?.path.split(/[\/\\]/).pop() || 'Unknown';
  return {
    ...task,
    displayName,
    progress: formatProgress(task.completedLength, task.totalLength),
    speedFormatted: formatSpeed(task.downloadSpeed),
    etaFormatted: formatEta(task.totalLength, task.completedLength, task.downloadSpeed),
    sizeFormatted: bytesToSize(task.totalLength)
  };
};

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  filter: 'all',
  selectedTask: null,
  setTasks: (ariaTasks) => set({ tasks: ariaTasks.map(mapTask) }),
  setFilter: (filter) => set({ filter }),
  setSelectedTask: (selectedTask) => set({ selectedTask }),
  updateTask: (task) => set((state) => ({
    tasks: state.tasks.map((t) => t.gid === task.gid ? mapTask(task) : t)
  })),
  removeTask: (gid) => set((state) => ({
    tasks: state.tasks.filter((t) => t.gid !== gid),
    selectedTask: state.selectedTask?.gid === gid ? null : state.selectedTask
  })),
  addTask: (task) => set((state) => {
    if (state.tasks.some(t => t.gid === task.gid)) return state;
    return { tasks: [...state.tasks, mapTask(task)] };
  }),
}));
