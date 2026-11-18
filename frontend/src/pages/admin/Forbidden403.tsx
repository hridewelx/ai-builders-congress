import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { Button } from '../../components/Button';

export const Forbidden403: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-[520px] flex flex-col items-center justify-center p-8 text-center max-w-lg mx-auto">
      <div className="w-16 h-16 rounded-2xl bg-[#FEE2E2] flex items-center justify-center text-[#B91C1C] mb-4 shadow-sm">
        <ShieldAlert className="w-8 h-8 stroke-[2.2]" />
      </div>

      <h1 className="text-3xl font-black text-[#0F172A] tracking-tight mb-2">403 Forbidden</h1>

      <p className="text-[14px] text-[#64748B] leading-relaxed mb-6">
        Access denied. The Admin Panel is restricted to <strong>Administrators</strong> and{' '}
        <strong>Supervisors</strong> (Audit view only). Your current role is <strong>Inspector</strong>.
      </p>

      <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-2.5 mb-6 text-xs text-[#64748B] font-mono">
        Request ID: req_admin_403_access_denied
      </div>

      <div className="flex gap-3">
        <Button variant="primary" onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </Button>
      </div>
    </div>
  );
};
