import { useEffect } from 'react';
import { useAppStore } from '@/stores/app-store';
import { useTaskStore } from '@/stores/task-store';
import { fetchAllTasks, fetchGlobalStat, isTauri } from '@/lib/tauri';

export const useTaskPolling = () => {
  const engineStatus = useAppStore((state) => state.engineStatus);
  const setStats = useAppStore((state) => state.setStats);
  const setTasks = useTaskStore((state) => state.setTasks);

  useEffect(() => {
    if (engineStatus !== 'running' || !isTauri()) return;

    let mounted = true;

    const poll = async () => {
      try {
        const [tasks, stat] = await Promise.all([
          fetchAllTasks(),
          fetchGlobalStat(),
        ]);

        if (mounted) {
          if (tasks) setTasks(tasks);
          if (stat) {
            setStats({
              downloadSpeed: stat.downloadSpeed,
              uploadSpeed: stat.uploadSpeed,
              activeCount: parseInt(stat.numActive, 10) || 0,
              waitingCount: parseInt(stat.numWaiting, 10) || 0,
              stoppedCount: parseInt(stat.numStoppedTotal, 10) || 0,
            });
          }
        }
      } catch (error) {
        console.error('Failed to poll tasks:', error);
      }
    };

    poll();
    const interval = setInterval(poll, 2000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [engineStatus, setTasks, setStats]);
};
