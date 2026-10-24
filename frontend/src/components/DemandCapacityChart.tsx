import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import * as api from '../api/client';

export const DemandCapacityChart: React.FC = () => {
  const [gates, setGates] = useState<api.GateInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getScenario()
      .then((sc) => setGates(sc.gates))
      .catch((err) => console.error('Failed to load gates:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-center h-40">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <span className="ml-2 text-xs text-slate-500">Loading gate data...</span>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
        <div>
          <h3 className="text-sm font-bold text-slate-900">
            Gate Capacity vs. Peak Arrival Demand
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Hourly vehicle capacity compared against peak dismissal surge rates (Synthetic data)
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-xs bg-slate-300"></span>
            <span className="text-slate-600">Hourly Capacity</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-xs bg-blue-600"></span>
            <span className="text-slate-600">Peak Demand Rate</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-xs bg-red-500"></span>
            <span className="text-slate-600">Overload Condition</span>
          </div>
        </div>
      </div>

      {/* Grid of Gate comparisons */}
      <div className="space-y-5">
        {gates.map((gate) => {
          const isOverloaded = gate.peakDemand > gate.hourlyCapacity;
          const maxScale = 160;
          const capacityWidthPct = Math.min(100, (gate.hourlyCapacity / maxScale) * 100);
          const demandWidthPct = Math.min(100, (gate.peakDemand / maxScale) * 100);

          return (
            <div key={gate.id} className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/50">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800">
                    {gate.name}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    ({gate.bays} bays)
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {isOverloaded ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-md">
                      <AlertTriangle className="w-3 h-3" />
                      {gate.utilizationRate}% Capacity Overload
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                      <CheckCircle2 className="w-3 h-3" />
                      {gate.utilizationRate}% Utilization (Nominal)
                    </span>
                  )}
                </div>
              </div>

              {/* Bar visualization */}
              <div className="space-y-1.5 mt-2">
                {/* Demand Bar */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-20 text-[11px] text-slate-500 truncate">
                    Peak Demand
                  </span>
                  <div className="flex-1 bg-slate-200/60 rounded-full h-3 overflow-hidden relative">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isOverloaded ? 'bg-red-500' : 'bg-blue-600'
                      }`}
                      style={{ width: `${demandWidthPct}%` }}
                    />
                  </div>
                  <span className="w-16 text-right text-xs font-semibold tabular-nums text-slate-800">
                    {gate.peakDemand} veh/h
                  </span>
                </div>

                {/* Capacity Bar */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-20 text-[11px] text-slate-500 truncate">
                    Max Capacity
                  </span>
                  <div className="flex-1 bg-slate-200/60 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-slate-400 transition-all duration-500"
                      style={{ width: `${capacityWidthPct}%` }}
                    />
                  </div>
                  <span className="w-16 text-right text-xs font-medium tabular-nums text-slate-500">
                    {gate.hourlyCapacity} veh/h
                  </span>
                </div>
              </div>

              {/* Assigned cohort note */}
              <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
                <span>Assigned: {gate.assignedGrades.join(' · ')}</span>
                <span className="hidden sm:inline text-slate-400">{gate.locationNote}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
