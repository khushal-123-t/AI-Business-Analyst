import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, Lock, Mail, TrendingUp, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function Login() {
  const [searchParams] = useSearchParams();
  const isExpired = searchParams.get('expired') === '1' || searchParams.get('session_expired') === '1';
  const isRegistered = searchParams.get('registered') === '1';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await api.login(email.trim(), password);
      if (data.role === 'ADMIN') {
        navigate('/admin/dashboard');
      } else {
        navigate('/client/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-[#070a13] p-4 relative overflow-hidden">
      {/* Dynamic Background Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-indigo-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-violet-600/10 blur-[120px] pointer-events-none" />
      
      <div className="w-full max-w-md glass-panel p-8 sm:p-9 rounded-2xl border border-slate-800/80 shadow-2xl relative z-10 space-y-7 my-8">
        {/* Branding header */}
        <div className="text-center space-y-3">
          <a href="/" className="inline-block group cursor-pointer">
            <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center mx-auto shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-200">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
          </a>
          <div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">AI Business Analyst</h1>
            <p className="text-xs text-slate-400 font-medium mt-1">Enterprise Business Intelligence & SQL Analytics</p>
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {isRegistered && (
            <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs rounded-xl text-center font-medium">
              Account created successfully! Please sign in with your credentials.
            </div>
          )}

          {isExpired && (
            <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs rounded-xl text-center font-medium">
              Your session has expired. Please sign in again to continue.
            </div>
          )}

          {error && (
            <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl text-center font-medium animate-shake">
              {error}
            </div>
          )}

          {/* Email input field */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
              Email Address
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Mail className="h-4.5 w-4.5" />
              </span>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full pl-11 pr-4 py-3 bg-[#0d1222]/60 border border-slate-800 rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all font-medium"
              />
            </div>
          </div>

          {/* Password input field */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Password
              </label>
              <a
                href="#forgot"
                onClick={(e) => {
                  e.preventDefault();
                  alert('Password recovery is handled by your system administrator.');
                }}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition"
              >
                Forgot Password?
              </a>
            </div>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Lock className="h-4.5 w-4.5" />
              </span>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-11 pr-11 py-3 bg-[#0d1222]/60 border border-slate-800 rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all font-medium"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition"
              >
                {showPassword ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            id="login-submit"
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 focus:outline-none shadow-lg shadow-indigo-600/20 hover:shadow-indigo-500/30 active:scale-[0.98] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
          >
            {loading ? (
              <>
                <Loader2 className="h-4.5 w-4.5 animate-spin" />
                Signing in...
              </>
            ) : (
              'Login'
            )}
          </button>
        </form>

        {/* Sign Up link */}
        <div className="text-center -mt-1">
          <p className="text-xs text-slate-400">
            Don't have an account?{' '}
            <a
              href="/signup"
              onClick={(e) => {
                e.preventDefault();
                navigate('/signup');
              }}
              className="text-indigo-400 hover:text-indigo-300 font-semibold transition cursor-pointer"
            >
              Sign Up
            </a>
          </p>
        </div>

        <div className="pt-2 text-center space-y-2.5">
          <p className="text-[11px] text-slate-400 font-medium">Quick Demo Sign-In:</p>
          <div className="flex gap-2 justify-center">
            <button
              type="button"
              onClick={() => {
                setEmail('client1@example.com');
                setPassword('client123');
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 transition-all cursor-pointer"
            >
              Fill Client (client1)
            </button>
            <button
              type="button"
              onClick={() => {
                setEmail('admin@example.com');
                setPassword('admin123');
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 text-purple-300 transition-all cursor-pointer"
            >
              Fill Admin (admin)
            </button>
          </div>
          <div className="text-[10px] text-slate-500">
            Client: <span className="font-semibold text-slate-400">client1@example.com / client123</span> | Admin: <span className="font-semibold text-slate-400">admin@example.com / admin123</span>
          </div>
        </div>
      </div>
    </div>
  );
}
