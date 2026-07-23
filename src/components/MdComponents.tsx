'use client';

import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'filled' | 'outlined' | 'ghost';
  children?: React.ReactNode;
}

export function MdFilledButton({ children, className = '', disabled, onClick, ...props }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold rounded-full bg-[var(--md-sys-color-primary)] text-[var(--md-sys-color-on-primary)] shadow-sm hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition-all duration-150 cursor-pointer ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function MdOutlinedButton({ children, className = '', disabled, onClick, ...props }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold rounded-full border border-[var(--md-sys-color-outline)] text-[var(--md-sys-color-primary)] hover:bg-[var(--md-sys-color-primary-container)]/20 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition-all duration-150 cursor-pointer ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function MdIconButton({ children, className = '', disabled, onClick, title, ...props }: ButtonProps & { title?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={title}
      className={`w-8 h-8 rounded-full flex items-center justify-center text-[var(--md-sys-color-on-surface-variant)] hover:bg-[var(--md-sys-color-surface-container-highest)] hover:text-[var(--md-sys-color-on-surface)] active:scale-95 disabled:opacity-40 transition-all duration-150 cursor-pointer ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function MdSwitch({ selected, onChange }: { selected?: boolean; onChange?: (val: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={selected}
      onClick={() => onChange?.(!selected)}
      className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 cursor-pointer ${
        selected ? 'bg-[var(--md-sys-color-primary)] justify-end' : 'bg-[var(--md-sys-color-surface-container-highest)] border border-[var(--md-sys-color-outline)] justify-start'
      }`}
    >
      <span className={`w-4 h-4 rounded-full transition-transform duration-200 ${selected ? 'bg-[var(--md-sys-color-on-primary)]' : 'bg-[var(--md-sys-color-outline)]'}`} />
    </button>
  );
}
