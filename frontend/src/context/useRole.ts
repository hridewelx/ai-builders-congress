import { createContext, useContext } from 'react';
import type { UserRole } from '../mocks';

export interface RoleContextType {
  currentRole: UserRole;
  setRole: (role: UserRole) => void;
}

export const RoleContext = createContext<RoleContextType | undefined>(undefined);

export const useRole = (): RoleContextType => {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
};
