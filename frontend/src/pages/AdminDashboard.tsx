import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Search,
  CalendarDays,
  PlaySquare,
  Car,
  Clock,
  ShieldCheck,
  CheckCircle2,
  Users,
  Loader2
} from 'lucide-react';
import { AdminTab } from '../types';
import * as api from '../api/client';
import { MetricCard } from '../components/MetricCard';

interface AdminDashboardProps {
  onNavigate: (tab: AdminTab) => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onNavigate }) => {
  const [scenario, setScenario] = useState<api.ScenarioResponse | null>(null);
  const [diagnosis, setDiagnosis] = useState<api.BottleneckDiagnosis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getScenario(), api.getDiagnosis()])
      .then(([sc, diag]) => {
        setScenario(sc);
        setDiagnosis(diag.diagnosis);
      })
      .catch((err) => console.error('Failed to load dashboard data:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !scenario || !diagnosis) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        <span className="ml-2 text-sm text-slate-500">Loading scenario data from backend...</span>
      </div>
    );
  }

  const SCHOOL_PROFILE = {
    name: scenario.school.name,
    activeSession: scenario.school.activeSession,
    timeWindow: `${scenario.school.timeWindowStart} – ${scenario.school.timeWindowEnd}`,
    totalVehicles: scenario.school.totalVehicles,
    totalGates: scenario.school.totalGates,
    pickupBays: scenario.school.pickupBays,
  };
  const INITIAL_TRAFFIC_METRICS = scenario.trafficMetrics;
  const GATES_DATA = scenario.gates;
  const BOTTLENECK_DIAGNOSIS = diagnosis;
  const underutilizedGate = GATES_DATA
    .filter((gate) => gate.id !== BOTTLENECK_DIAGNOSIS.gateId)
    .sort((a, b) => a.utilizationRate - b.utilizationRate)[0];

  return (
    <div className="space-y-6">
      {/* Top Welcome & Session Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 md:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                Synthetic Scenario Baseline
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500">
                Deterministic estimates · no live sensor feed
              </span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900 mt-1">
              {SCHOOL_PROFILE.name}
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl">
              {SCHOOL_PROFILE.activeSession}: {SCHOOL_PROFILE.totalVehicles} modeled vehicles across {scenario.gates.length} gates and {SCHOOL_PROFILE.pickupBays} pickup bays.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => onNavigate('cause')}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs focus-visible:outline-blue-600"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Diagnose Bottlenecks</span>
            </button>
            <button
              onClick={() => onNavigate('schedule')}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200 hover:bg-slate-100 rounded-lg transition-colors focus-visible:outline-blue-600"
            >
              <CalendarDays className="w-3.5 h-3.5 text-blue-600" />
              <span>Optimize Schedule</span>
            </button>
          </div>
        </div>
      </div>

      {/* Current Congestion Alert Banner */}
      <div className="bg-red-50/80 border border-red-200 rounded-xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-2 bg-red-100 text-red-700 rounded-lg shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-red-900">
                Modeled Capacity Bottleneck — {BOTTLENECK_DIAGNOSIS.gateName.split('—')[0].trim()}
              </h3>
              <span className="text-[11px] font-semibold bg-red-200/70 text-red-800 px-2 py-0.2 rounded-full">
                Synthetic estimate
              </span>
            </div>
            <p className="text-xs text-red-700 mt-1 max-w-3xl leading-relaxed">
              Scenario peak demand is <strong className="font-semibold">{BOTTLENECK_DIAGNOSIS.peakDemandRate} veh/h</strong> against {BOTTLENECK_DIAGNOSIS.maxThroughputCapacity} veh/h capacity ({Math.round(BOTTLENECK_DIAGNOSIS.overloadRatio * 100)}% of capacity). This is modeled from synthetic inputs, not an observed queue or live traffic feed.
            </p>
          </div>
        </div>

        <button
          onClick={() => onNavigate('cause')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shrink-0 transition-colors shadow-2xs"
        >
          <span>Investigate Root Cause</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 4 Key Traffic Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {INITIAL_TRAFFIC_METRICS.map((metric) => (
          <MetricCard
            key={metric.id}
            metric={metric}
            icon={
              metric.id === 'peak-queue' ? (
                <Car className="w-4 h-4" />
              ) : metric.id === 'avg-wait-time' ? (
                <Clock className="w-4 h-4" />
              ) : metric.id === 'gate-utilization' ? (
                <AlertTriangle className="w-4 h-4" />
              ) : (
                <Users className="w-4 h-4" />
              )
            }
          />
        ))}
      </div>

      {/* Main Bottleneck Summary & Gate Status Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Main Bottleneck Summary */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                <h3 className="text-sm font-bold text-slate-900">
                  Primary Bottleneck Summary
                </h3>
              </div>
              <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded">
                {BOTTLENECK_DIAGNOSIS.gateName.split('—')[0].trim()}
              </span>
            </div>

            <div className="mt-4 space-y-3">
              <div className="text-sm font-semibold text-slate-800">
                {BOTTLENECK_DIAGNOSIS.primaryCause}
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {BOTTLENECK_DIAGNOSIS.explanation}
              </p>

              {/* Mini metrics strip */}
              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="bg-slate-50 border border-slate-100 p-3 rounded-lg text-center">
                  <div className="text-[11px] text-slate-500 font-medium">Hourly Capacity</div>
                  <div className="text-base font-bold text-slate-800 tabular-nums mt-0.5">
                    {BOTTLENECK_DIAGNOSIS.maxThroughputCapacity} veh/hr
                  </div>
                </div>
                <div className="bg-red-50 border border-red-100 p-3 rounded-lg text-center">
                  <div className="text-[11px] text-red-600 font-medium">Peak Arrival Demand</div>
                  <div className="text-base font-bold text-red-700 tabular-nums mt-0.5">
                    {BOTTLENECK_DIAGNOSIS.peakDemandRate} veh/hr
                  </div>
                </div>
                <div className="bg-slate-50 border border-slate-100 p-3 rounded-lg text-center">
                  <div className="text-[11px] text-slate-500 font-medium">Overload Ratio</div>
                  <div className="text-base font-bold text-red-600 tabular-nums mt-0.5">
                    {BOTTLENECK_DIAGNOSIS.overloadRatio}x ({Math.round(BOTTLENECK_DIAGNOSIS.overloadRatio * 100)}%)
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              {underutilizedGate
                ? `${underutilizedGate.name.split('—')[0].trim()} is least utilized at ${underutilizedGate.utilizationRate}% of capacity.`
                : 'No alternate gate utilization data is available.'}
            </span>
            <button
              onClick={() => onNavigate('cause')}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700"
            >
              <span>View Full Diagnostic</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right Col: Active Gates Utilization */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900">
              Gate Utilization
            </h3>
            <span className="text-xs text-slate-400">{GATES_DATA.length} Operational</span>
          </div>

          <div className="mt-4 space-y-3.5">
            {GATES_DATA.map((gate) => {
              const isBottleneck = gate.status === 'bottleneck';
              const isOptimal = gate.status === 'optimal';

              return (
                <div key={gate.id} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-800 truncate max-w-[140px]">
                      {gate.name.split('—')[0]}
                    </span>
                    <span
                      className={`font-semibold tabular-nums ${
                        isBottleneck
                          ? 'text-red-600'
                          : isOptimal
                          ? 'text-slate-700'
                          : 'text-amber-600'
                      }`}
                    >
                      {gate.utilizationRate}%
                    </span>
                  </div>

                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        isBottleneck
                          ? 'bg-red-500'
                          : gate.utilizationRate > 80
                          ? 'bg-amber-500'
                          : 'bg-blue-600'
                      }`}
                      style={{ width: `${Math.min(100, gate.utilizationRate)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>{gate.bays} bays</span>
                    <span>{gate.peakDemand} / {gate.hourlyCapacity} veh/h</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-5 pt-3 border-t border-slate-100">
            <button
              onClick={() => onNavigate('schedule')}
              className="w-full py-2 px-3 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold rounded-lg transition-colors text-center block"
            >
              Rebalance Gate Allocations
            </button>
          </div>
        </div>
      </div>

      {/* 3 Core Features Quick Navigation Cards */}
      <div>
        <div className="mb-3">
          <h3 className="text-sm font-bold text-slate-900">
            Core Workflow Navigation
          </h3>
          <p className="text-xs text-slate-500">
            Step through the diagnostic, optimization, and simulation pipeline
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Find the Cause */}
          <div
            onClick={() => onNavigate('cause')}
            className="group cursor-pointer bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-sm transition-all flex flex-col justify-between"
          >
            <div>
              <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Search className="w-4 h-4" />
              </div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Step 1 · Diagnostic
              </div>
              <h4 className="text-base font-bold text-slate-900 mt-1">
                Find the Cause
              </h4>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Compare scenario-provided peak demand with configured gate capacities to identify modeled bottlenecks.
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-blue-600 group-hover:text-blue-700">
              <span>View Evidence & Imbalances</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Card 2: Find a Better Schedule */}
          <div
            onClick={() => onNavigate('schedule')}
            className="group cursor-pointer bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-sm transition-all flex flex-col justify-between"
          >
            <div>
              <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <CalendarDays className="w-4 h-4" />
              </div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Step 2 · Optimization
              </div>
              <h4 className="text-base font-bold text-slate-900 mt-1">
                Find a Better Schedule
              </h4>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Generate and compare candidate schedules using natural-language requests, stagger intervals, and gate redistribution constraints.
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-blue-600 group-hover:text-blue-700">
              <span>Explore 3 Candidate Plans</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Card 3: Test the Schedule */}
          <div
            onClick={() => onNavigate('test')}
            className="group cursor-pointer bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-sm transition-all flex flex-col justify-between"
          >
            <div>
              <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <PlaySquare className="w-4 h-4" />
              </div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Step 3 · Verification
              </div>
              <h4 className="text-base font-bold text-slate-900 mt-1">
                Test the Schedule
              </h4>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Run a deterministic estimate to compare queue, wait, delay, and spillback metrics against the scenario baseline.
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-blue-600 group-hover:text-blue-700">
              <span>Simulate & Compare Metrics</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
