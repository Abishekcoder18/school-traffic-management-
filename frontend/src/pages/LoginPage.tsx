import React, { useState } from 'react';
import { Eye, EyeOff, ShieldCheck, ArrowRight, UserCheck, AlertCircle, UsersRound } from 'lucide-react';
import { UserRole } from '../types';
import { IntegrationStatus } from '../components/IntegrationStatus';
import { AuthUser, clearAuthToken, login } from '../api/client';

interface LoginPageProps {
  onLogin: (user: AuthUser) => Promise<void>;
  initialRole?: UserRole;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin, initialRole = 'admin' }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [selectedRole, setSelectedRole] = useState<UserRole>(initialRole);
  const [rememberTerminal, setRememberTerminal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const selectRole = (role: UserRole) => {
    setSelectedRole(role);
    setErrorMessage('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please provide both email address and password.');
      return;
    }

    if (!email.includes('@')) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await login(email.trim(), password, rememberTerminal);
      if (user.role !== selectedRole) {
        clearAuthToken();
        setErrorMessage(`This account is registered as ${user.role}. Select the matching sign-in portal.`);
        return;
      }
      await onLogin(user);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Sign-in failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Brand Lockup */}
        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md">
            <ShieldCheck className="w-7 h-7" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-extrabold text-slate-900 tracking-tight">
          GateFlow <span className="text-blue-600">AI</span>
        </h2>
        <p className="mt-1 text-center text-xs text-slate-500">
          Intelligent School Traffic & Gate Management Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 sm:rounded-2xl sm:px-10">
          {/* Role Segmented Selector */}
          <div className="mb-6">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Select Sign-In Portal
            </label>
            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-xl">
              <button
                type="button"
                onClick={() => selectRole('admin')}
                className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all focus-visible:outline-blue-600 ${
                  selectedRole === 'admin'
                    ? 'bg-white text-blue-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <UserCheck className="w-4 h-4 text-blue-600" />
                <span>School Administrator</span>
              </button>

              <button
                type="button"
                onClick={() => selectRole('parent')}
                className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all focus-visible:outline-blue-600 ${
                  selectedRole === 'parent'
                    ? 'bg-white text-blue-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <UsersRound className="w-4 h-4 text-blue-600" />
                <span>Parent</span>
              </button>
            </div>
            <p className="mt-2 text-[11px] text-slate-400">
              {selectedRole === 'admin'
                ? 'Access to traffic diagnostics, schedule optimization, simulation, and map editing.'
                : 'View pickup details only for schools linked to your verified parent account.'}
            </p>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2.5 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-medium text-slate-700 mb-1"
              >
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                placeholder="name@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-medium text-slate-700 mb-1"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full px-3.5 py-2.5 pr-10 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
                  placeholder="••••••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center text-xs text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberTerminal}
                  onChange={(event) => setRememberTerminal(event.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 mr-2"
                />
                Remember this terminal
              </label>

              <span className="text-xs text-slate-500">School access is verified after sign-in.</span>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 transition-colors disabled:opacity-70"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <>
                    <span>Sign In as {selectedRole === 'admin' ? 'School Administrator' : 'Parent'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        <div className="mt-4">
          <IntegrationStatus />
        </div>

        <p className="mt-4 text-center text-xs text-slate-400">
          GateFlow AI Traffic Platform · District 7 Oakridge Campus Safety Group
        </p>
      </div>
    </div>
  );
};
