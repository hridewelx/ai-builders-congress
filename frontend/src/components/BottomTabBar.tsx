import React from 'react';
import { Home, List, Plus, User } from 'lucide-react';

export type TabId = 'home' | 'lots' | 'new-lot' | 'account';

export interface TabItem {
  id: TabId;
  label: string;
  icon: React.ElementType;
  badge?: number | string;
}

export interface BottomTabBarProps {
  activeTab: TabId;
  onTabChange: (tabId: TabId) => void;
  hideNewLot?: boolean; // New lot is hidden for Admin per section 3
  className?: string;
}

export const BottomTabBar: React.FC<BottomTabBarProps> = ({
  activeTab,
  onTabChange,
  hideNewLot = false,
  className = '',
}) => {
  const allTabs: TabItem[] = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'lots', label: 'Lots', icon: List },
    { id: 'new-lot', label: 'New lot', icon: Plus },
    { id: 'account', label: 'Account', icon: User },
  ];

  const visibleTabs = hideNewLot ? allTabs.filter((t) => t.id !== 'new-lot') : allTabs;

  return (
    <nav
      aria-label="Bottom Navigation"
      className={`w-full bg-white border-t border-[#E2E8F0] shadow-[0_-2px_10px_rgba(0,0,0,0.03)] px-2 py-1.5 select-none ${className}`}
    >
      <div className="flex items-center justify-around max-w-md mx-auto">
        {visibleTabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={`flex-1 flex flex-col items-center justify-center min-h-[44px] py-1 px-1 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[#1F4FD8]/20 ${
                isActive
                  ? 'text-[#1F4FD8] font-semibold'
                  : 'text-[#64748B] hover:text-[#0F172A]'
              }`}
            >
              <div className="relative">
                <Icon
                  className={`w-5 h-5 transition-transform ${
                    isActive ? 'scale-110 stroke-[2.4]' : 'stroke-[1.8]'
                  }`}
                />
                {tab.badge && (
                  <span className="absolute -top-1 -right-2 min-w-[16px] h-4 px-1 rounded-full bg-[#B91C1C] text-white text-[10px] font-bold flex items-center justify-center">
                    {tab.badge}
                  </span>
                )}
              </div>
              <span className="text-[11px] mt-1 tracking-tight leading-none">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
