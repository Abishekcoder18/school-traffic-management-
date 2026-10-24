/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { UserRole, AdminTab } from './types';
import type { ScheduleCandidate } from './api/client';
import { LoginPage } from './pages/LoginPage';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { AdminDashboard } from './pages/AdminDashboard';
import { FindCausePage } from './pages/FindCausePage';
import { FindSchedulePage } from './pages/FindSchedulePage';
import { TestSchedulePage } from './pages/TestSchedulePage';
import { DriverDashboard } from './pages/DriverDashboard';

export default function App() {
  const [currentUserRole, setCurrentUserRole] = useState<UserRole | null>('admin');
  const [currentAdminTab, setCurrentAdminTab] = useState<AdminTab>('overview');
  const [selectedCandidate, setSelectedCandidate] = useState<ScheduleCandidate | null>(null);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Authentication Handlers
  const handleLogin = (role: UserRole) => {
    setCurrentUserRole(role);
    if (role === 'admin') {
      setCurrentAdminTab('overview');
    }
  };

  const handleLogout = () => {
    setCurrentUserRole(null);
  };

  // If not logged in, render Login Page
  if (!currentUserRole) {
    return <LoginPage onLogin={handleLogin} />;
  }

  // If Driver role, render dedicated Driver Dashboard (mobile-friendly, no admin sidebar)
  if (currentUserRole === 'driver') {
    return (
      <DriverDashboard
        onLogout={handleLogout}
      />
    );
  }

  // If School Administrator role, render full Admin console
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row text-slate-900 font-sans antialiased">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentAdminTab}
        onSelectTab={(tab) => setCurrentAdminTab(tab)}
        onLogout={handleLogout}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Administrative Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Administrator Header */}
        <Header
          currentTab={currentAdminTab}
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          onLogout={handleLogout}
        />

        {/* Dynamic Viewport */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {currentAdminTab === 'overview' && (
            <AdminDashboard onNavigate={(tab) => setCurrentAdminTab(tab)} />
          )}

          {currentAdminTab === 'cause' && (
            <FindCausePage onNavigate={(tab) => setCurrentAdminTab(tab)} />
          )}

          {currentAdminTab === 'schedule' && (
            <FindSchedulePage
              onNavigate={(tab) => setCurrentAdminTab(tab)}
              selectedCandidate={selectedCandidate}
              onSelectCandidate={(cand) => setSelectedCandidate(cand)}
            />
          )}

          {currentAdminTab === 'test' && (
            <TestSchedulePage
              onNavigate={(tab) => setCurrentAdminTab(tab)}
              selectedCandidate={selectedCandidate}
            />
          )}
        </main>
      </div>
    </div>
  );
}
