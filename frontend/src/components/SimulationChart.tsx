import React from 'react';
import type { TimeInterval } from '../api/client';

interface SimulationChartProps {
  timeIntervals: TimeInterval[];
}

export const SimulationChart: React.FC<SimulationChartProps> = ({ timeIntervals }) => {
  const maxVehicleScale = 60; // Max Y-axis scale

  if (!timeIntervals || timeIntervals.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h3 className="text-sm font-bold text-slate-900">
            Queue Length Over Dismissal Period (Baseline vs. Candidate)
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Simulated intervals evaluating peak queue against campus physical perimeter limit (Deterministic Estimate)
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-xs bg-slate-300"></span>
            <span className="text-slate-600">Baseline (Current)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-xs bg-blue-600"></span>
            <span className="text-slate-900 font-medium">Candidate (Optimized)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-0.5 bg-red-500 border-t border-dashed border-red-500"></span>
            <span className="text-red-600 font-medium">35-Car Spillback Threshold</span>
          </div>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="relative pt-6 pb-2">
        {/* Horizontal Threshold Line (35 vehicles) */}
        <div
          className="absolute left-12 right-0 border-t-2 border-dashed border-red-400 z-10 pointer-events-none flex items-center justify-end pr-2"
          style={{
            bottom: `${((35 / maxVehicleScale) * 100) * 0.75 + 18}%`
          }}
        >
          <span className="text-[10px] bg-red-50 text-red-700 px-1.5 py-0.5 rounded font-bold border border-red-200">
            Perimeter Storage Limit: 35 Cars
          </span>
        </div>

        {/* Bars Container */}
        <div className={`grid gap-2 sm:gap-6 pl-10 pr-2 h-56 items-end border-b border-l border-slate-200`}
             style={{ gridTemplateColumns: `repeat(${timeIntervals.length}, minmax(0, 1fr))` }}>
          {timeIntervals.map((interval) => {
            const baselineHeightPct = (interval.baselineQueue / maxVehicleScale) * 100;
            const candidateHeightPct = (interval.candidateQueue / maxVehicleScale) * 100;
            const isBaselineOverflow = interval.baselineQueue > 35;

            return (
              <div
                key={interval.time}
                className="flex flex-col items-center h-full justify-end group relative"
              >
                {/* Visual tooltip on hover */}
                <div className="absolute -top-12 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900 text-white text-[10px] rounded px-2 py-1 pointer-events-none whitespace-nowrap z-20 shadow-md">
                  <div>Baseline: {interval.baselineQueue} veh</div>
                  <div>Candidate: {interval.candidateQueue} veh</div>
                </div>

                <div className="w-full flex items-end justify-center gap-1 sm:gap-2 h-full pb-1">
                  {/* Baseline Bar */}
                  <div className="w-1/2 max-w-[28px] flex flex-col items-center justify-end h-full">
                    <span className="text-[10px] text-slate-500 font-medium tabular-nums mb-1">
                      {interval.baselineQueue}
                    </span>
                    <div
                      className={`w-full rounded-t-sm transition-all duration-300 ${
                        isBaselineOverflow ? 'bg-red-400' : 'bg-slate-300'
                      }`}
                      style={{ height: `${Math.min(baselineHeightPct, 100)}%` }}
                    />
                  </div>

                  {/* Candidate Bar */}
                  <div className="w-1/2 max-w-[28px] flex flex-col items-center justify-end h-full">
                    <span className="text-[10px] text-blue-700 font-bold tabular-nums mb-1">
                      {interval.candidateQueue}
                    </span>
                    <div
                      className="w-full rounded-t-sm bg-blue-600 transition-all duration-300 hover:bg-blue-700"
                      style={{ height: `${Math.min(candidateHeightPct, 100)}%` }}
                    />
                  </div>
                </div>

                {/* X-axis label */}
                <span className="text-[11px] font-medium text-slate-600 pt-2 text-center truncate w-full">
                  {interval.time}
                </span>
              </div>
            );
          })}
        </div>

        {/* Y-axis labels */}
        <div className="absolute left-0 top-6 bottom-8 w-10 flex flex-col justify-between text-[10px] text-slate-400 text-right pr-2 font-mono">
          <span>60</span>
          <span>45</span>
          <span className="text-red-500 font-bold">35</span>
          <span>20</span>
          <span>0</span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-500 gap-2">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-blue-600"></span>
          Queue comparison based on deterministic queuing model (synthetic data).
        </span>
        <span className="text-[11px] text-slate-400">
          Source: DeterministicEstimate (five-minute bucket queue model)
        </span>
      </div>
    </div>
  );
};
