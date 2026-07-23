'use client';
import { type ForwardRefExoticComponent, type RefAttributes, type SVGProps } from 'react';
import type { IconWeight } from '@solar-icons/react';

type SolarIcon = ForwardRefExoticComponent<Omit<SVGProps<SVGSVGElement> & {
  size?: number;
  weight?: IconWeight;
}, 'ref'> & RefAttributes<SVGSVGElement>>;

export function SIcon({ icon: Icon, size = 20, className = '', hover = true }: {
  icon: SolarIcon;
  size?: number;
  className?: string;
  hover?: boolean;
}) {
  if (!hover) {
    return <Icon size={size} weight="Linear" className={className} />;
  }
  return (
    <span className="relative inline-flex items-center justify-center align-middle leading-none">
      <Icon size={size} weight="Linear" className={`transition-all duration-200 ease-out group-hover:opacity-0 ${className}`} />
      <Icon size={size} weight="Bold" className={`absolute inset-0 transition-all duration-200 ease-out opacity-0 group-hover:opacity-100 ${className}`} />
    </span>
  );
}
