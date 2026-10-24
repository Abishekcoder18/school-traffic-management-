import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { TrafficMetric } from '../types';

interface MetricCardProps {
  metric: TrafficMetric;
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({ metric, icon }) => {
  const isAlert = metric.status === 'alert';
  const isWarning = metric.status === 'warning';

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

      <div className="flex items-center gap-1.5 text-xs">
        {metric.trend === 'up' && (
          <TrendingUp
            className={`w-3.5 h-3.5 ${
              isAlert ? 'text-red-600' : isWarning ? 'text-amber-600' : 'text-blue-600'
            }`}
          />
        )}
        {metric.trend === 'down' && (
          <TrendingDown className="w-3.5 h-3.5 text-green-600" />
        )}
        {metric.trend === 'neutral' && (
          <Minus className="w-3.5 h-3.5 text-slate-400" />
        )}

        <span
          className={`font-medium ${
            isAlert
              ? 'text-red-600'
              : isWarning
              ? 'text-amber-600'
              : 'text-slate-600'
          }`}
        >
          {metric.change}
        </span>
      </div>

      <p className="mt-2 text-xs text-slate-500 line-clamp-1">
        {metric.description}
      </p>
    </div>
  );
};
