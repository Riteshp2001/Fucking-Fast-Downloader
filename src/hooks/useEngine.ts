import { useEffect } from 'react';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { useAppStore } from '@/stores/app-store';
import { startEngine, stopEngine, restartEngine, isTauri, EVENTS } from '@/lib/tauri';

export const useEngine = () => {
  const setEngineStatus = useAppStore((state) => state.setEngineStatus);
  const engineStatus = useAppStore((state) => state.engineStatus);

  useEffect(() => {
    if (!isTauri()) return;

    let unlisten: UnlistenFn | undefined;

    const setupListener = async () => {
      try {
        unlisten = await listen<{ status: 'stopped' | 'starting' | 'running' | 'error' }>(EVENTS.ENGINE_STATUS, (event) => {
          setEngineStatus(event.payload.status);
        });
      } catch (error) {
        console.error('Failed to set up engine listener:', error);
      }
    };

    setupListener();

    return () => {
      if (unlisten) unlisten();
    };
  }, [setEngineStatus]);

  useEffect(() => {
    if (isTauri() && engineStatus === 'stopped') {
      const initEngine = async () => {
        setEngineStatus('starting');
        try {
          await startEngine();
        } catch (error) {
          console.error('Failed to start engine:', error);
          setEngineStatus('error');
        }
      };
      
      initEngine();
    }
  }, [engineStatus, setEngineStatus]);

  return {
    start: async () => {
      setEngineStatus('starting');
      try {
        await startEngine();
        setEngineStatus('running');
      } catch {
        setEngineStatus('error');
      }
    },
    stop: async () => {
      try {
        await stopEngine();
        setEngineStatus('stopped');
      } catch (error) {
        console.error('Failed to stop engine:', error);
      }
    },
    restart: async () => {
      setEngineStatus('starting');
      try {
        await restartEngine();
        setEngineStatus('running');
      } catch {
        setEngineStatus('error');
      }
    }
  };
};
