import React, { useState } from 'react';
import {
  Button,
  OutcomeChip,
  StatusChip,
  Banner,
  Input,
  ProgressBar,
  AppBar,
  BottomTabBar,
  StickyActionBar,
  type TabId,
  type OutcomeType,
} from '../components';
import {
  Camera,
  Sparkles,
  Eye,
  Check,
  Copy,
  AlertTriangle,
} from 'lucide-react';

export const DesignSystemPage: React.FC = () => {
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('home');
  const [progressVal, setProgressVal] = useState(74);

  const copyToClipboard = (text: string, tokenName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(tokenName);
    setTimeout(() => setCopiedToken(null), 1800);
  };

  const brandNeutrals = [
    { name: 'Navy', hex: '#0B1F5C', bgClass: 'bg-[#0B1F5C]', textWhite: true },
    { name: 'Brand blue', hex: '#1F4FD8', bgClass: 'bg-[#1F4FD8]', textWhite: true },
    { name: 'Tint', hex: '#EAF0FF', bgClass: 'bg-[#EAF0FF]', textWhite: false, textHex: 'text-[#1F4FD8]' },
    { name: 'Ink', hex: '#0F172A', bgClass: 'bg-[#0F172A]', textWhite: true },
    { name: 'Muted', hex: '#64748B', bgClass: 'bg-[#64748B]', textWhite: true },
    { name: 'Line', hex: '#E2E8F0', bgClass: 'bg-[#E2E8F0]', textWhite: false, textHex: 'text-[#0F172A]' },
  ];

  const outcomeColors = [
    { outcome: 'ACCEPT' as OutcomeType, hex: '#15803D', bgClass: 'bg-[#15803D]' },
    { outcome: 'REJECT' as OutcomeType, hex: '#B91C1C', bgClass: 'bg-[#B91C1C]' },
    { outcome: 'HOLD' as OutcomeType, hex: '#B45309', bgClass: 'bg-[#B45309]' },
    { outcome: 'ESCALATE' as OutcomeType, hex: '#6D28D9', bgClass: 'bg-[#6D28D9]' },
    { outcome: 'Info' as const, hex: '#0369A1', bgClass: 'bg-[#0369A1]' },
  ];

  return (
    <div className="min-h-screen bg-[#EEF2F6] text-[#0F172A] py-6 sm:py-12 px-3 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-5xl mx-auto space-y-12">

        {/* ========================================================= */}
        {/* MASTER POSTER CARD (EXACT REPLICA OF 00-design-system.png) */}
        {/* ========================================================= */}
        <div className="bg-white rounded-[24px] sm:rounded-[28px] border border-slate-200/90 shadow-xl p-5 sm:p-10 md:p-14 select-none">
          {/* Header */}
          <div>
            <h1 className="text-[32px] sm:text-[38px] md:text-[42px] font-black text-[#0F172A] tracking-tight leading-none">
              Lotline design system
            </h1>
            <p className="text-[16px] sm:text-[18px] text-[#64748B] mt-2 font-normal">
              Calm, trustworthy, built for one hand on a factory floor.
            </p>
          </div>

          {/* Section 1: Brand and neutrals */}
          <div className="mt-8">
            <h2 className="text-[13px] font-semibold text-[#64748B] mb-3">
              Brand and neutrals
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {brandNeutrals.map((token) => (
                <div
                  key={token.name}
                  onClick={() => copyToClipboard(token.hex, token.name)}
                  className={`group relative p-3.5 sm:p-4 rounded-[14px] ${token.bgClass} cursor-pointer transition-transform hover:scale-[1.02] active:scale-[0.98] shadow-xs flex flex-col justify-between min-h-[96px] ${
                    token.textWhite ? 'text-white' : token.textHex || 'text-[#0F172A]'
                  }`}
                  title={`Click to copy ${token.hex}`}
                >
                  <div className="flex justify-between items-start">
                    <span className="font-bold text-[14px] tracking-tight">{token.name}</span>
                    {copiedToken === token.name ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    )}
                  </div>
                  <div className="font-mono text-[12px] opacity-90 tracking-wide font-medium">
                    {token.hex}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 2: Outcome colours */}
          <div className="mt-8">
            <h2 className="text-[13px] font-semibold text-[#64748B] mb-3">
              Outcome colours (never colour alone: always a text label)
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {outcomeColors.map((token) => (
                <div
                  key={token.outcome}
                  onClick={() => copyToClipboard(token.hex, token.outcome)}
                  className={`group relative p-3.5 sm:p-4 rounded-[14px] ${token.bgClass} text-white cursor-pointer transition-transform hover:scale-[1.02] active:scale-[0.98] shadow-xs flex flex-col justify-between min-h-[96px]`}
                  title={`Click to copy ${token.hex}`}
                >
                  <div className="flex justify-between items-start">
                    <span className="font-bold text-[14px] tracking-wide">{token.outcome}</span>
                    {copiedToken === token.outcome ? (
                      <Check className="w-3.5 h-3.5 text-emerald-300" />
                    ) : (
                      <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    )}
                  </div>
                  <div className="font-mono text-[12px] opacity-90 tracking-wide font-medium">
                    {token.hex}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Two Columns (Type Scale + Components) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 md:gap-10 mt-8 pt-6 border-t border-slate-100">
            {/* Left Column: Type scale */}
            <div className="lg:col-span-5 flex flex-col justify-between space-y-4">
              <div>
                <h2 className="text-[13px] font-semibold text-[#64748B] mb-3">
                  Type scale (Inter / system)
                </h2>
                <div className="space-y-3">
                  <div className="text-[28px] font-extrabold leading-none text-[#0F172A] tracking-tight">
                    Display 28 / 800
                  </div>
                  <div className="text-[20px] font-bold leading-none text-[#0F172A] tracking-tight">
                    Title 20 / 700
                  </div>
                  <div className="text-[15px] font-semibold text-[#0F172A]">
                    Body strong 15 / 600
                  </div>
                  <div className="text-[13px] text-[#475569] leading-relaxed">
                    Body 13 / 400. Minimum body size on phone is 12.5.
                  </div>
                  <div className="font-mono text-[11.5px] text-[#0F172A] pt-1">
                    Mono 11.5 · LT-2411-018 · ESC_UNKNOWN_CLAUSE
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Components matching 00-design-system.png */}
            <div className="lg:col-span-7 space-y-3.5">
              <h2 className="text-[13px] font-semibold text-[#64748B] mb-2">
                Components
              </h2>

              {/* Row 1: Primary, Secondary, Ghost, Compute, ACCEPT, REJECT */}
              <div className="flex flex-wrap items-center gap-2.5">
                <Button variant="primary" size="sm">Primary</Button>
                <Button variant="secondary" size="sm">Secondary</Button>
                <Button variant="ghost" size="sm">Ghost</Button>
                <Button variant="compute" size="sm">Compute</Button>
                <OutcomeChip outcome="ACCEPT" size="sm" />
                <OutcomeChip outcome="REJECT" size="sm" />
              </div>

              {/* Row 2: HOLD, ESCALATE, uncalibrated */}
              <div className="flex flex-wrap items-center gap-2.5">
                <OutcomeChip outcome="HOLD" size="sm" />
                <OutcomeChip outcome="ESCALATE" size="sm" />
                <StatusChip label="uncalibrated" variant="uncalibrated" size="sm" />
              </div>

              {/* Row 3: Inputs side by side */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-0.5">
                <input
                  type="text"
                  readOnly
                  value="Input field"
                  className="w-full h-11 px-3.5 rounded-[10px] border border-[#CBD5E1] bg-white text-[#0F172A] text-sm focus:outline-none"
                />
                <input
                  type="text"
                  readOnly
                  value="Error state"
                  className="w-full h-11 px-3.5 rounded-[10px] border-2 border-[#B91C1C] bg-white text-[#0F172A] text-sm focus:outline-none"
                />
              </div>

              {/* Row 4: Warning Banner */}
              <div className="pt-0.5">
                <div className="flex items-center gap-2.5 px-4 py-3 rounded-[12px] bg-[#FEF9C3] text-[#854D0E] border border-[#FDE047]/60 text-sm">
                  <AlertTriangle className="w-4 h-4 text-[#B45309] shrink-0" />
                  <span className="font-normal">Warning banner with a plain next step.</span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Specification Text */}
          <div className="mt-8 pt-5 border-t border-slate-100 text-[12px] text-[#64748B] flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>Spacing 4 / 8 / 12 / 16 / 24.</span>
            <span>Radius 10 (inputs), 12 (buttons), 14 (cards), 28 (phone).</span>
            <span>Touch target 44 px or more.</span>
            <span>Reference phone width 360 CSS px.</span>
          </div>
        </div>

        {/* ========================================================= */}
        {/* COMPONENT LAB & VISUAL TEST BENCH (ALL 9 SPEC COMPONENTS) */}
        {/* ========================================================= */}
        <section className="bg-white rounded-[28px] border border-slate-200/90 shadow-md p-8 sm:p-12 space-y-10">
          <div className="border-b border-[#E2E8F0] pb-4">
            <h2 className="text-2xl font-black text-[#0F172A] tracking-tight">
              Component Library & Interactive Specs
            </h2>
            <p className="text-[#64748B] text-sm mt-1">
              Detailed breakdown of all 9 system components specified in docs/ui-ux/UI_UX_DESIGN.md section 2.
            </p>
          </div>

          {/* 1. Button Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">1. Button Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/Button.tsx
              </span>
            </div>
            <div className="flex flex-wrap gap-3 items-center">
              <Button variant="primary">Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="compute">Compute</Button>
              <Button variant="destructive">Destructive</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="primary" leftIcon={<Camera className="w-4 h-4" />}>With Icon</Button>
              <Button variant="secondary" rightIcon={<Sparkles className="w-4 h-4" />}>Icon Right</Button>
              <Button variant="primary" loading>Loading</Button>
              <Button variant="primary" disabled>Disabled</Button>
            </div>
          </div>

          {/* 2. OutcomeChip Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">2. OutcomeChip Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/OutcomeChip.tsx
              </span>
            </div>
            <p className="text-xs text-[#64748B]">
              Rigidly paired text + colour for all 4 deterministic sampling engine outcomes. Never colour alone.
            </p>
            <div className="flex flex-wrap gap-4 items-center">
              <OutcomeChip outcome="ACCEPT" />
              <OutcomeChip outcome="REJECT" />
              <OutcomeChip outcome="HOLD" />
              <OutcomeChip outcome="ESCALATE" />
              <OutcomeChip outcome="ACCEPT" size="sm" showDot />
              <OutcomeChip outcome="REJECT" size="sm" showDot />
              <OutcomeChip outcome="HOLD" size="sm" showDot />
              <OutcomeChip outcome="ESCALATE" size="sm" showDot />
            </div>
          </div>

          {/* 3. StatusChip Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">3. StatusChip Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/StatusChip.tsx
              </span>
            </div>
            <div className="flex flex-wrap gap-3 items-center">
              <StatusChip label="uncalibrated" variant="uncalibrated" />
              <StatusChip label="Possible critical" variant="critical" />
              <StatusChip label="LOW_SCORE" variant="warning" />
              <StatusChip label="BLUR" variant="warning" />
              <StatusChip label="DARK" variant="neutral" />
              <StatusChip label="UNKNOWN" variant="escalate" />
              <StatusChip label="not inferred" count={3} variant="neutral" />
              <StatusChip label="retake" count={2} variant="warning" />
              <StatusChip label="escalate" count={1} variant="escalate" />
            </div>
          </div>

          {/* 4. Banner Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">4. Banner Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/Banner.tsx
              </span>
            </div>
            <div className="space-y-3">
              <Banner
                variant="warn"
                title="Not inferred, detector unavailable."
                description="New photos need full manual review."
                actionLabel="Learn more"
                onAction={() => alert('Fallback mode details')}
              />
              <Banner
                variant="error"
                title="Duplicate lot code detected"
                description="A lot with code 'LT-2411-018' already exists."
                requestId="req_88f219c0"
              />
              <Banner
                variant="ok"
                title="Sampling plan verified and locked"
                description="ANSI/ASQ Z1.4 Normal II single sampling plan approved."
              />
              <Banner
                variant="escalate"
                title="Critical defect detected"
                description="Rejecting a critical proposal escalates the lot. A person must decide."
              />
            </div>
          </div>

          {/* 5. Input Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">5. Input Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/Input.tsx
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <Input label="Lot Code" defaultValue="LT-2411-019" mono helpText="Unique identifier" />
              <Input label="Lot Size" defaultValue="800" mono helpText="Whole number, 1 or more" />
              <Input label="Reason Code" defaultValue="ESC_UNKNOWN_CLAUSE" mono error="Unknown buyer clause" />
            </div>
          </div>

          {/* 6. ProgressBar Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">6. ProgressBar Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/ProgressBar.tsx
              </span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-[#64748B]">Adjust Slider:</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={progressVal}
                  onChange={(e) => setProgressVal(Number(e.target.value))}
                  className="w-48 accent-[#1F4FD8]"
                />
                <span className="font-mono text-xs font-bold text-[#1F4FD8]">{progressVal}%</span>
              </div>
              <ProgressBar value={progressVal} max={100} variant="blue" label="In Progress" showPercent />
              <ProgressBar value={100} max={100} variant="green" label="Accepted (100%)" showPercent />
              <ProgressBar value={85} max={100} variant="red" label="Rejected (Over limit)" showPercent />
            </div>
          </div>

          {/* 7. AppBar Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">7. AppBar Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/AppBar.tsx
              </span>
            </div>
            <div className="rounded-[16px] overflow-hidden border border-[#0B1F5C] shadow-xs">
              <AppBar
                title="Inspection Suite"
                subtitle="Acme Knitwear Ltd. · Floor 2"
                role="Inspector"
                showStatusBarMock
              />
            </div>
          </div>

          {/* 8. BottomTabBar Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">8. BottomTabBar Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/BottomTabBar.tsx
              </span>
            </div>
            <div className="border border-[#E2E8F0] rounded-[16px] overflow-hidden bg-slate-50 p-3 max-w-md mx-auto">
              <BottomTabBar
                activeTab={activeTab}
                onTabChange={setActiveTab}
                hideNewLot={false}
              />
            </div>
          </div>

          {/* 9. StickyActionBar Component */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-base text-[#0F172A]">9. StickyActionBar Component</h3>
              <span className="text-xs font-mono bg-[#EAF0FF] text-[#1F4FD8] px-2 py-0.5 rounded">
                components/StickyActionBar.tsx
              </span>
            </div>
            <div className="border border-[#E2E8F0] rounded-[16px] overflow-hidden bg-slate-50 p-4 max-w-md mx-auto">
              <StickyActionBar
                row1={
                  <>
                    <Button variant="primary" leftIcon={<Camera className="w-4 h-4" />}>
                      Add unit
                    </Button>
                    <Button variant="secondary" leftIcon={<Eye className="w-4 h-4" />}>
                      Review
                    </Button>
                  </>
                }
                row2={
                  <>
                    <Button variant="secondary">Sampling plan</Button>
                    <Button variant="compute">Compute decision</Button>
                  </>
                }
              />
            </div>
          </div>
        </section>

      </div>
    </div>
  );
};
