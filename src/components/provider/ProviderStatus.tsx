'use client';

import React from 'react';
import type { ProviderStatus as ProviderStatusType } from '@/types/provider';

interface Props {
  providers: ProviderStatusType[];
}

export default function ProviderStatus({ providers }: Props) {
  return (
    <div className="space-y-1">
      {providers.map((p) => (
        <div key={p.name} className="flex items-center gap-2 px-2 py-1 rounded-lg text-[10px]">
          <span className={`w-1.5 h-1.5 rounded-full ${p.enabled ? 'bg-teal-400' : 'bg-red-400'}`} />
          <span className="text-[var(--md-sys-color-on-surface-variant)] capitalize">{p.name}</span>
          {p.error && <span className="text-red-400 truncate">{p.error}</span>}
        </div>
      ))}
    </div>
  );
}
