import React, { useState } from 'react';
import { useRole } from '../context';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Smartphone, X } from 'lucide-react';
import type { UserRole } from '../mocks';

export const DevToolbar: React.FC = () => {
  const { currentRole, setRole } = useRole();
  const navigate = useNavigate();
  const location = useLocation();
  // Collapsed by default as requested
  const [isOpen, setIsOpen] = useState(false);

  const roles: UserRole[] = ['Inspector', 'Supervisor', 'Admin'];

  const screens = [
    { path: '/login', label: '1. Login' },
    { path: '/dashboard', label: '2. Dashboard' },
    { path: '/lots', label: '3. Lot List' },
    { path: '/lots/new', label: '4. Create Lot' },
    { path: '/lots/LT-2411-018', label: '5. Lot Details' },
    { path: '/lots/LT-2411-018/plan', label: '6. Plan' },
    { path: '/lots/LT-2411-018/capture', label: '7. Capture' },
    { path: '/lots/LT-2411-018/review', label: '8. Review' },
    { path: '/lots/LT-2411-018/defect-confirm/prop-1', label: '9. Defect' },
    { path: '/lots/LT-2411-018/decision', label: '10. Decision' },
    { path: '/lots/LT-2411-018/report', label: '11. Report' },
    { path: '/admin', label: 'Admin (12-17)' },
    { path: '/design-system', label: 'Design System' },
  ];

  return (
    <aside
      aria-label="Dev Toolbar"
      className="fixed top-3 right-3 z-50 select-none print:hidden"
    >
      {!isOpen ? (
        /* Collapsed Floating Pill Button at Top-Right Corner */
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#0B1F5C] text-white text-[11.5px] font-bold shadow-lg border border-white/25 hover:bg-[#122B78] hover:scale-105 active:scale-95 transition-all cursor-pointer backdrop-blur-md"
          title="Open Dev Switcher (Role & Screen navigation)"
        >
          <Shield className="w-3.5 h-3.5 text-[#60A5FA]" />
          <span>Dev:</span>
          <span className="bg-[#1F4FD8] px-1.5 py-0.2 rounded text-[10.5px]">
            {currentRole}
          </span>
        </button>
      ) : (
        /* Expanded Floating Card at Top-Right Corner */
        <div className="w-[320px] max-w-[calc(100vw-24px)] bg-[#0B1F5C] text-white rounded-2xl shadow-2xl border border-white/20 p-3.5 backdrop-blur-md animate-in fade-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider bg-[#1F4FD8] px-2 py-0.5 rounded-full">
                <Shield className="w-3 h-3" />
                Dev Switcher
              </span>
              <span className="text-[11px] text-white/70">Role & Nav</span>
            </div>

            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              title="Close Dev Switcher"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="pt-3 space-y-3">
            {/* Role Switcher */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-white/60 mb-1.5">
                Current Role
              </div>
              <div className="grid grid-cols-3 gap-1.5 text-xs">
                {roles.map((r) => {
                  const isSelected = currentRole === r;
                  return (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setRole(r)}
                      className={`py-1.5 px-2 rounded-lg font-semibold text-center transition-all ${
                        isSelected
                          ? 'bg-white text-[#0B1F5C] shadow-sm'
                          : 'bg-white/10 text-white/80 hover:bg-white/20'
                      }`}
                    >
                      {r}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Quick Screen Switcher */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-white/60 mb-1.5 flex items-center gap-1">
                <Smartphone className="w-3 h-3" />
                Jump to Screen
              </div>
              <div className="grid grid-cols-2 gap-1.5 text-xs max-h-[220px] overflow-y-auto pr-1">
                {screens.map((s) => {
                  const isCurrent = location.pathname === s.path;
                  return (
                    <button
                      key={s.path}
                      type="button"
                      onClick={() => {
                        navigate(s.path);
                        setIsOpen(false);
                      }}
                      className={`py-1.5 px-2 rounded-lg font-medium text-left truncate transition-all ${
                        isCurrent
                          ? 'bg-[#1F4FD8] text-white font-bold'
                          : 'bg-white/10 text-white/80 hover:bg-white/20'
                      }`}
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
