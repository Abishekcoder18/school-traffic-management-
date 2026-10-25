import React from 'react';
import { TrafficMetric } from '../types';

interface MetricCardProps {
  metric: TrafficMetric;
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({ metric, icon }) => {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs transition-all hover:border-slate-300">
      <div className="flex items-center justify-between gap-3 mb-3">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          {metric.label}
        </span>
        {icon && <div className="text-slate-400 shrink-0">{icon}</div>}
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-2xl font-bold text-slate-900 tabular-nums">
          {metric.value}
        </span>
      </div>

      <p className="mt-2 text-xs text-slate-500">Synthetic scenario baseline</p>
    </div>
  );
};
