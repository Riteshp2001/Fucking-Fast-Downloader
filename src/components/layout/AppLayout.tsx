'use client';

import React, { useState } from 'react';
import Sidebar from './Sidebar';
import TitleBar from './TitleBar';
import UpdateBanner from '@/components/update/UpdateBanner';

interface AppLayoutProps {
  children: (props: { activeView: string; setActiveView: (view: string) => void }) => React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const [activeView, setActiveView] = useState('downloads');

  return (
    <div className="flex flex-col h-screen w-full overflow-hidden">
      <TitleBar />
      <UpdateBanner />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeView={activeView} onSelectView={setActiveView} />
        <main className="flex-1 flex flex-col overflow-hidden p-4">
          {children({ activeView, setActiveView })}
        </main>
      </div>
    </div>
  );
}
