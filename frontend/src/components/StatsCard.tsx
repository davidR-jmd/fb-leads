import React from 'react';
import { cn } from '../lib/utils';

/**
 * StatsCard component
 * Single Responsibility: Only displays a single statistic
 * Interface Segregation: Simple props, no unnecessary dependencies
 */
interface StatsCardProps {
  title: string;
  value: string | number;
  className?: string;
}

export default function StatsCard({ title, value, className }: StatsCardProps) {
  return (
    <div className={cn('bg-white rounded-lg border border-slate-200 p-6', className)}>
      <p className="text-sm text-slate-500 mb-2">{title}</p>
      <p className="text-4xl font-semibold text-slate-800">{value}</p>
    </div>
  );
}
