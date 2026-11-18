import React, { useState, useEffect } from 'react';
import type { UserRole } from '../mocks';
import { RoleContext } from './useRole';

export const RoleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRole, setCurrentRole] = useState<UserRole>(() => {
    const saved = localStorage.getItem('lotline_dev_role');
    return (saved as UserRole) || 'Inspector';
  });

  useEffect(() => {
    localStorage.setItem('lotline_dev_role', currentRole);
  }, [currentRole]);

  return (
    <RoleContext.Provider value={{ currentRole, setRole: setCurrentRole }}>
      {children}
    </RoleContext.Provider>
  );
};
