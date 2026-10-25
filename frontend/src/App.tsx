/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { UserRole, AdminTab } from './types';
import type { ScheduleCandidate } from './api/client';
import {
  clearAuthToken,
  getAuthToken,
  getCurrentUser,
  getMySchools,
  setSchoolContext,
  type AuthUser,
  type ManagedSchool,
} from './api/client';
import { LoginPage } from './pages/LoginPage';
import { ParentInvitationPage } from './pages/ParentInvitationPage';
import { ParentDashboard } from './pages/ParentDashboard';
import { SchoolManagementPage } from './pages/SchoolManagementPage';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { AdminDashboard } from './pages/AdminDashboard';
import { FindCausePage } from './pages/FindCausePage';
import { FindSchedulePage } from './pages/FindSchedulePage';
import { TestSchedulePage } from './pages/TestSchedulePage';
import { SchoolMapPage } from './pages/SchoolMapPage';
import { IntegrationStatus } from './components/IntegrationStatus';

export default function App() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [schools, setSchools] = useState<ManagedSchool[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<ManagedSchool | null>(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);
  const [currentAdminTab, setCurrentAdminTab] = useState<AdminTab>('overview');
  const [selectedCandidate, setSelectedCandidate] = useState<ScheduleCandidate | null>(null);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [accessError, setAccessError] = useState('');
  const [loginRole, setLoginRole] = useState<UserRole>('admin');
  const [inviteToken, setInviteToken] = useState<string | null>(() => new URLSearchParams(window.location.search).get('invite'));

  const loadMemberships = async (user: AuthUser) => {
    const authorized = await getMySchools();
    const allowed = user.role === 'admin' ? authorized.filter((school) => school.canManage) : authorized;
    setCurrentUser(user);
    setSchools(allowed);
    const previousSchoolId = sessionStorage.getItem('gateflow_school_context');
    const nextSchool = allowed.find((school) => school.id === previousSchoolId)
      ?? (allowed.length === 1 ? allowed[0] : null);
    setSelectedSchool(nextSchool);
    setSchoolContext(nextSchool?.id ?? null);
    setAccessError(allowed.length ? '' : user.role === 'parent'
      ? 'Your account has no active school memberships. Ask a school administrator to verify your account.'
      : 'No schools are assigned to this administrator account.');
  };

  useEffect(() => {
    if (inviteToken || !getAuthToken()) {
      setIsRestoringSession(false);
      return;
    }
    getCurrentUser()
      .then((user) => loadMemberships(user))
      .catch(() => clearAuthToken())
      .finally(() => setIsRestoringSession(false));
  }, []);

  const handleLogin = async (user: AuthUser) => {
    try {
      setAccessError('');
      await loadMemberships(user);
    } catch (cause) {
      clearAuthToken();
      setCurrentUser(null);
      setAccessError(cause instanceof Error ? cause.message : 'Could not load your authorized schools.');
      throw cause;
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    setCurrentUser(null);
    setSchools([]);
    setSelectedSchool(null);
    setCurrentAdminTab('overview');
  };

  const selectSchool = (school: ManagedSchool) => {
    if (!schools.some((authorized) => authorized.id === school.id)) return;
    if (selectedSchool?.id !== school.id) setSelectedCandidate(null);
    setSelectedSchool(school);
    setSchoolContext(school.id);
  };

  const updateSchool = (updated: ManagedSchool) => {
    setSchools((current) => current.map((school) => school.id === updated.id ? updated : school));
    if (selectedSchool?.id === updated.id) setSelectedSchool(updated);
  };

  const addSchool = (school: ManagedSchool) => {
    setSchools((current) => [...current, school]);
    setSelectedCandidate(null);
    setSelectedSchool(school);
    setSchoolContext(school.id);
  };

  const completeInvitation = () => {
    window.history.replaceState({}, '', window.location.pathname);
    setInviteToken(null);
    setLoginRole('parent');
  };

  if (inviteToken) return <ParentInvitationPage token={inviteToken} onComplete={completeInvitation} />;
  if (isRestoringSession) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">Restoring session...</div>;
  }
  if (!currentUser) return <LoginPage onLogin={handleLogin} initialRole={loginRole} />;

  if (accessError || schools.length === 0) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
        <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6">
          <h1 className="text-lg font-bold text-slate-900">School access unavailable</h1>
          <p role="alert" className="mt-2 text-sm text-slate-600">{accessError || 'No authorized schools were returned for this account.'}</p>
          <button onClick={handleLogout} className="mt-5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white">Sign out</button>
        </section>
      </main>
    );
  }

  if (!selectedSchool) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
        <section className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div><h1 className="text-xl font-bold text-slate-900">Choose a school</h1><p className="mt-1 text-sm text-slate-500">Only schools linked to your account are listed.</p></div>
            <button onClick={handleLogout} className="text-sm font-semibold text-blue-700">Sign out</button>
          </div>
          <div className="mt-5 space-y-2">
            {schools.map((school) => (
              <button key={school.id} onClick={() => selectSchool(school)} className="flex w-full items-center justify-between rounded-xl border border-slate-200 p-4 text-left hover:border-blue-300 hover:bg-blue-50">
                <span><span className="block font-semibold text-slate-900">{school.name}</span><span className="text-sm text-slate-500">{school.city}</span></span>
                <span className="text-xs font-mono text-slate-400">{school.id.slice(0, 8)}</span>
              </button>
            ))}
          </div>
        </section>
      </main>
    );
  }

  if (currentUser.role === 'parent') {
    return <ParentDashboard school={selectedSchool} schools={schools} onSelectSchool={selectSchool} onLogout={handleLogout} />;
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 font-sans text-slate-900 antialiased md:flex-row">
      <Sidebar
        currentTab={currentAdminTab}
        onSelectTab={setCurrentAdminTab}
        onLogout={handleLogout}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        school={selectedSchool}
        user={currentUser}
      />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <Header
          currentTab={currentAdminTab}
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          onLogout={handleLogout}
          school={selectedSchool}
          user={currentUser}
        />
        <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6 lg:p-8">
          {schools.length > 1 && (
            <label className="mb-4 flex flex-wrap items-center gap-2 text-sm font-medium text-slate-700">
              Active school
              <select value={selectedSchool.id} onChange={(event) => {
                const next = schools.find((school) => school.id === event.target.value);
                if (next) selectSchool(next);
              }} className="rounded-lg border border-slate-300 bg-white px-3 py-2">
                {schools.map((school) => <option key={school.id} value={school.id}>{school.name}</option>)}
              </select>
            </label>
          )}
          <div className="mb-4"><IntegrationStatus /></div>
          {!selectedSchool.trafficScenarioConfigured && currentAdminTab !== 'schools' && currentAdminTab !== 'map' ? (
            <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-5">
              <h2 className="font-semibold text-amber-950">Traffic scenario not configured</h2>
              <p className="mt-1 text-sm text-amber-900">This school has no traffic dataset configured. GateFlow will not reuse another school’s scenario or fabricate dashboard results.</p>
              <button onClick={() => setCurrentAdminTab('schools')} className="mt-3 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white">Open school settings</button>
            </div>
          ) : (
            <>
              {currentAdminTab === 'overview' && <AdminDashboard onNavigate={setCurrentAdminTab} />}
              {currentAdminTab === 'map' && <SchoolMapPage editable schoolId={selectedSchool.id} school={selectedSchool} onSchoolUpdated={updateSchool} />}
              {currentAdminTab === 'cause' && <FindCausePage onNavigate={setCurrentAdminTab} />}
              {currentAdminTab === 'schedule' && (
                <FindSchedulePage onNavigate={setCurrentAdminTab} selectedCandidate={selectedCandidate} onSelectCandidate={setSelectedCandidate} />
              )}
              {currentAdminTab === 'test' && <TestSchedulePage onNavigate={setCurrentAdminTab} selectedCandidate={selectedCandidate} />}
              {currentAdminTab === 'schools' && (
                <SchoolManagementPage school={selectedSchool} schools={schools} onSchoolUpdated={updateSchool} onSchoolCreated={addSchool} />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
