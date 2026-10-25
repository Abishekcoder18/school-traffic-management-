import React, { useState } from 'react';
import {
  PlaySquare,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Clock,
  ShieldCheck,
  Building,
  Car,
  FileCheck,
  Loader2
} from 'lucide-react';
import { AdminTab } from '../types';
import * as api from '../api/client';
import { SimulationChart } from '../components/SimulationChart';
import { ProjectExplanation } from '../components/ProjectExplanation';

interface TestSchedulePageProps {
  onNavigate: (tab: AdminTab) => void;
  selectedCandidate: api.ScheduleCandidate | null;
}

const MetricDelta: React.FC<{ metric: api.MetricComparison }> = ({ metric }) => {
  const isImprovement = metric.deltaPct !== null && metric.deltaPct < 0;
  const isWorse = metric.deltaPct !== null && metric.deltaPct > 0;
  const label = metric.deltaPct === null
    ? 'No baseline for % change'
    : metric.deltaPct === 0
      ? 'No modeled change'
      : `${Math.abs(metric.deltaPct)}% ${isImprovement ? 'lower' : 'higher'}`;
  const color = isImprovement
    ? 'text-emerald-700 bg-emerald-50'
    : isWorse
      ? 'text-red-700 bg-red-50'
      : 'text-slate-600 bg-slate-100';

  return <span className={`px-2 py-0.5 rounded ${color}`}>{label}</span>;
};

