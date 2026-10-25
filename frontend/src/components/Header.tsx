import React, { useState, useRef, useEffect } from 'react';
import {
  Menu,
  Bell,
  Clock,
  ChevronDown,
  LogOut,
  CheckCircle2,
  AlertTriangle,
  Info
} from 'lucide-react';
import { AdminTab } from '../types';
import { SYSTEM_NOTIFICATIONS } from '../data/mockData';
import type { AuthUser, ManagedSchool } from '../api/client';

interface HeaderProps {
  currentTab: AdminTab;
  onOpenMobileSidebar: () => void;
  onLogout: () => void;
  school: ManagedSchool;
  user: AuthUser;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onOpenMobileSidebar,
  onLogout,
  school,
  user,
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  // Close popovers on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getBreadcrumbTitle = () => {
    switch (currentTab) {
      case 'overview':
        return 'School Traffic Overview';
      case 'map':
        return 'Chennai School Map';
      case 'cause':
        return 'Bottleneck Diagnostic & Root Cause';
      case 'schedule':
        return 'Schedule Optimization & Candidate Selection';
      case 'test':
        return 'Simulation Verification & Comparison';
      case 'schools':
        return 'School Management & Parent Access';
      default:
        return 'Dashboard';
    }
  };

  return (
    <header className="sticky top-0 z-10 bg-white border-b border-slate-200 px-4 md:px-8 py-3.5 flex items-center justify-between gap-4">
      {/* Left: Mobile hamburger + Breadcrumbs */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onOpenMobileSidebar}
          className="md:hidden p-2 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100 focus-visible:outline-blue-600"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
            <span>Administrator</span>
            <span>/</span>
            <span className="text-slate-600">{school.name}</span>
          </div>
          <h1 className="text-base md:text-lg font-bold text-slate-900 truncate">
            {getBreadcrumbTitle()}
          </h1>
        </div>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2 md:gap-3 shrink-0">
        {/* Session Badge */}
        <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-600">
          <Clock className="w-3.5 h-3.5 text-blue-600" />
          <span>{school.activeSession || 'School traffic session'}</span>
        </div>

        {/* Notifications Popover */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors focus-visible:outline-blue-600"
            aria-label="View notifications"
            aria-expanded={showNotifications}
          >
            <Bell className="w-4 h-4" />
            {school.trafficScenarioConfigured && <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-600 ring-2 ring-white"></span>}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 md:w-96 bg-white border border-slate-200 rounded-xl shadow-lg z-50 p-0 overflow-hidden animate-in fade-in duration-150">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
                <div className="text-xs font-semibold text-slate-800">
                  Scenario Notes
                </div>
                <span className="text-[11px] text-blue-600 font-medium">
                  Synthetic
                </span>
              </div>

              <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
                {school.trafficScenarioConfigured ? SYSTEM_NOTIFICATIONS.map((item) => (
                  <div key={item.id} className="p-3.5 hover:bg-slate-50 transition-colors">
                    <div className="flex items-start gap-2.5">
                      {item.type === 'alert' && (
                        <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                      )}
                      {item.type === 'success' && (
                        <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0 mt-0.5" />
                      )}
                      {item.type === 'info' && (
                        <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                      )}

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-xs font-semibold text-slate-800">
                            {item.title}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {item.time}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {item.detail}
                        </p>
                      </div>
                    </div>
                  </div>
                )) : <p className="p-4 text-xs text-slate-500">No notifications are configured for this school.</p>}
              </div>

              <div className="p-2 border-t border-slate-100 bg-slate-50 text-center">
                <span className="text-[11px] text-slate-500">
                  Static demo data · no physical sensor feed connected
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Profile Dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="flex items-center gap-2 p-1.5 md:px-2.5 md:py-1.5 border border-slate-200 rounded-lg hover:border-slate-300 bg-white transition-colors focus-visible:outline-blue-600"
            aria-label="User menu"
            aria-expanded={showProfileMenu}
          >
            <div className="w-6 h-6 rounded-full bg-blue-600 text-white font-semibold text-xs flex items-center justify-center shrink-0">
              {(user.full_name || user.email).slice(0, 1).toUpperCase()}
            </div>
            <span className="hidden sm:inline text-xs font-medium text-slate-700">
              {user.full_name || 'Admin Console'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {showProfileMenu && (
            <div className="absolute right-0 mt-2 w-56 bg-white border border-slate-200 rounded-xl shadow-lg z-50 p-1.5 overflow-hidden animate-in fade-in duration-150">
              <div className="px-3 py-2 border-b border-slate-100">
                <div className="text-xs font-semibold text-slate-800">
                  {user.full_name || 'School Administrator'}
                </div>
                <div className="text-[11px] text-slate-500 truncate">
                  {user.email}
                </div>
              </div>

              <div className="py-1">
                <button
                  onClick={() => {
                    setShowProfileMenu(false);
                    onLogout();
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-red-600 hover:bg-red-50 rounded-md transition-colors text-left"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
