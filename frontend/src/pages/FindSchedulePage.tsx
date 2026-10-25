import React, { useState } from 'react';
import {
  CalendarDays,
  Sparkles,
  ArrowRight,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Check,
  Search,
  Clock,
  Car,
  ShieldCheck,
  HelpCircle,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { AdminTab } from '../types';
import * as api from '../api/client';
import { ProjectExplanation } from '../components/ProjectExplanation';

interface FindSchedulePageProps {
  onNavigate: (tab: AdminTab) => void;
  selectedCandidate: api.ScheduleCandidate | null;
  onSelectCandidate: (candidate: api.ScheduleCandidate) => void;
}

const formatLowerIsBetter = (
  reduction: number | null,
  unit: string,
  lowerLabel: string,
  higherLabel: string,
) => {
  if (reduction === null) return 'Not comparable';
  if (Math.abs(reduction) < 0.05) return 'No modeled change';
  const amount = unit === '%' ? `${Math.abs(reduction)}%` : `${Math.abs(reduction)} ${unit}`;
  return `${amount} ${reduction > 0 ? lowerLabel : higherLabel}`;
};

const changeColor = (reduction: number | null) => {
  if (reduction === null || reduction === 0) return 'text-slate-600';
  return reduction > 0 ? 'text-emerald-600' : 'text-amber-600';
};

export const FindSchedulePage: React.FC<FindSchedulePageProps> = ({
  onNavigate,
  selectedCandidate,
  onSelectCandidate
}) => {
  const [naturalQuery, setNaturalQuery] = useState(
    'Keep Kindergarten fixed and prioritize queue reduction using current scenario demand.'
  );
  const [staggerInterval, setStaggerInterval] = useState<number>(15);
  const [gateFlexibility, setGateFlexibility] = useState<'strict' | 'eligible'>('eligible');
  const [syncSiblings, setSyncSiblings] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [candidates, setCandidates] = useState<api.ScheduleCandidate[]>([]);
  const [searchMeta, setSearchMeta] = useState<{ totalEvaluated: number; feasibleCount: number; searchExplanation: string } | null>(null);
  const [noFeasible, setNoFeasible] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [constraintWarnings, setConstraintWarnings] = useState<string[]>([]);

  const samplePrompts = [
    'Increase demand by 30%, keep Kindergarten fixed, keep sibling groups synchronized and prioritize queue reduction.',
    'Stagger Grades 1–3 by 15 minutes to clear East Wing',
    'Shift all Grade 4–5 vehicles to Gate 4 Athletics loop',
    'Prioritize multi-student sibling carpool synchronization',
  ];

  const handleGenerate = async () => {
    setIsGenerating(true);
    setErrorMessage('');
    setNoFeasible(false);
    setConstraintWarnings([]);

    try {
      // Step 1: Parse natural language → constraints
      const parseResult = await api.parseConstraints(naturalQuery);

      if (!parseResult.valid || !parseResult.constraints) {
        setErrorMessage(
          parseResult.errors.join(' ') ||
          'Constraints could not be validated. Please rephrase your request.'
        );
        setNoFeasible(true);
        setIsGenerating(false);
        return;
      }

      if (parseResult.warnings.length > 0) {
        setConstraintWarnings(parseResult.warnings);
      }

      // Step 2: Search for feasible schedules
      const searchResult = await api.searchSchedules({
        ...parseResult.constraints,
        maxShiftMin: staggerInterval,
        siblingSync: syncSiblings,
        allowGateReassignment: gateFlexibility === 'eligible',
      });

      if (searchResult.candidates.length === 0) {
        setNoFeasible(true);
        setErrorMessage(searchResult.searchExplanation);
      } else {
        setCandidates(searchResult.candidates);
        setSearchMeta({
          totalEvaluated: searchResult.totalEvaluated,
          feasibleCount: searchResult.feasibleCount,
          searchExplanation: searchResult.searchExplanation,
        });
        setNoFeasible(false);
        // Auto-select the first (recommended) candidate
        onSelectCandidate(searchResult.candidates[0]);
      }
    } catch (err: any) {
      const body = err?.body;
      if (body?.error?.code === 'INFEASIBLE_PLAN' || body?.detail?.error?.code === 'INFEASIBLE_PLAN') {
        setNoFeasible(true);
        setErrorMessage(
          body?.error?.details?.[0] ||
          body?.detail?.error?.details?.[0] ||
          err.message
        );
      } else if (body?.error?.code === 'INVALID_CONSTRAINTS' || body?.detail?.error?.code === 'INVALID_CONSTRAINTS') {
        setNoFeasible(true);
        const details = body?.error?.details || body?.detail?.error?.details || [];
        setErrorMessage(
          details.join(' ') || err.message
        );
      } else {
        setErrorMessage(err.message || 'An unexpected error occurred.');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleResetConstraints = () => {
    setNaturalQuery('Keep Kindergarten fixed and prioritize queue reduction using current scenario demand.');
    setStaggerInterval(15);
    setGateFlexibility('eligible');
    setSyncSiblings(false);
    setNoFeasible(false);
    setErrorMessage('');
    setCandidates([]);
    setSearchMeta(null);
    setConstraintWarnings([]);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 md:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                Feature 2 · Schedule Optimization
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500">Stagger Planning Engine</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900 mt-1">
              Find a Better Schedule
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl">
              Compare feasible dismissal times and scenario-eligible gate assignments against the synthetic baseline.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {selectedCandidate && (
              <button
                onClick={() => onNavigate('test')}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs focus-visible:outline-blue-600"
              >
                <span>Test Selected Schedule</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Natural Language Prompt & Constraints Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 md:p-6 shadow-xs space-y-5">
        <div>
          <label
            htmlFor="query-box"
            className="flex items-center justify-between text-xs font-bold text-slate-800 uppercase tracking-wider mb-2"
          >
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-blue-600" />
              Optimization Directive (Natural Language Request)
            </span>
            <span className="text-[11px] text-slate-400 lowercase font-normal">
              Type or select constraint directives below
            </span>
          </label>

          <div className="relative">
            <textarea
              id="query-box"
              rows={2}
              value={naturalQuery}
              onChange={(e) => {
                const value = e.target.value;
                setNaturalQuery(value);
                setSyncSiblings(/\b(sibling|siblings|family|families|multi-child|synchronize|synchronized|sync|together)\b/i.test(value));
              }}
              className="w-full px-3.5 py-2.5 bg-slate-50/70 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white resize-none"
              placeholder="E.g., Increase demand by 30%, keep Kindergarten fixed, keep sibling groups synchronized and prioritize queue reduction."
            />
          </div>

          {/* Quick Suggestion Chips */}
          <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
            <span className="text-[11px] font-medium text-slate-400 mr-1">
              Suggested:
            </span>
            {samplePrompts.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setNaturalQuery(p);
                  setSyncSiblings(/\b(sibling|siblings|family|families|multi-child|synchronize|synchronized|sync|together)\b/i.test(p));
                }}
                className="text-xs bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 px-2.5 py-1 rounded-md transition-colors border border-slate-200/60"
              >
                {p.length > 60 ? p.substring(0, 57) + '...' : p}
              </button>
            ))}
          </div>
        </div>

        {/* Constraint Configurations Grid */}
        <div className="pt-4 border-t border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-slate-500" />
              Operational Parameters & Safeguards
            </h4>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Control 1: Stagger Interval */}
            <div className="p-3 bg-slate-50 border border-slate-200/70 rounded-lg">
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Maximum Time Shift: <span className="text-blue-600 tabular-nums">{staggerInterval} min</span>
              </label>
              <div className="flex items-center gap-1">
                {[10, 15, 20].map((mins) => (
                  <button
                    key={mins}
                    type="button"
                    onClick={() => setStaggerInterval(mins)}
                    className={`flex-1 py-1 text-xs font-medium rounded transition-colors ${
                      staggerInterval === mins
                        ? 'bg-blue-600 text-white shadow-2xs'
                        : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {mins}m
                  </button>
                ))}
              </div>
            </div>

            {/* Control 2: Gate Assignment Flexibility */}
            <div className="p-3 bg-slate-50 border border-slate-200/70 rounded-lg">
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Gate Reallocation
              </label>
              <select
                value={gateFlexibility}
                onChange={(e) => setGateFlexibility(e.target.value as 'strict' | 'eligible')}
                className="w-full bg-white border border-slate-200 rounded text-xs py-1.5 px-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-600"
              >
                <option value="strict">Preserve current gate assignments</option>
                <option value="eligible">Allow scenario-listed alternate gates</option>
              </select>
            </div>

            {/* Control 3: Sibling Synchronization */}
            <div className="p-3 bg-slate-50 border border-slate-200/70 rounded-lg">
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Sibling Carpools
              </label>
              <button
                type="button"
                onClick={() => setSyncSiblings(!syncSiblings)}
                className={`w-full py-1.5 px-2 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                  syncSiblings
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : 'bg-white text-slate-600 border border-slate-200'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>{syncSiblings ? 'Synchronized Pickups' : 'Independent Bells'}</span>
              </button>
            </div>

          </div>

          {/* Constraint Warnings */}
          {constraintWarnings.length > 0 && (
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 space-y-1">
              <div className="font-semibold flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                Constraint Notes:
              </div>
              {constraintWarnings.map((w, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Action Row */}
          <div className="mt-4 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Synthetic scenario · deterministic capacity estimates · no live traffic feed.
            </span>

            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors shadow-2xs disabled:opacity-70 focus-visible:outline-blue-600"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Parsing & Searching...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Candidate Schedules</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Search Meta (when results exist) */}
      {searchMeta && !noFeasible && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
          <span className="font-semibold">Search Complete:</span> {searchMeta.searchExplanation}
        </div>
      )}

      {/* No Feasible Schedule State Handler */}
      {noFeasible ? (
        <div className="bg-white border-2 border-dashed border-red-300 rounded-xl p-8 text-center space-y-4 shadow-xs">
          <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">
              No Feasible Schedule Satisfies Current Constraints
            </h3>
            <p className="text-xs text-slate-600 max-w-lg mx-auto mt-1 leading-relaxed">
              {errorMessage || 'The planner could not find any valid schedule under the given constraints. Try relaxing the parameters.'}
            </p>
          </div>

          <div className="bg-slate-50 p-4 rounded-lg max-w-md mx-auto text-left text-xs text-slate-600 border border-slate-200">
            Gate capacities and scenario-listed gate eligibility were preserved. The explanation above identifies the limiting constraint.
          </div>

          <div className="pt-2">
            <button
              onClick={handleResetConstraints}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-xs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset to Valid Feasible Constraints</span>
            </button>
          </div>
        </div>
      ) : candidates.length > 0 ? (
        <>
          {/* Candidate Schedule Comparison */}
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 gap-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Candidate Schedules ({candidates.length} Feasible Solutions Found)
                </h3>
                <p className="text-xs text-slate-500">
                  Select a candidate schedule to review cohort dismissals and test in simulation
                </p>
              </div>

              {selectedCandidate && (
                <span className="text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-md font-medium">
                  Active Selection: {selectedCandidate.name.split(':')[0]}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
              {candidates.map((candidate) => {
                const isSelected = selectedCandidate?.id === candidate.id;

                return (
                  <div
                    key={candidate.id}
                    onClick={() => onSelectCandidate(candidate)}
                    className={`cursor-pointer rounded-xl p-5 border transition-all relative flex flex-col justify-between ${
                      isSelected
                        ? 'bg-white border-blue-600 ring-2 ring-blue-600/20 shadow-md'
                        : 'bg-white border-slate-200 hover:border-slate-300 shadow-2xs'
                    }`}
                  >
                    <div>
                      {/* Top Header Badge */}
                      <div className="flex items-center justify-between mb-3">
                        <span
                          className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                            candidate.badge === 'Recommended'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {candidate.badge}
                        </span>

                        <div
                          className={`w-5 h-5 rounded-full flex items-center justify-center transition-colors ${
                            isSelected
                              ? 'bg-blue-600 text-white'
                              : 'border border-slate-300 text-transparent'
                          }`}
                        >
                          <Check className="w-3.5 h-3.5" />
                        </div>
                      </div>

                      <h4 className="text-sm font-bold text-slate-900">
                        {candidate.name}
                      </h4>
                      <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                        {candidate.description}
                      </p>

                      {/* Key Metric Comparison Badges */}
                      <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-500">Peak Queue Reduction:</span>
                          <span className={`font-bold tabular-nums ${changeColor(candidate.peakQueueReductionPct)}`}>
                            {formatLowerIsBetter(candidate.peakQueueReductionPct, '%', 'lower', 'higher')}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-500">Wait Time Saved:</span>
                          <span className={`font-bold tabular-nums ${changeColor(candidate.waitTimeReductionMin)}`}>
                            {formatLowerIsBetter(candidate.waitTimeReductionMin, 'min', 'saved', 'longer')}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-500">Spillback Contained:</span>
                          <span className={`font-bold tabular-nums ${changeColor(candidate.spillbackReductionMeters)}`}>
                            {formatLowerIsBetter(candidate.spillbackReductionMeters, 'm', 'lower', 'higher')}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">
                        Compliance: {candidate.constraintFeasibility}
                      </span>
                      <span
                        className={`font-semibold ${
                          candidate.riskProfile === 'Low'
                            ? 'text-emerald-700'
                            : 'text-amber-700'
                        }`}
                      >
                        Risk: {candidate.riskProfile}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Group Pickup-Time Changes Table for Selected Candidate */}
          {selectedCandidate && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-2 mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Cohort Release Schedule: {selectedCandidate.name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Detailed timeline adjustments, assigned gates, bay allocations, and vehicle volumes
                  </p>
                </div>

                <button
                  onClick={() => onNavigate('test')}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors shadow-2xs self-start sm:self-auto"
                >
                  <span>Proceed to Test with Simulation</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Grade Cohort</th>
                      <th className="py-2.5 px-3">Baseline Bell</th>
                      <th className="py-2.5 px-3">Proposed Bell</th>
                      <th className="py-2.5 px-3">Shift Adjustment</th>
                      <th className="py-2.5 px-3">Assigned Gate</th>
                      <th className="py-2.5 px-3">Bay Zone</th>
                      <th className="py-2.5 px-3 text-right">Est. Vehicles</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {selectedCandidate.groupSchedule.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-3 font-semibold text-slate-800">
                          {row.cohort}
                        </td>
                        <td className="py-3 px-3 text-slate-500">{row.baselineTime}</td>
                        <td className="py-3 px-3 font-bold text-blue-700">
                          {row.proposedTime}
                        </td>
                        <td className="py-3 px-3">
                          <span className="inline-block text-[11px] font-medium bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                            {row.timeDelta}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-800 font-medium">
                          {row.assignedGate}
                        </td>
                        <td className="py-3 px-3 text-slate-600">
                          {row.zoneBay}
                          <div className={`mt-1 text-[10px] ${
                            row.bayConstraintStatus === 'grandfathered'
                              ? 'text-amber-700'
                              : 'text-slate-400'
                          }`}>
                            {row.requiredBays} required · {row.availableBays} available
                            {row.bayConstraintStatus === 'grandfathered' && ' · existing assignment'}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-right font-semibold tabular-nums text-slate-800">
                          {row.vehicles} veh
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Constraint Compliance Summary */}
              <div className="mt-5 pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Feasibility: {selectedCandidate.constraintFeasibility}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Risk Profile: {selectedCandidate.riskProfile}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Data Source: Synthetic (Deterministic Planning)</span>
                </div>
              </div>
              {selectedCandidate.feasibilityReason && (
                <p className="mt-3 text-xs text-slate-600">
                  Capacity check: {selectedCandidate.feasibilityReason}
                </p>
              )}
              {selectedCandidate.gateLoads && selectedCandidate.gateCapacities && (
                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                  {Object.entries(selectedCandidate.gateLoads).map(([gateId, load]) => {
                    const capacity = selectedCandidate.gateCapacities?.[gateId] ?? 0;
                    const gateName = selectedCandidate.groupSchedule.find(
                      (row) => row.assignedGateId === gateId
                    )?.assignedGate ?? gateId;
                    const overCapacity = load > capacity;
                    return (
                      <span
                        key={gateId}
                        className={`rounded px-2 py-1 ${
                          overCapacity
                            ? 'bg-amber-50 text-amber-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {gateName}: {load.toFixed(1)} / {capacity.toFixed(0)} veh/h
                      </span>
                    );
                  })}
                </div>
              )}
              <div className="mt-4">
                <ProjectExplanation source="schedule" referenceId={selectedCandidate.id} />
              </div>
            </div>
          )}
        </>
      ) : (
        /* Initial state — no search performed yet */
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center shadow-xs">
          <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
            <Search className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900 mt-4">
            Ready to Generate Candidate Schedules
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1.5 leading-relaxed">
            Enter your optimization directive above and click "Generate Candidate Schedules" to search the feasible schedule space using the backend planning engine.
          </p>
        </div>
      )}
    </div>
  );
};
