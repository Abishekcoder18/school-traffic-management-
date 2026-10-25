import React, { useState, useEffect } from 'react';
import {
  ArrowRight,
  AlertTriangle,
  Building,
  Users,
  Car,
  Clock,
  ShieldAlert,
  CheckCircle2,
  Sparkles,
  Loader2
} from 'lucide-react';
import { AdminTab } from '../types';
import * as api from '../api/client';
import { DemandCapacityChart } from '../components/DemandCapacityChart';
import { ProjectExplanation } from '../components/ProjectExplanation';

interface FindCausePageProps {
  onNavigate: (tab: AdminTab) => void;
}

export const FindCausePage: React.FC<FindCausePageProps> = ({ onNavigate }) => {
  const [scenario, setScenario] = useState<api.ScenarioResponse | null>(null);
  const [diagResp, setDiagResp] = useState<api.DiagnosisResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getScenario(), api.getDiagnosis()])
      .then(([sc, dr]) => {
        setScenario(sc);
        setDiagResp(dr);
      })
      .catch((err) => console.error('Failed to load diagnosis data:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !scenario || !diagResp) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
        <span className="ml-2 text-sm text-slate-500">Loading diagnosis from backend...</span>
      </div>
    );
  }

  const SCHOOL_PROFILE = {
    name: scenario.school.name,
    timeWindow: `${scenario.school.timeWindowStart} – ${scenario.school.timeWindowEnd}`,
    totalVehicles: scenario.school.totalVehicles,
    pickupBays: scenario.school.pickupBays,
  };
  const DEMAND_COHORTS = scenario.cohorts;
  const BOTTLENECK_DIAGNOSIS = diagResp.diagnosis;
  const GATES_DATA = scenario.gates;

  return (
    <div className="space-y-6">
      {/* Header & Scenario Summary */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 md:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                Feature 1 · Diagnostic Analysis
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500">Root-Cause Detection</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900 mt-1">
              Find the Cause
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl">
              Evaluating infrastructure throughput limits against cohort vehicle arrival volumes during the peak afternoon dismissal window.
            </p>
          </div>

          <button
            onClick={() => onNavigate('schedule')}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs self-start md:self-auto focus-visible:outline-blue-600"
          >
            <span>Proceed to Find a Better Schedule</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Scenario Overview Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-slate-100">
          <div className="bg-slate-50 border border-slate-200/60 p-3 rounded-lg">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs">
              <Clock className="w-3.5 h-3.5" />
              <span>Time Window</span>
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1">
              {SCHOOL_PROFILE.timeWindow}
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200/60 p-3 rounded-lg">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs">
              <Car className="w-3.5 h-3.5" />
              <span>Total Vehicle Demand</span>
            </div>
            <div className="text-sm font-bold text-slate-800 tabular-nums mt-1">
              {SCHOOL_PROFILE.totalVehicles} Vehicles
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200/60 p-3 rounded-lg">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs">
              <Building className="w-3.5 h-3.5" />
              <span>Active Physical Gates</span>
            </div>
            <div className="text-sm font-bold text-slate-800 tabular-nums mt-1">
              {GATES_DATA.length} Physical Gates
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200/60 p-3 rounded-lg">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs">
              <Users className="w-3.5 h-3.5" />
              <span>Loading Bays</span>
            </div>
            <div className="text-sm font-bold text-slate-800 tabular-nums mt-1">
              {SCHOOL_PROFILE.pickupBays} Dedicated Bays
            </div>
          </div>
        </div>
      </div>

      {/* Demand vs Capacity Visualization */}
      <DemandCapacityChart />
      <ProjectExplanation source="diagnosis" />

      {/* Identified Bottleneck & Evidence Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 md:p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-red-100 text-red-600 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Identified Bottleneck: {BOTTLENECK_DIAGNOSIS.gateName}
              </h3>
              <p className="text-xs text-slate-500">
                Modeled load imbalance · {Math.round(BOTTLENECK_DIAGNOSIS.overloadRatio * 100)}% of gate capacity
              </p>
            </div>
          </div>

          <span className="text-xs font-bold text-red-700 bg-red-50 border border-red-200 px-3 py-1 rounded-full self-start sm:self-auto">
            Requires Rescheduling
          </span>
        </div>

        {/* Clear Cause Explanation */}
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
            Root Cause Diagnosis
          </h4>
          <p className="text-sm text-slate-800 leading-relaxed">
            {BOTTLENECK_DIAGNOSIS.explanation}
          </p>
        </div>

        {/* 3 Evidence Cards */}
        <div>
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
            Scenario-Derived Evidence
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {BOTTLENECK_DIAGNOSIS.evidence.map((item, index) => (
              <div
                key={index}
                className="p-4 border border-slate-200 rounded-lg bg-white shadow-2xs hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-xs font-bold text-slate-900">
                    {item.title}
                  </span>
                  <span className="text-[11px] font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded tabular-nums">
                    {item.metric}
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {item.detail}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Cohort Demand Breakdown Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-2 mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Grade Cohort Demand & Gate Assignment Mapping
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Breakdown of student cohorts, estimated vehicle volume, current bell times, and designated gates
            </p>
          </div>
          <span className="text-xs font-medium text-slate-500">
            5 Registered Cohorts
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Grade Cohort</th>
                <th className="py-2.5 px-3">Grade Span</th>
                <th className="py-2.5 px-3 text-right">Students</th>
                <th className="py-2.5 px-3 text-right">Vehicle Demand</th>
                <th className="py-2.5 px-3">Dismissal Bell</th>
                <th className="py-2.5 px-3">Assigned Gate</th>
                <th className="py-2.5 px-3 text-right">Bays Req.</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {DEMAND_COHORTS.map((c) => {
                const isConflict = c.assignedGateId === 'gate-2';
                const gate = GATES_DATA.find((g) => g.id === c.assignedGateId);

                return (
                  <tr
                    key={c.id}
                    className={`hover:bg-slate-50/70 transition-colors ${
                      isConflict ? 'bg-red-50/30' : ''
                    }`}
                  >
                    <td className="py-3 px-3 font-semibold text-slate-800">
                      {c.cohort}
                    </td>
                    <td className="py-3 px-3 text-slate-600">{c.gradeSpan}</td>
                    <td className="py-3 px-3 text-right font-medium tabular-nums text-slate-700">
                      {c.studentCount}
                    </td>
                    <td className="py-3 px-3 text-right font-bold tabular-nums text-slate-900">
                      {c.vehicleDemand} veh
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-800">
                      {c.currentDismissalTime}
                    </td>
                    <td className="py-3 px-3 text-slate-700 font-medium">
                      {gate ? gate.name.split('—')[0] : c.assignedGateId}
                    </td>
                    <td className="py-3 px-3 text-right font-medium tabular-nums text-slate-700">
                      {c.bayRequirement}
                    </td>
                    <td className="py-3 px-3">
                      {isConflict ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-red-600 bg-red-100/70 px-2 py-0.5 rounded">
                          <AlertTriangle className="w-3 h-3" />
                          Simultaneous Bell Conflict
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                          <CheckCircle2 className="w-3 h-3" />
                          Balanced
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Next Step Action Banner */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl p-5 md:p-6 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h4 className="text-base font-bold">
            Ready to eliminate the East Wing Gate bottleneck?
          </h4>
          <p className="text-xs text-blue-100 mt-1 max-w-xl">
            GateFlow AI can formulate staggered cohort release windows and redistribute vehicle demand across idle Gate 4 capacity.
          </p>
        </div>

        <button
          onClick={() => onNavigate('schedule')}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-blue-700 hover:bg-blue-50 text-xs font-bold rounded-lg transition-colors shrink-0 shadow-sm focus-visible:outline-white"
        >
          <span>Find a Better Schedule</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
