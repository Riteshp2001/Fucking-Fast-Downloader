'use client';

import React, { useEffect, useState } from 'react';
import { load } from '@tauri-apps/plugin-store';
import Sidebar from './Sidebar';
import TitleBar from './TitleBar';
import UpdateBanner from '@/components/update/UpdateBanner';
import { useAppStore } from '@/stores/app-store';
import { isTauri } from '@/lib/tauri';

type StoredRecord = Record<string, unknown>;

interface AppLayoutProps {
  children: (props: { activeView: string; setActiveView: (view: string) => void }) => React.ReactNode;
}

function storedBoolean(record: StoredRecord, key: string, fallback: boolean): boolean {
  const value = record[key];
  return typeof value === 'boolean' ? value : fallback;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const [activeView, setActiveView] = useState('downloads');
  const appearance = useAppStore((state) => state.appearance);
  const setAppearance = useAppStore((state) => state.setAppearance);

  useEffect(() => {
    if (!isTauri()) return;
    let cancelled = false;

    const hydrateAppearance = async () => {
      try {
        const store = await load('config.json');
        const storedAppearance = await store.get<StoredRecord>('ffDownloaderAppearance') ?? {};
        const enginePreferences = await store.get<StoredRecord>('preferences') ?? {};
        if (cancelled) return;

        setAppearance({
          compact_mode: storedBoolean(storedAppearance, 'compact_mode', appearance.compact_mode),
          show_speed_graph: storedBoolean(storedAppearance, 'show_speed_graph', appearance.show_speed_graph),
          show_badges: storedBoolean(storedAppearance, 'show_badges', appearance.show_badges),
          minimize_to_tray: storedBoolean(
            enginePreferences,
            'minimizeToTrayOnClose',
            storedBoolean(storedAppearance, 'minimize_to_tray', appearance.minimize_to_tray),
          ),
        });
      } catch (error) {
        console.error('Failed to hydrate appearance settings:', error);
      }
    };

    void hydrateAppearance();
    return () => {
      cancelled = true;
    };
    // Hydrate once from the persisted Tauri store during shell startup.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col h-screen w-full overflow-hidden">
      <TitleBar />
      <UpdateBanner />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeView={activeView} onSelectView={setActiveView} />
        <main className={`flex-1 flex flex-col overflow-hidden ${appearance.compact_mode ? 'p-2' : 'p-4'}`}>
          {children({ activeView, setActiveView })}
        </main>
      </div>
    </div>
  );
}
