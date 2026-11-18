import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { Button } from '../components/Button';
import { Banner } from '../components/Banner';
import { useRole } from '../context';

export const LoginScreen: React.FC = () => {
  const navigate = useNavigate();
  const { currentRole } = useRole();
  const [email, setEmail] = useState('inspector@acme.com');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [hasError] = useState(true);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-[#0B1F5C] bg-[radial-gradient(ellipse_at_top,_#1F4FD8_0%,_#0B1F5C_60%,_#061138_100%)] text-[#0F172A] flex flex-col justify-between items-center py-8 sm:py-14 px-4 select-none">
      {/* Centered Branded Card Container */}
      <div className="w-full max-w-[460px] my-auto space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-[20px] bg-white/10 backdrop-blur-md shadow-xl text-white border border-white/25">
            <Shield className="w-7 h-7 text-[#60A5FA] stroke-[2.2]" />
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight leading-none">
            Lotline
          </h1>
          <p className="text-sm text-[#EAF0FF]/80 max-w-sm mx-auto font-normal">
            Acme Knitwear Ltd. · Factory Floor Inspection System
          </p>
        </div>

        {/* Main Login Card */}
        <div className="bg-white p-6 sm:p-8 rounded-[28px] border border-slate-200/90 shadow-2xl space-y-5 text-left">
          <div className="border-b border-[#F1F5F9] pb-3">
            <h2 className="text-lg font-bold text-[#0F172A]">Sign in to workstation</h2>
            <p className="text-xs text-[#64748B] mt-0.5">
              Enter your factory credentials to access Floor Line 2
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-1.5">
              <label className="text-[13px] font-bold text-[#0F172A]">Work Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@acme.com"
                className="w-full h-11 px-3.5 rounded-[12px] border border-[#CBD5E1] text-[14px] text-[#0F172A] bg-[#F8FAFC] focus:bg-white focus:outline-none focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF] transition-all"
              />
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[13px] font-bold text-[#0F172A]">Password</label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-xs font-semibold text-[#1F4FD8] hover:underline flex items-center gap-1"
                >
                  {showPassword ? (
                    <>
                      <EyeOff className="w-3.5 h-3.5" />
                      <span>Hide</span>
                    </>
                  ) : (
                    <>
                      <Eye className="w-3.5 h-3.5" />
                      <span>Show</span>
                    </>
                  )}
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`w-full h-11 px-3.5 rounded-[12px] text-[14px] text-[#0F172A] bg-[#F8FAFC] focus:bg-white focus:outline-none transition-all ${
                    hasError
                      ? 'border border-[#EF4444] focus:border-[#B91C1C] focus:ring-2 focus:ring-[#FEE2E2]'
                      : 'border border-[#CBD5E1] focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF]'
                  }`}
                />
              </div>
              {hasError && (
                <p className="text-[12px] font-semibold text-[#B91C1C] pt-0.5">
                  Email or password is incorrect.
                </p>
              )}
            </div>

            {/* Log in Button */}
            <Button
              type="submit"
              variant="primary"
              fullWidth
              size="lg"
              className="mt-2 font-bold"
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Sign In to Factory Floor
            </Button>
          </form>

          {/* Account Lockout Notice */}
          <Banner
            variant="warn"
            title="Account Lockout Protocol"
            description="Too many attempts. Try again in 12 min 40 s, or contact an Admin to unlock your inspector account."
          />

          {/* First Login Password Setup */}
          <div className="pt-3 border-t border-[#F1F5F9] space-y-2.5">
            <h3 className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
              First login? Set a new password
            </h3>
            <input
              type="password"
              placeholder="New password (15+ characters)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full h-10 px-3 rounded-[10px] border border-[#E2E8F0] text-xs placeholder:text-[#94A3B8] text-[#0F172A] bg-white focus:outline-none focus:border-[#1F4FD8]"
            />
            <p className="text-[11px] text-[#64748B]">Must not contain your email name.</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              fullWidth
              onClick={() => alert(`Password updated for ${currentRole}`)}
            >
              Change password
            </Button>
          </div>
        </div>

        {/* Footer Note */}
        <div className="text-center text-xs text-[#EAF0FF]/70">
          Governing principle: AI proposes defects. Humans confirm defects. Engine decides.
        </div>
      </div>
    </div>
  );
};
