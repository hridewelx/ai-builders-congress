import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ListFilter,
  PlusCircle,
  Shield,
  User,
  Palette,
  Home,
  List,
  Plus,
  X,
  LogOut,
  Building2,
  CheckCircle2,
} from 'lucide-react';
import { useRole } from '../../context';

export const AppLayout: React.FC = () => {
  const { currentRole } = useRole();
  const navigate = useNavigate();
  const location = useLocation();
  const [isAccountOpen, setIsAccountOpen] = useState(false);

  // Email and user info mapping based on role
  const userMap = {
    Admin: { name: 'Admin User', email: 'admin@acme.com' },
    Supervisor: { name: 'Karim Rahman', email: 'karim@acme.com' },
    Inspector: { name: 'Rahim Khan', email: 'inspector@acme.com' },
  };

  const currentUser = userMap[currentRole] || userMap.Inspector;

  // Rule: New lot is hidden for Admin per section 3
  const isNewLotAllowed = currentRole !== 'Admin';

  // Rule: Admin if allowed (Admin sees all 6 tabs, Supervisor sees Audit tab, Inspector sees 403)
  const isAdminAllowed = currentRole === 'Admin' || currentRole === 'Supervisor';

  // Desktop sidebar navigation items
  const navItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
      show: true,
    },
    {
      id: 'lots',
      label: 'Lots',
      path: '/lots',
      icon: ListFilter,
      show: true,
    },
    {
      id: 'new-lot',
      label: 'New lot',
      path: '/lots/new',
      icon: PlusCircle,
      show: isNewLotAllowed,
    },
    {
      id: 'admin',
      label: 'Admin',
      path: '/admin',
      icon: Shield,
      show: isAdminAllowed,
    },
    {
      id: 'design-system',
      label: 'Design System',
      path: '/design-system',
      icon: Palette,
      show: true,
    },
  ];

  // Mobile bottom tab bar items (under 768px)
  const mobileTabs = [
    {
      id: 'home',
      label: 'Home',
      path: '/dashboard',
      icon: Home,
      show: true,
    },
    {
      id: 'lots',
      label: 'Lots',
      path: '/lots',
      icon: List,
      show: true,
    },
    {
      id: 'new-lot',
      label: 'New lot',
      path: '/lots/new',
      icon: Plus,
      show: isNewLotAllowed,
    },
    {
      id: 'admin',
      label: 'Admin',
      path: '/admin',
      icon: Shield,
      show: isAdminAllowed,
    },
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans text-[#0F172A]">
      {/* ========================================================= */}
      {/* TOP BAR: Org name, user and role badge                     */}
      {/* ========================================================= */}
      <header className="sticky top-0 z-40 bg-[#0B1F5C] text-white px-4 sm:px-6 h-[58px] flex items-center justify-between shadow-md select-none border-b border-[#0B1F5C]">
        {/* Left: Brand & Organization */}
        <div className="flex items-center gap-3.5">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2.5 focus:outline-none group text-left"
          >
            <div className="w-8 h-8 rounded-lg bg-[#1F4FD8] flex items-center justify-center text-white shadow-xs group-hover:bg-[#1a44bc] transition-colors">
              <Shield className="w-4 h-4 stroke-[2.4]" />
            </div>
            <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-2">
              <span className="text-[17px] font-black tracking-tight leading-none text-white">
                Lotline
              </span>
              <span className="text-[11px] sm:text-[12.5px] text-[#EAF0FF]/80 leading-none">
                Acme Knitwear Ltd.
              </span>
            </div>
          </button>
        </div>

        {/* Right: User, Role Badge, and Account Toggle (with pr-24 for floating Dev Switcher) */}
        <div className="flex items-center gap-2.5 sm:gap-3 pr-24 sm:pr-28">
          {/* User Info (hidden on tiny screens) */}
          <div className="hidden sm:flex flex-col text-right">
            <span className="text-[13px] font-semibold text-white leading-tight">
              {currentUser.name}
            </span>
            <span className="text-[11px] text-white/70 font-mono leading-tight">
              {currentUser.email}
            </span>
          </div>

          {/* Role Badge (Token: Navy #0B1F5C with high-contrast pill) */}
          <span
            className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
              currentRole === 'Admin'
                ? 'bg-purple-500/30 text-purple-200 border border-purple-400/40'
                : currentRole === 'Supervisor'
                ? 'bg-amber-500/30 text-amber-200 border border-amber-400/40'
                : 'bg-[#1F4FD8]/40 text-[#EAF0FF] border border-[#1F4FD8]/60'
            }`}
          >
            {currentRole}
          </span>

          {/* Account Profile Button */}
          <button
            type="button"
            onClick={() => setIsAccountOpen(true)}
            aria-label="Account details"
            className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 active:bg-white/30 text-white flex items-center justify-center transition-colors border border-white/20"
            title="Account profile"
          >
            <User className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* ========================================================= */}
      {/* DESKTOP BODY: Left Sidebar + Fluid Main Content Area      */}
      {/* ========================================================= */}
      <div className="flex-1 flex flex-row min-h-[calc(100vh-58px)] relative">
        {/* DESKTOP LEFT SIDEBAR (>= 768px) */}
        <aside
          aria-label="Desktop Navigation Sidebar"
          className="hidden md:flex flex-col justify-between w-60 bg-white border-r border-[#E2E8F0] p-4 select-none shrink-0 sticky top-[58px] h-[calc(100vh-58px)] overflow-y-auto"
        >
          <div className="space-y-6">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] px-3 mb-2">
                Factory Floor Menu
              </div>

              <nav className="space-y-1">
                {navItems
                  .filter((item) => item.show)
                  .map((item) => {
                    const isActive =
                      item.path === '/dashboard'
                        ? location.pathname === '/dashboard'
                        : location.pathname.startsWith(item.path);
                    const Icon = item.icon;

                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => navigate(item.path)}
                        className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-[12px] text-[13.5px] font-medium transition-all text-left ${
                          isActive
                            ? 'bg-[#EAF0FF] text-[#1F4FD8] font-bold shadow-xs'
                            : 'text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]'
                        }`}
                      >
                        <Icon
                          className={`w-4 h-4 ${
                            isActive ? 'text-[#1F4FD8]' : 'text-[#64748B]'
                          }`}
                        />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
              </nav>
            </div>
          </div>

          {/* Sidebar Footer: Account Button & Floor Status */}
          <div className="pt-4 border-t border-[#E2E8F0] space-y-2">
            <button
              type="button"
              onClick={() => setIsAccountOpen(true)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-[12px] text-[13px] text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A] transition-colors text-left"
            >
              <User className="w-4 h-4 text-[#64748B]" />
              <div className="truncate min-w-0">
                <div className="font-semibold text-[#0F172A] truncate">
                  {currentUser.name}
                </div>
                <div className="text-[11px] text-[#64748B] truncate">
                  {currentRole}
                </div>
              </div>
            </button>

            <div className="px-3 py-1 text-[11px] text-[#64748B] flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Inspection Floor 2 Online</span>
            </div>
          </div>
        </aside>

        {/* FLUID CONTENT AREA: max-w-[1200px] with 24px padding on desktop */}
        <main className="flex-1 w-full min-w-0 flex flex-col items-center">
          <div className="w-full max-w-[1200px] px-4 sm:px-6 py-6 pb-24 md:pb-8 transition-all">
            <Outlet />
          </div>
        </main>
      </div>

      {/* ========================================================= */}
      {/* MOBILE BOTTOM TAB BAR (< 768px): Keep phone view working   */}
      {/* ========================================================= */}
      <nav
        aria-label="Mobile Bottom Navigation"
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-[#E2E8F0] shadow-[0_-4px_16px_rgba(0,0,0,0.06)] px-2 py-1.5 select-none"
      >
        <div className="flex items-center justify-around max-w-md mx-auto">
          {mobileTabs
            .filter((t) => t.show)
            .map((tab) => {
              const isActive =
                tab.path === '/dashboard'
                  ? location.pathname === '/dashboard'
                  : location.pathname.startsWith(tab.path);
              const Icon = tab.icon;

              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => navigate(tab.path)}
                  className={`flex-1 flex flex-col items-center justify-center min-h-[46px] py-1 px-1 rounded-lg transition-colors focus:outline-none ${
                    isActive
                      ? 'text-[#1F4FD8] font-semibold'
                      : 'text-[#64748B] hover:text-[#0F172A]'
                  }`}
                >
                  <Icon
                    className={`w-5 h-5 transition-transform ${
                      isActive ? 'scale-110 stroke-[2.4]' : 'stroke-[1.8]'
                    }`}
                  />
                  <span className="text-[11px] mt-1 tracking-tight leading-none">
                    {tab.label}
                  </span>
                </button>
              );
            })}

          {/* Account Tab on Mobile */}
          <button
            type="button"
            onClick={() => setIsAccountOpen(true)}
            className="flex-1 flex flex-col items-center justify-center min-h-[46px] py-1 px-1 rounded-lg transition-colors text-[#64748B] hover:text-[#0F172A] focus:outline-none"
          >
            <User className="w-5 h-5 stroke-[1.8]" />
            <span className="text-[11px] mt-1 tracking-tight leading-none">
              Account
            </span>
          </button>
        </div>
      </nav>

      {/* ========================================================= */}
      {/* ACCOUNT MODAL / PROFILE SHEET                             */}
      {/* ========================================================= */}
      {isAccountOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white rounded-[20px] shadow-2xl border border-[#E2E8F0] w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="bg-[#0B1F5C] text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#1F4FD8] flex items-center justify-center text-white font-bold text-base shadow-xs">
                  {currentUser.name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-base leading-tight">
                    {currentUser.name}
                  </h3>
                  <p className="text-xs text-white/70 font-mono">
                    {currentUser.email}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsAccountOpen(false)}
                className="p-1 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5">
              <div className="bg-[#F8FAFC] rounded-[14px] p-4 border border-[#E2E8F0] space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-[#64748B] flex items-center gap-1.5">
                    <Building2 className="w-4 h-4 text-[#1F4FD8]" /> Organization
                  </span>
                  <span className="font-semibold text-[#0F172A]">
                    Acme Knitwear Ltd.
                  </span>
                </div>

                <div className="flex justify-between items-center text-sm border-t border-[#E2E8F0] pt-2.5">
                  <span className="text-[#64748B] flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-[#1F4FD8]" /> Assigned Role
                  </span>
                  <span className="font-bold text-[#1F4FD8] bg-[#EAF0FF] px-2.5 py-0.5 rounded-full text-xs">
                    {currentRole}
                  </span>
                </div>

                <div className="flex justify-between items-center text-sm border-t border-[#E2E8F0] pt-2.5">
                  <span className="text-[#64748B] flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Floor Status
                  </span>
                  <span className="font-medium text-emerald-700 text-xs">
                    Floor 2 Active Shift
                  </span>
                </div>
              </div>

              <div className="text-xs text-[#64748B] leading-relaxed">
                Role and permissions are managed by system administrators. Use the
                floating <strong>Dev Switcher</strong> (top-right) during testing to switch roles.
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAccountOpen(false)}
                  className="px-4 py-2 rounded-[12px] border border-[#CBD5E1] text-[#475569] text-sm font-semibold hover:bg-slate-50 transition-colors"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsAccountOpen(false);
                    navigate('/login');
                  }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-[12px] bg-[#B91C1C] hover:bg-[#991b1b] text-white text-sm font-semibold transition-colors shadow-xs"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign out</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
