import React, { useState } from 'react';
import { Search, ChevronDown, Plus, Info } from 'lucide-react';
import { Button } from '../../components/Button';
import { mockAdminUsers, type AdminUser } from '../../mocks';

export const UsersTab: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>(mockAdminUsers);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('All roles');

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === 'All roles' || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleUnlock = (id: string) => {
    setUsers(users.map((u) => (u.id === id ? { ...u, status: 'Active' } : u)));
    alert('User account unlocked and audit row logged.');
  };

  const handleEnable = (id: string) => {
    setUsers(users.map((u) => (u.id === id ? { ...u, status: 'Active' } : u)));
    alert('User account enabled and audit row logged.');
  };

  const handleDisable = (id: string) => {
    setUsers(users.map((u) => (u.id === id ? { ...u, status: 'Disabled' } : u)));
    alert('User account disabled and audit row logged.');
  };

  return (
    <div className="space-y-6 text-left">
      {/* Top Header Row with Title and + Create user */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-black text-[#0F172A] tracking-tight">Users</h1>
          <p className="text-[13px] text-[#64748B] mt-0.5">
            Create accounts, reset passwords, unlock and change roles.
          </p>
        </div>

        <Button
          variant="primary"
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={() => alert('Create user modal')}
        >
          Create user
        </Button>
      </div>

      {/* Filters Row: Search input + All roles dropdown */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by name or email"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-11 pl-10 pr-3.5 bg-white rounded-[10px] border border-[#E2E8F0] text-[13.5px] text-[#0F172A] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#1F4FD8] focus:ring-1 focus:ring-[#1F4FD8]"
          />
        </div>

        <div className="relative w-full sm:w-44">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="w-full h-11 px-3.5 bg-white rounded-[10px] border border-[#E2E8F0] text-[13.5px] text-[#0F172A] appearance-none focus:outline-none focus:border-[#1F4FD8] cursor-pointer"
          >
            <option value="All roles">All roles</option>
            <option value="Admin">Admin</option>
            <option value="Supervisor">Supervisor</option>
            <option value="Inspector">Inspector</option>
          </select>
          <ChevronDown className="w-4 h-4 text-[#94A3B8] absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {/* Users Table Card */}
      <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC]/50 text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
                <th className="py-3 px-4">NAME</th>
                <th className="py-3 px-4">EMAIL</th>
                <th className="py-3 px-4">ROLE</th>
                <th className="py-3 px-4">STATUS</th>
                <th className="py-3 px-4">LAST LOGIN</th>
                <th className="py-3 px-4 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-[#0F172A] whitespace-nowrap">
                    {user.name}
                  </td>
                  <td className="py-3.5 px-4 text-[#475569] font-mono text-[12.5px] whitespace-nowrap">
                    {user.email}
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                        user.role === 'Admin'
                          ? 'bg-[#E0F2FE] text-[#0369A1]'
                          : user.role === 'Supervisor'
                          ? 'bg-[#EDE9FE] text-[#6D28D9]'
                          : 'bg-[#F1F5F9] text-[#475569]'
                      }`}
                    >
                      {user.role}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                        user.status === 'Active'
                          ? 'bg-[#DCFCE7] text-[#15803D]'
                          : user.status === 'Locked'
                          ? 'bg-[#FEF3C7] text-[#B45309]'
                          : 'bg-[#F1F5F9] text-[#64748B]'
                      }`}
                    >
                      {user.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-[#64748B] whitespace-nowrap">
                    {user.lastLogin}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap font-medium text-[12.5px]">
                    {user.isSelf ? (
                      <span className="text-[#94A3B8]">You</span>
                    ) : user.status === 'Locked' ? (
                      <button
                        onClick={() => handleUnlock(user.id)}
                        className="text-[#1F4FD8] font-bold hover:underline"
                      >
                        Unlock
                      </button>
                    ) : user.status === 'Disabled' ? (
                      <button
                        onClick={() => handleEnable(user.id)}
                        className="text-[#1F4FD8] font-bold hover:underline"
                      >
                        Enable
                      </button>
                    ) : (
                      <span className="space-x-1.5 text-[#64748B]">
                        <button
                          onClick={() => alert(`Reset password sent for ${user.email}`)}
                          className="hover:text-[#0F172A] hover:underline"
                        >
                          Reset
                        </button>
                        <span>·</span>
                        <button
                          onClick={() => handleDisable(user.id)}
                          className="hover:text-[#B91C1C] hover:underline"
                        >
                          Disable
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Security Rule Info Banner */}
      <div className="bg-[#E0F2FE] border border-[#BAE6FD]/80 rounded-[14px] p-3.5 flex items-start gap-2.5 text-left">
        <Info className="w-4 h-4 text-[#0369A1] shrink-0 mt-0.5" />
        <div className="text-[12.5px] text-[#075985] leading-relaxed">
          Every action writes an audit row and signs the affected user out. The last Admin cannot
          be disabled. You cannot change your own role.
        </div>
      </div>
    </div>
  );
};