export const TestSchedulePage: React.FC<TestSchedulePageProps> = ({
  onNavigate,
  selectedCandidate
}) => {
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationProgress, setSimulationProgress] = useState<number>(0);
  const [simStepText, setSimStepText] = useState<string>('');
  const [simResult, setSimResult] = useState<api.SimulationResult | null>(null);
  const [comparison, setComparison] = useState<api.ComparisonReport | null>(null);
  const [stressResult, setStressResult] = useState<api.StressTestResponse | null>(null);
  const [stressError, setStressError] = useState<string>('');
  const [showAdoptSuccess, setShowAdoptSuccess] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');

  if (!selectedCandidate) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-8 text-center shadow-xs space-y-4">
        <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
          <PlaySquare className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-slate-900">
          No Schedule Selected for Testing
        </h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Navigate to "Find a Better Schedule" to generate and select a candidate plan before running a simulation.
        </p>
        <button
          onClick={() => onNavigate('schedule')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Go to Schedule Planner</span>
        </button>
      </div>
    );
  }

  const runSimulation = async () => {
    setIsSimulating(true);
    setErrorMessage('');
    setSimResult(null);
    setComparison(null);
    setStressResult(null);
    setStressError('');

    setSimulationProgress(15);
    setSimStepText('Phase 1: Preparing schedule inputs for queuing simulation...');

    try {
      // Small delay to show progress
      await new Promise(r => setTimeout(r, 300));
      setSimulationProgress(40);
      setSimStepText('Phase 2: Running deterministic estimate for candidate and baseline...');

      const result = await api.runSimulation(selectedCandidate.id);
      setSimulationProgress(70);
      setSimStepText('Phase 3: Loading baseline-versus-candidate comparison...');
      const report = await api.getComparison(result.runId);
      setSimResult(result);
      setComparison(report);

      setSimulationProgress(85);
      setSimStepText('Optional: Running stress scenarios...');
      try {
        setStressResult(await api.runStressTests(selectedCandidate.id));
      } catch (err: any) {
        setStressError(err.message || 'Stress testing failed.');
      }
      setSimulationProgress(100);
      setSimStepText('Comparison complete.');
    } catch (err: any) {
      setErrorMessage(err.message || 'Simulation failed unexpectedly.');
    } finally {
      setIsSimulating(false);
    }
  };

  const metrics = simResult?.metrics;
  const improvements = simResult?.improvements || [];
  const remainingRisks = simResult?.remainingRisks || [];
  const fidelityNote = simResult?.fidelityNote || '';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 md:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                Feature 3 · Deterministic Traffic Simulation
              </span>
              <span className="text-xs text-slate-400">·</span>
              <span className="text-xs text-slate-500">Validation & Impact Assessment</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900 mt-1">
              Test the Schedule
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-2xl">
              Compare baseline congestion against <strong className="font-semibold text-slate-800">{selectedCandidate.name}</strong> to verify queue dissipation and queue containment before deployment.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => onNavigate('schedule')}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors focus-visible:outline-blue-600"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Schedule Selection</span>
            </button>

            <button
              onClick={runSimulation}
              disabled={isSimulating}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-2xs disabled:opacity-60 focus-visible:outline-blue-600"
            >
              {isSimulating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <PlaySquare className="w-4 h-4" />
              )}
              <span>{isSimulating ? 'Simulating...' : 'Run Simulation'}</span>
            </button>
          </div>
        </div>

        {/* Candidate Summary Card */}
        <div className="mt-5 p-3.5 bg-blue-50/60 border border-blue-200/70 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0">
              ✓
            </div>
            <div>
              <div className="text-xs font-bold text-blue-900">
                Active Test Subject: {selectedCandidate.name}
              </div>
              <div className="text-[11px] text-blue-700">
                {selectedCandidate.description}
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Synthetic scenario data · deterministic estimate · no live traffic feed or SUMO simulation.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-blue-800 font-medium shrink-0">
            <span>Stagger: {selectedCandidate.staggerIntervalMin} mins</span>
            <span>·</span>
            <span>Feasibility: {selectedCandidate.constraintFeasibility}</span>
          </div>
        </div>
      </div>

      {/* Error message */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800">
          <strong>Simulation Error:</strong> {errorMessage}
        </div>
      )}
      {stressError && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
          The simulation and comparison completed; optional stress testing failed: {stressError}
        </div>
      )}

      {/* Simulation Running Progress Indicator */}
      {isSimulating && (
        <div className="bg-white border border-blue-300 rounded-xl p-5 shadow-sm space-y-3 animate-in fade-in">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-blue-900">{simStepText}</span>
            <span className="font-bold text-blue-600 tabular-nums">
              {simulationProgress}%
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
            <div
              className="h-full bg-blue-600 rounded-full transition-all duration-300"
              style={{ width: `${simulationProgress}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-500">
            Running deterministic queuing simulation with synthetic data. Results labeled as DeterministicEstimate.
          </p>
        </div>
      )}

      {/* Results — only shown when simulation has run */}
      {metrics && (
        <>
          {comparison && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <div className="text-xs font-semibold uppercase tracking-wider text-blue-800">
                Baseline comparison · {comparison.computedFrom}
              </div>
              <p className="mt-1 text-sm text-blue-900">{comparison.overallImprovement}</p>
              <p className="mt-1 text-xs text-blue-700">
                This is a model estimate from synthetic scenario data, not an observed or guaranteed improvement.
              </p>
            </div>
          )}

          {/* 5-Metric Comparison Matrix Dashboard */}
          <div>
            <div className="mb-3">
              <h3 className="text-sm font-bold text-slate-900">
                Baseline vs. Candidate Verification Matrix
              </h3>
              <p className="text-xs text-slate-500">
                Quantitative impact across key traffic, safety, and delay metrics
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {/* Metric 1: Peak Queue */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Peak Queue Length
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-900 tabular-nums">
                    {metrics.peakQueue.candidate}
                  </span>
                  <span className="text-xs text-slate-400 line-through tabular-nums">
                    {metrics.peakQueue.baseline}
                  </span>
                  <span className="text-[11px] text-slate-500">{metrics.peakQueue.unit}</span>
                </div>
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  <MetricDelta metric={metrics.peakQueue} />
                </div>
              </div>

              {/* Metric 2: 95th% Wait Time */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  95th% Pickup Wait
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-900 tabular-nums">
                    {metrics.waitTimeP95.candidate}
                  </span>
                  <span className="text-xs text-slate-400 line-through tabular-nums">
                    {metrics.waitTimeP95.baseline}
                  </span>
                  <span className="text-[11px] text-slate-500">{metrics.waitTimeP95.unit}</span>
                </div>
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  <MetricDelta metric={metrics.waitTimeP95} />
                </div>
              </div>

              {/* Metric 3: Total Vehicle Delay */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Total Vehicle Delay
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-900 tabular-nums">
                    {metrics.totalDelay.candidate}
                  </span>
                  <span className="text-xs text-slate-400 line-through tabular-nums">
                    {metrics.totalDelay.baseline}
                  </span>
                  <span className="text-[11px] text-slate-500">{metrics.totalDelay.unit}</span>
                </div>
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  <MetricDelta metric={metrics.totalDelay} />
                </div>
              </div>

              {/* Metric 4: Spillback Distance */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Arterial Spillback
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-emerald-700 tabular-nums">
                    {metrics.spillbackDistance.candidate}m
                  </span>
                  <span className="text-xs text-slate-400 line-through tabular-nums">
                    {metrics.spillbackDistance.baseline}m
                  </span>
                </div>
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  <MetricDelta metric={metrics.spillbackDistance} />
                </div>
              </div>

              {/* Metric 5: Zone Violations */}
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Zone Violations
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-bold text-slate-900 tabular-nums">
                    {metrics.zoneViolations.candidate}
                  </span>
                  <span className="text-xs text-slate-400 line-through tabular-nums">
                    {metrics.zoneViolations.baseline}
                  </span>
                  <span className="text-[11px] text-slate-500">{metrics.zoneViolations.unit}</span>
                </div>
                <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  <MetricDelta metric={metrics.zoneViolations} />
                </div>
              </div>
            </div>
          </div>

          {/* Chart — uses simulation time intervals */}
          {simResult && <SimulationChart timeIntervals={simResult.timeIntervals} />}
          {simResult && (
            <ProjectExplanation source="simulation" referenceId={simResult.runId} />
          )}

          {/* Improvements and Operational Risks Side-by-Side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Model Observations
                </h3>
              </div>
              <ul className="mt-4 space-y-3 text-xs text-slate-600">
                {improvements.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 shrink-0 mt-1.5"></span>
                    <span className="leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  Remaining Operational Risks & Mitigations
                </h3>
              </div>
              <ul className="mt-4 space-y-3 text-xs text-slate-600">
                {remainingRisks.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-1.5"></span>
                    <span className="leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Stress Test Results */}
          {stressResult && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                <h3 className="text-sm font-bold text-slate-900">
                  Stress Test Results ({stressResult.scenarios.length} Scenarios)
                </h3>
                <span className="text-xs text-slate-500">Data: Synthetic · DeterministicEstimate</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Scenario</th>
                      <th className="py-2.5 px-3 text-right">Demand</th>
                      <th className="py-2.5 px-3 text-right">Dwell</th>
                      <th className="py-2.5 px-3 text-right">Compliance</th>
                      <th className="py-2.5 px-3 text-right">Peak Gate Load</th>
                      <th className="py-2.5 px-3 text-right">Mean Queue</th>
                      <th className="py-2.5 px-3 text-right">P95 Wait</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {stressResult.scenarios.map((sc) => (
                      <tr key={sc.scenarioId} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-3 font-semibold text-slate-800">{sc.scenarioName}</td>
                        <td className="py-3 px-3 text-right tabular-nums">{(sc.demandFactor * 100).toFixed(0)}%</td>
                        <td className="py-3 px-3 text-right tabular-nums">{(sc.dwellFactor * 100).toFixed(0)}%</td>
                        <td className="py-3 px-3 text-right tabular-nums">{(sc.complianceRate * 100).toFixed(0)}%</td>
                        <td className={`py-3 px-3 text-right font-medium tabular-nums ${sc.gateCapacityWithinLimit ? 'text-slate-700' : 'text-red-700'}`}>
                          {sc.peakGateUtilizationPct.toFixed(1)}%
                          {!sc.gateCapacityWithinLimit && <div className="text-[10px]">Above 105% limit</div>}
                        </td>
                        <td className="py-3 px-3 text-right font-medium tabular-nums">{sc.meanQueue}</td>
                        <td className="py-3 px-3 text-right font-medium tabular-nums">{sc.p95Wait} min</td>
                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded ${
                            sc.status === 'stable'
                              ? 'bg-emerald-50 text-emerald-700'
                              : sc.status === 'degraded'
                              ? 'bg-amber-50 text-amber-700'
                              : 'bg-red-50 text-red-700'
                          }`}>
                            {sc.status === 'stable' && <CheckCircle2 className="w-3 h-3" />}
                            {sc.status === 'degraded' && <AlertTriangle className="w-3 h-3" />}
                            {sc.status === 'critical' && <AlertTriangle className="w-3 h-3" />}
                            {sc.status.charAt(0).toUpperCase() + sc.status.slice(1)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
                <strong>Assessment:</strong> {stressResult.overallAssessment}
              </div>
            </div>
          )}

          {/* Model Attribution & Verification Disclaimer */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-500 flex items-start gap-3">
            <Building className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-700">
                Simulation Model Grounding Notice:
              </span>{' '}
              {fidelityNote || 'Results are deterministic planning estimates. SUMO is not installed.'}
            </div>
          </div>

          {/* Adoption CTA Footer */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-900">
                Ready to enact this schedule across the campus?
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Publishes new staggered arrival windows and gate passes to driver portals.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => onNavigate('schedule')}
                className="px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Review Other Plans
              </button>

              <button
                onClick={() => setShowAdoptSuccess(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors shadow-2xs focus-visible:outline-blue-600"
              >
                <FileCheck className="w-4 h-4" />
                <span>Publish as Official Schedule</span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* No simulation run yet, show prompt */}
      {!simResult && !isSimulating && !errorMessage && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center shadow-xs">
          <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
            <PlaySquare className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900 mt-4">
            Click "Run Simulation" to Test This Schedule
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1.5 leading-relaxed">
            The backend will run a deterministic queuing simulation comparing the selected plan against the baseline, then stress-test the plan under 6 scenarios.
          </p>
        </div>
      )}

      {/* Adoption Confirmation Modal */}
      {showAdoptSuccess && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 className="text-base font-bold text-slate-900">
                Official Schedule Published Successfully
              </h3>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                <strong className="font-semibold text-slate-800">{selectedCandidate.name}</strong> is now the active operational plan. Driver arrival windows have been updated.
              </p>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-600 space-y-1">
              <div className="flex justify-between">
                <span>Effective Date:</span>
                <span className="font-semibold text-slate-800">Immediately (Afternoon Bell)</span>
              </div>
              <div className="flex justify-between">
                <span>Data Source:</span>
                <span className="font-semibold text-amber-600">Synthetic / Demo</span>
              </div>
            </div>

            <div className="pt-2 flex gap-3">
              <button
                onClick={() => setShowAdoptSuccess(false)}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
