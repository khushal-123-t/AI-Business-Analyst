import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { Client, User } from '../types';
import { 
  User as UserIcon, Building2, Lock, ShieldCheck, 
  Loader2, CheckCircle2, AlertTriangle 
} from 'lucide-react';

export default function ClientProfile() {
  const [user, setUser] = useState<User | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form States
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [industry, setIndustry] = useState('');
  
  // Password Reset States
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passError, setPassError] = useState<string | null>(null);

  const [formLoading, setFormLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getClientProfile();
      setUser(res.user);
      setClient(res.client || null);
      
      setName(res.user.name);
      setEmail(res.user.email);
      if (res.client) {
        setPhone(res.client.phone || '');
        setIndustry(res.client.industry || '');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load user profile.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      setError('Name and Email are required.');
      return;
    }

    setFormLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await api.updateClientProfile({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        industry: industry.trim()
      });
      setUser(res.user);
      setClient(res.client || null);
      setSuccessMsg('Profile details updated successfully!');
      
      // Update sidebar username if changed
      localStorage.setItem('userName', res.user.name);
      window.dispatchEvent(new Event('userNameChanged'));
    } catch (err: any) {
      setError(err.message || 'Failed to update profile settings.');
    } finally {
      setFormLoading(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) {
      setPassError('Password cannot be empty.');
      return;
    }
    if (password !== confirmPassword) {
      setPassError('Passwords do not match.');
      return;
    }

    setFormLoading(true);
    setPassError(null);
    setSuccessMsg(null);

    try {
      await api.updateClientProfile({ password });
      setSuccessMsg('Password changed successfully!');
      setPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPassError(err.message || 'Failed to update password.');
    } finally {
      setFormLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-400 font-semibold">Retrieving profile statistics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">Account Settings</h2>
        <p className="text-xs text-slate-400 font-medium">Manage credentials, contact representatives, and subscription metadata</p>
      </div>

      {/* Main Alert notifications */}
      {successMsg && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl font-semibold flex items-center gap-2 max-w-4xl mx-auto">
          <CheckCircle2 className="h-4.5 w-4.5" />
          {successMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-6xl mx-auto items-start">
        {/* Profile Card & Password settings */}
        <div className="lg:col-span-2 space-y-8">
          {/* Main Info Form */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-6">
            <div className="flex items-center gap-2.5 border-b border-slate-800/80 pb-3 text-slate-200">
              <UserIcon className="h-4.5 w-4.5 text-indigo-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider">Contact Profile Details</h3>
            </div>
            
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              {error && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Contact Name</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Email Address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Phone Number</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Industry</label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end border-t border-slate-800/80">
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-lg text-xs font-semibold shadow transition cursor-pointer"
                >
                  {formLoading ? 'Saving...' : 'Update Details'}
                </button>
              </div>
            </form>
          </div>

          {/* Change Password Form */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-6">
            <div className="flex items-center gap-2.5 border-b border-slate-800/80 pb-3 text-slate-200">
              <Lock className="h-4.5 w-4.5 text-indigo-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider">Change Password</h3>
            </div>
            
            <form onSubmit={handleUpdatePassword} className="space-y-4">
              {passError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{passError}</span>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">New Password</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Confirm New Password</label>
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end border-t border-slate-800/80">
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50"
                >
                  {formLoading ? 'Resetting...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Company profile summary details card */}
        {client && (
          <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-5">
            <div className="flex items-center gap-2.5 border-b border-slate-800/80 pb-3 text-slate-200">
              <Building2 className="h-4.5 w-4.5 text-indigo-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider">Company Subscriptions</h3>
            </div>
            <div className="space-y-4 text-xs font-semibold">
              <div className="flex justify-between">
                <span className="text-slate-500">Company Name</span>
                <span className="text-slate-350">{client.company_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Service Plan</span>
                <span className="px-2.5 py-0.5 rounded border border-slate-700 bg-slate-800 text-[10px] uppercase font-bold text-indigo-400">
                  {client.plan}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Tenant Status</span>
                <span className="flex items-center gap-1 text-[10px] uppercase font-bold text-emerald-400">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Active Profile
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Account Created</span>
                <span className="text-slate-400">{new Date(client.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
