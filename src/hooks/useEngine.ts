import { useCallback, useEffect, useRef } from 'react';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { useAppStore } from '@/stores/app-store';
import { isTauri, restartEngine, startEngine, stopEngine, waitForEngine } from '@/lib/tauri';

type EngineOperation = 'start' | 'restart';

const MAX_AUTOMATIC_RECOVERY_ATTEMPTS = 2;

export const useEngine = () => {
  const setEngineStatus = useAppStore((state) => state.setEngineStatus);
  const operationRef = useRef<Promise<boolean> | null>(null);
  const recoveryAttemptsRef = useRef(0);

  const bringEngineOnline = useCallback(async (operation: EngineOperation): Promise<boolean> => {
    if (!isTauri()) return false;
    if (operationRef.current) return operationRef.current;

    const run = (async () => {
      setEngineStatus('starting');
      try {
        if (operation === 'restart') {
          await restartEngine();
        } else {
          await startEngine();
        }

        const ready = await waitForEngine();
        if (!ready) {
          throw new Error('The download engine started but its RPC endpoint never became ready.');
        }

        recoveryAttemptsRef.current = 0;
        setEngineStatus('running');
        return true;
      } catch (error) {
        console.error(`Failed to ${operation} download engine:`, error);
        setEngineStatus('error');
        return false;
      } finally {
        operationRef.current = null;
      }
    })();

    operationRef.current = run;
    return run;
  }, [setEngineStatus]);

  // Cold start only. Do not key this effect off `engineStatus`: doing that makes
  // an intentional stop immediately start the engine again.
  useEffect(() => {
    if (!isTauri()) return;
    void bringEngineOnline('start');
  }, [bringEngineOnline]);

  useEffect(() => {
    if (!isTauri()) return;

    let disposed = false;
    const unlisteners: UnlistenFn[] = [];

    const setupListeners = async () => {
      try {
        const crashUnlisten = await listen('engine-crashed', () => {
          if (disposed) return;

          setEngineStatus('error');
          if (recoveryAttemptsRef.current >= MAX_AUTOMATIC_RECOVERY_ATTEMPTS) {
            console.error('Download engine recovery stopped after repeated crashes.');
            return;
          }

          recoveryAttemptsRef.current += 1;
          void bringEngineOnline('restart');
        });
        if (disposed) crashUnlisten(); else unlisteners.push(crashUnlisten);

        const stoppedUnlisten = await listen('engine-stopped', () => {
          if (!disposed && !operationRef.current) {
            setEngineStatus('stopped');
          }
        });
        if (disposed) stoppedUnlisten(); else unlisteners.push(stoppedUnlisten);

        const recoveredUnlisten = await listen('engine-recovered', async () => {
          if (disposed) return;
          try {
            const ready = await waitForEngine();
            if (!disposed) setEngineStatus(ready ? 'running' : 'error');
          } catch (error) {
            console.error('Failed to verify recovered download engine:', error);
            if (!disposed) setEngineStatus('error');
          }
        });
        if (disposed) recoveredUnlisten(); else unlisteners.push(recoveredUnlisten);
      } catch (error) {
        console.error('Failed to set up engine lifecycle listeners:', error);
      }
    };

    void setupListeners();

    return () => {
      disposed = true;
      for (const unlisten of unlisteners) unlisten();
    };
  }, [bringEngineOnline, setEngineStatus]);

  return {
    start: async () => {
      recoveryAttemptsRef.current = 0;
      return bringEngineOnline('start');
    },
    stop: async () => {
      if (!isTauri()) return;
      try {
        await stopEngine();
        setEngineStatus('stopped');
      } catch (error) {
        console.error('Failed to stop download engine:', error);
        setEngineStatus('error');
      }
    },
    restart: async () => {
      recoveryAttemptsRef.current = 0;
      return bringEngineOnline('restart');
    },
  };
};
