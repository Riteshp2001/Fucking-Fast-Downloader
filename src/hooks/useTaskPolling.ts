import { useEffect } from 'react';
import { useAppStore } from '@/stores/app-store';
import { useTaskStore } from '@/stores/task-store';
import { fetchAllTasks, fetchGlobalStat, isTauri } from '@/lib/tauri';
import { formatSpeed } from '@/lib/utils';

export const useTaskPolling = () => {
  const engineStatus = useAppStore((state) => state.engineStatus);
  const setStats = useAppStore((state) => state.setStats);
  const setTasks = useTaskStore((state) => state.setTasks);

  useEffect(() => {
    if (engineStatus !== 'running' || !isTauri()) return;

    let mounted = true;
    let inFlight = false;

    const poll = async () => {
      if (inFlight) return;
      inFlight = true;

      try {
        const [tasks, stat] = await Promise.all([
          fetchAllTasks(),
          fetchGlobalStat(),
        ]);

        if (mounted) {
          setTasks(tasks);
          if (stat) {
            setStats({
              downloadSpeed: formatSpeed(stat.downloadSpeed),
              uploadSpeed: formatSpeed(stat.uploadSpeed),
              activeCount: parseInt(stat.numActive, 10) || 0,
              waitingCount: parseInt(stat.numWaiting, 10) || 0,
              stoppedCount: parseInt(stat.numStoppedTotal, 10) || 0,
            });
          }
        }
      } catch (error) {
        console.error('Failed to poll tasks:', error);
      } finally {
        inFlight = false;
      }
    };

    void poll();
    const interval = window.setInterval(() => void poll(), 2000);

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, [engineStatus, setTasks, setStats]);
};
