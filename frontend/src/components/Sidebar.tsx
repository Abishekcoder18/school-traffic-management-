import React from 'react';
import {
  LayoutDashboard,
  Search,
  CalendarDays,
  PlaySquare,
  LogOut,
  ShieldCheck,
  X,
  Map,
  School,
} from 'lucide-react';
import { AdminTab } from '../types';
import type { AuthUser, ManagedSchool } from '../api/client';

interface SidebarProps {
  currentTab: AdminTab;
  onSelectTab: (tab: AdminTab) => void;
  onLogout: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
  school: ManagedSchool;
  user: AuthUser;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  onLogout,
  isMobileOpen,
  onCloseMobile,
  school,
  user,
}) => {
  const navItems: { id: AdminTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <LayoutDashboard className="w-4 h-4 shrink-0" />
    },
    {
      id: 'map',
      label: 'School Map',
      icon: <Map className="w-4 h-4 shrink-0" />
    },
    {
      id: 'cause',
      label: 'Find the Cause',
      icon: <Search className="w-4 h-4 shrink-0" />,
      badge: 'Bottleneck'
    },
    {
      id: 'schedule',
      label: 'Find a Better Schedule',
      icon: <CalendarDays className="w-4 h-4 shrink-0" />,
      badge: '3 Plans'
    },
    {
      id: 'test',
      label: 'Test the Schedule',
      icon: <PlaySquare className="w-4 h-4 shrink-0" />
    },
    {
      id: 'schools',
      label: 'School Management',
      icon: <School className="w-4 h-4 shrink-0" />
    }
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white border-r border-slate-200">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-slate-900 tracking-tight text-base flex items-center gap-1.5">
              GateFlow <span className="text-blue-600">AI</span>
            </div>
            <div className="text-[11px] text-slate-500 font-medium">
              School Traffic Control
            </div>
          </div>
        </div>

        {/* Mobile close button */}
        <button
          onClick={onCloseMobile}
          className="md:hidden text-slate-400 hover:text-slate-600 p-1.5 rounded-lg focus-visible:outline-blue-600"
          aria-label="Close navigation sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* School Badge Context */}
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-100">
        <div className="text-[11px] uppercase font-semibold text-slate-400 tracking-wider">
          Active Campus
        </div>
        <div className="text-xs font-semibold text-slate-800 truncate mt-0.5">
          {school.name}
        </div>
        <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0"></span>
          <span>{school.trafficScenarioConfigured ? 'Traffic scenario configured' : 'Traffic scenario not configured'}</span>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Core Workflows
        </div>

        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => {
                onSelectTab(item.id);
                onCloseMobile();
              }}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left focus-visible:outline-blue-600 ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={isActive ? 'text-blue-600' : 'text-slate-400'}>
                  {item.icon}
                </span>
                <span className="whitespace-nowrap">{item.label}</span>
              </div>

              {item.badge && (
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                    isActive
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Current user & Logout Footer */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/50">
        <div className="flex items-center justify-between px-2 py-1">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 font-semibold text-xs flex items-center justify-center shrink-0">
              {(user.full_name || user.email).slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold text-slate-800 truncate">
                {user.full_name || 'School Administrator'}
              </div>
              <div className="text-[11px] text-slate-500 truncate">
                {user.email}
              </div>
            </div>
          </div>

          <button
            onClick={onLogout}
            title="Sign Out"
            className="text-slate-400 hover:text-red-600 p-1.5 rounded-md transition-colors focus-visible:outline-blue-600"
            aria-label="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Persistent 260px) */}
      <aside className="hidden md:block w-64 shrink-0 h-screen sticky top-0 z-20">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex"
          onClick={onCloseMobile}
        >
          <div
            className="w-72 max-w-[80vw] h-full shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
