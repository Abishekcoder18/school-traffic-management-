import React, { useState } from 'react';
import {
  Car,
  Clock,
  MapPin,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Navigation,
  LogOut,
  Info,
  Calendar,
  PhoneCall,
  RotateCcw
} from 'lucide-react';
import { DriverAssignment } from '../types';
import { INITIAL_DRIVER_ASSIGNMENT, SCHOOL_PROFILE } from '../data/mockData';

interface DriverDashboardProps {
  onLogout: () => void;
}

export const DriverDashboard: React.FC<DriverDashboardProps> = ({
  onLogout
}) => {
  const [assignment, setAssignment] = useState<DriverAssignment>(INITIAL_DRIVER_ASSIGNMENT);
  const [hasNoSchedule, setHasNoSchedule] = useState<boolean>(false);
  const [isCheckedIn, setIsCheckedIn] = useState<boolean>(false);
  const [checkInTime, setCheckInTime] = useState<string>('');

  const handleCheckIn = () => {
    setIsCheckedIn(true);
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setCheckInTime(timeStr);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Mobile-Friendly Driver Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20 px-4 py-3.5 shadow-2xs">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-2xs">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
                GateFlow <span className="text-blue-600">Driver</span>
              </div>
              <div className="text-[11px] text-slate-500 font-medium">
                {SCHOOL_PROFILE.name.split('&')[0]}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Toggle empty state for testing */}
            <button
              onClick={() => setHasNoSchedule(!hasNoSchedule)}
              className="text-[11px] px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition-colors"
              title="Toggle to view empty state when no schedule is active"
            >
              {hasNoSchedule ? 'View Active Pass' : 'Test Empty State'}
            </button>

            {/* Logout */}
            <button
              onClick={onLogout}
              className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg transition-colors"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-2xl w-full mx-auto p-4 sm:p-6 space-y-4">
        {hasNoSchedule ? (
          /* Empty State */
          <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center space-y-4 shadow-xs mt-4">
            <div className="w-14 h-14 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Calendar className="w-7 h-7" />
            </div>

            <div>
              <h2 className="text-lg font-bold text-slate-900">
                No Active Pickup Schedule Assigned
              </h2>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 leading-relaxed">
                There are no scheduled dismissals or gate passes linked to your registered student profile at this time.
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 text-left text-xs space-y-1.5 text-slate-600">
              <div className="font-semibold text-slate-800">Need immediate assistance?</div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                <span>Regular schedules are published by 1:00 PM daily</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                <span>Contact School Office: {SCHOOL_PROFILE.schoolContactPhone}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-center gap-3">
              <button
                onClick={() => setHasNoSchedule(false)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-2xs"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reload Assigned Schedule</span>
              </button>
            </div>
          </div>
        ) : (
          /* Populated Driver Schedule */
          <>
            {/* Student & Vehicle Banner */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs flex items-center justify-between">
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Registered Student
                </div>
                <div className="text-sm font-bold text-slate-900 mt-0.5">
                  {assignment.studentName}
                </div>
                <div className="text-xs text-slate-500">
                  {assignment.grade} · {assignment.vehiclePlate}
                </div>
              </div>

              <div className="text-right">
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3" />
                  {isCheckedIn ? 'Checked-In' : assignment.assignmentStatus}
                </span>
                <div className="text-[10px] text-slate-400 mt-1">
                  {assignment.date}
                </div>
              </div>
            </div>

            {/* Crucial Arrival & Gate Details - High Visibility Card */}
            <div className="bg-blue-600 text-white rounded-2xl p-5 sm:p-6 shadow-md relative overflow-hidden">
              {/* Background ambient badge */}
              <div className="text-xs font-bold uppercase tracking-wider text-blue-200 flex items-center justify-between mb-3">
                <span>Assigned Dismissal Pass</span>
                <span>Afternoon Session</span>
              </div>

              {/* Large Arrival Window */}
              <div className="mb-4">
                <div className="text-xs text-blue-100 flex items-center gap-1.5 mb-1">
                  <Clock className="w-4 h-4 text-blue-200" />
                  <span>Target Arrival Window</span>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold tracking-tight tabular-nums">
                  {assignment.arrivalWindow}
                </div>
                <div className="text-xs text-blue-100 mt-0.5">
                  Official Dismissal Bell: <strong className="font-semibold text-white">{assignment.officialSlot}</strong>
                </div>
              </div>

              {/* Gate & Pickup Zone */}
              <div className="pt-4 border-t border-blue-500/60 grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-blue-200">Assigned Gate</div>
                  <div className="text-base sm:text-lg font-bold text-white mt-0.5">
                    {assignment.gateNumber}
                  </div>
                  <div className="text-xs text-blue-100">
                    {assignment.gateName.split('—')[1]}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-blue-200">Zone & Bay</div>
                  <div className="text-base sm:text-lg font-bold text-white mt-0.5">
                    {assignment.bayNumber}
                  </div>
                  <div className="inline-block text-[11px] font-semibold bg-white text-blue-700 px-2 py-0.5 rounded mt-0.5">
                    {assignment.laneColor}
                  </div>
                </div>
              </div>
            </div>

            {/* Arrival Check-In Action Button */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-bold text-slate-800">
                    Live Gate 2 Queue Status
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {assignment.queueStatus}
                  </p>
                </div>

                {isCheckedIn ? (
                  <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Arrived & Staged at {checkInTime}</span>
                  </div>
                ) : (
                  <button
                    onClick={handleCheckIn}
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors shadow-2xs focus-visible:outline-blue-600"
                  >
                    <MapPin className="w-4 h-4" />
                    <span>I Have Arrived at Gate 2</span>
                  </button>
                )}
              </div>
            </div>

            {/* Turn-by-Turn Route Instructions */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <Navigation className="w-4 h-4 text-blue-600" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Designated Approach Route
                </h3>
              </div>

              <div className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200/70">
                {assignment.routeInstructions}
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                <span>Entry Corridor: {assignment.approachStreet}</span>
                <span className="text-blue-600 font-medium">Follow Green Signs</span>
              </div>
            </div>

            {/* Driver Instructions Checklist */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-2xs space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <FileText className="w-4 h-4 text-slate-600" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Important Driver Instructions
                </h3>
              </div>

              <div className="space-y-2.5">
                {assignment.instructions.map((inst, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-600">
                    <span className="w-4 h-4 rounded-full bg-slate-100 text-slate-700 font-semibold text-[10px] flex items-center justify-center shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed">{inst}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* School Notices & Advisory */}
            <div className="space-y-2">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
                Campus Notices
              </div>

              {assignment.notices.map((notice, idx) => (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border text-xs ${
                    notice.type === 'advisory'
                      ? 'bg-amber-50/70 border-amber-200 text-amber-900'
                      : 'bg-blue-50/70 border-blue-200 text-blue-900'
                  }`}
                >
                  <div className="font-bold flex items-center gap-1.5 mb-1">
                    {notice.type === 'advisory' ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    ) : (
                      <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                    )}
                    <span>{notice.title}</span>
                  </div>
                  <p className="text-slate-700 leading-relaxed">
                    {notice.message}
                  </p>
                </div>
              ))}
            </div>

            {/* Support Footer */}
            <div className="pt-4 text-center text-xs text-slate-400">
              Need assistance? Call campus safety at {SCHOOL_PROFILE.schoolContactPhone}
            </div>
          </>
        )}
      </main>
    </div>
  );
};
