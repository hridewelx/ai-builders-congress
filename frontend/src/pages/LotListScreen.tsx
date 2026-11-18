import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  X,
} from 'lucide-react';
import { OutcomeChip } from '../components/OutcomeChip';
import { Button } from '../components/Button';
import { ProgressBar } from '../components/ProgressBar';
import { useRole } from '../context';
import { mockLots } from '../mocks';
import type { OutcomeType } from '../mocks';

export const LotListScreen: React.FC = () => {
  const navigate = useNavigate();
  const { currentRole } = useRole();

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [buyerFilter, setBuyerFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'code' | 'pieces' | 'progress'>('code');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;

  // Filtered and sorted list
  const filteredLots = useMemo(() => {
    return mockLots
      .filter((lot) => {
        const query = searchQuery.trim().toLowerCase();
        const matchesSearch =
          !query ||
          lot.code.toLowerCase().includes(query) ||
          lot.product.toLowerCase().includes(query) ||
          lot.buyer.toLowerCase().includes(query) ||
          (lot.createdBy && lot.createdBy.toLowerCase().includes(query));

        if (!matchesSearch) return false;

        if (statusFilter !== 'ALL') {
          if (statusFilter === 'OPEN') {
            if (lot.status !== 'IN_PROGRESS' && lot.status !== 'HOLD' && lot.status !== 'ESCALATE') {
              return false;
            }
          } else if (lot.status !== statusFilter) {
            return false;
          }
        }

        if (buyerFilter !== 'ALL' && !lot.buyer.toLowerCase().includes(buyerFilter.toLowerCase())) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        let valA: string | number = a.code;
        let valB: string | number = b.code;

        if (sortBy === 'pieces') {
          valA = a.pieces;
          valB = b.pieces;
        } else if (sortBy === 'progress') {
          valA = a.progressPercent;
          valB = b.progressPercent;
        }

        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
  }, [searchQuery, statusFilter, buyerFilter, sortBy, sortOrder]);

  // Paginated items
  const totalPages = Math.ceil(filteredLots.length / pageSize) || 1;
  const paginatedLots = filteredLots.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handleSort = (field: 'code' | 'pieces' | 'progress') => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const clearAllFilters = () => {
    setSearchQuery('');
    setStatusFilter('ALL');
    setBuyerFilter('ALL');
    setCurrentPage(1);
  };

  const hasActiveFilters = searchQuery !== '' || statusFilter !== 'ALL' || buyerFilter !== 'ALL';

  return (
    <div className="space-y-6 text-[#0F172A] select-none">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#E2E8F0]">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-[#0F172A] tracking-tight">
            Lot Inspection Register
          </h1>
          <p className="text-sm text-[#64748B] mt-0.5">
            Production batches, sampling progress, and deterministic engine recommendations
          </p>
        </div>

        {currentRole !== 'Admin' && (
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => navigate('/lots/new')}
          >
            Create new lot
          </Button>
        )}
      </div>

      {/* ========================================================= */}
      {/* SEARCH AND FILTERS ABOVE TABLE                            */}
      {/* ========================================================= */}
      <div className="bg-white p-5 rounded-[22px] border border-[#E2E8F0] shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          {/* Search Input (Cols 6) */}
          <div className="md:col-span-6 relative">
            <Search className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by lot code, product, buyer, created by..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-11 pl-10 pr-3.5 bg-[#F8FAFC] rounded-[12px] border border-[#E2E8F0] text-[13.5px] text-[#0F172A] placeholder:text-[#94A3B8] focus:bg-white focus:outline-none focus:border-[#1F4FD8] focus:ring-2 focus:ring-[#EAF0FF] transition-all"
            />
          </div>

          {/* Buyer Filter Dropdown (Cols 3) */}
          <div className="md:col-span-3">
            <select
              value={buyerFilter}
              onChange={(e) => {
                setBuyerFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-11 px-3 bg-[#F8FAFC] rounded-[12px] border border-[#E2E8F0] text-[13px] text-[#0F172A] focus:bg-white focus:outline-none focus:border-[#1F4FD8] transition-all"
            >
              <option value="ALL">Buyer: All Buyers</option>
              <option value="Northwind">Northwind Apparel</option>
              <option value="Brightway">Brightway</option>
            </select>
          </div>

          {/* Reset Filters (Cols 3) */}
          <div className="md:col-span-3 flex items-center justify-end">
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={clearAllFilters}
                className="h-11 px-4 text-xs font-semibold text-[#B91C1C] bg-[#FEE2E2]/60 hover:bg-[#FEE2E2] rounded-[12px] flex items-center gap-1.5 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                <span>Reset filters</span>
              </button>
            ) : (
              <span className="text-xs text-[#64748B]">Showing all registered lots</span>
            )}
          </div>
        </div>

        {/* Status Filter Chips Row */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1 border-t border-[#F1F5F9]">
          <span className="text-xs font-bold uppercase tracking-wider text-[#64748B] mr-1 shrink-0">
            Status:
          </span>
          {[
            { id: 'ALL', label: 'All Lots' },
            { id: 'OPEN', label: 'Open' },
            { id: 'ACCEPT', label: 'ACCEPT' },
            { id: 'REJECT', label: 'REJECT' },
            { id: 'HOLD', label: 'HOLD' },
            { id: 'ESCALATE', label: 'ESCALATE' },
          ].map((tab) => {
            const isSelected = statusFilter === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setStatusFilter(tab.id);
                  setCurrentPage(1);
                }}
                className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-semibold transition-all shrink-0 ${
                  isSelected
                    ? 'bg-[#1F4FD8] text-white shadow-xs'
                    : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ========================================================= */}
      {/* REAL TABLE FOR DESKTOP WIDTH                              */}
      {/* Columns: lot code, product, buyer, size, progress,        */}
      {/*          outcome chip, created by                         */}
      {/* ========================================================= */}
      <div className="bg-white rounded-[22px] border border-[#E2E8F0] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[780px]">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[12px] font-bold text-[#64748B] uppercase tracking-wider select-none">
                <th
                  onClick={() => handleSort('code')}
                  className="py-3.5 px-5 cursor-pointer hover:text-[#0F172A] transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Lot Code</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#94A3B8]" />
                  </div>
                </th>
                <th className="py-3.5 px-4">Product</th>
                <th className="py-3.5 px-4">Buyer</th>
                <th
                  onClick={() => handleSort('pieces')}
                  className="py-3.5 px-4 cursor-pointer hover:text-[#0F172A] transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Size</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#94A3B8]" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('progress')}
                  className="py-3.5 px-4 w-44 cursor-pointer hover:text-[#0F172A] transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Progress</span>
                    <ArrowUpDown className="w-3.5 h-3.5 text-[#94A3B8]" />
                  </div>
                </th>
                <th className="py-3.5 px-4 text-center">Outcome</th>
                <th className="py-3.5 px-4">Created By</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9] text-sm">
              {paginatedLots.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-[#64748B]">
                    <p className="text-base font-semibold text-[#0F172A]">No lots match your filters</p>
                    <p className="text-xs mt-1">Try resetting search criteria or clearing filters.</p>
                  </td>
                </tr>
              ) : (
                paginatedLots.map((lot) => {
                  return (
                    <tr
                      key={lot.id}
                      onClick={() => navigate(`/lots/${lot.code}`)}
                      className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    >
                      {/* 1. Lot Code */}
                      <td className="py-4 px-5">
                        <span className="font-mono font-bold text-[14.5px] text-[#1F4FD8] group-hover:underline">
                          {lot.code}
                        </span>
                      </td>

                      {/* 2. Product */}
                      <td className="py-4 px-4 font-semibold text-[#0F172A]">
                        {lot.product}
                      </td>

                      {/* 3. Buyer */}
                      <td className="py-4 px-4 text-[#475569]">
                        {lot.buyer}
                      </td>

                      {/* 4. Size */}
                      <td className="py-4 px-4 font-mono font-medium text-[#0F172A]">
                        {lot.pieces.toLocaleString()} pcs
                      </td>

                      {/* 5. Progress */}
                      <td className="py-4 px-4">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[11px] text-[#64748B]">
                            <span>
                              {lot.registeredUnits || 0}/{lot.requiredUnits || 80}
                            </span>
                            <span className="font-mono font-bold text-[#0F172A]">
                              {lot.progressPercent}%
                            </span>
                          </div>
                          <ProgressBar
                            value={lot.progressPercent}
                            max={100}
                            variant={
                              lot.status === 'ACCEPT'
                                ? 'green'
                                : lot.status === 'REJECT'
                                ? 'red'
                                : 'blue'
                            }
                            height="sm"
                          />
                        </div>
                      </td>

                      {/* 6. Outcome Chip */}
                      <td className="py-4 px-4 text-center">
                        {lot.status === 'IN_PROGRESS' ? (
                          <span className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#E2E8F0] text-[#475569]">
                            In progress
                          </span>
                        ) : (
                          <OutcomeChip outcome={lot.status as OutcomeType} size="sm" showDot />
                        )}
                      </td>

                      {/* 7. Created By */}
                      <td className="py-4 px-4 text-[#64748B] text-xs font-medium">
                        {lot.createdBy || 'A. Rahman'}
                      </td>

                      {/* 8. Action Link */}
                      <td className="py-4 px-4 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/lots/${lot.code}`);
                          }}
                          className="px-2.5 py-1 rounded-lg text-xs font-semibold text-[#1F4FD8] hover:bg-[#EAF0FF] transition-colors"
                        >
                          Details →
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ========================================================= */}
        {/* PAGINATION BELOW TABLE                                    */}
        {/* ========================================================= */}
        <div className="p-4 sm:px-6 bg-[#F8FAFC] border-t border-[#E2E8F0] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#64748B]">
          <div>
            Showing{' '}
            <strong className="text-[#0F172A]">
              {filteredLots.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}
            </strong>{' '}
            to{' '}
            <strong className="text-[#0F172A]">
              {Math.min(currentPage * pageSize, filteredLots.length)}
            </strong>{' '}
            of <strong className="text-[#0F172A]">{filteredLots.length}</strong> registered lots
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              className="p-1.5 rounded-lg border border-[#CBD5E1] bg-white text-[#0F172A] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors"
              title="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            {Array.from({ length: totalPages }, (_, idx) => idx + 1).map((page) => (
              <button
                key={page}
                type="button"
                onClick={() => setCurrentPage(page)}
                className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${
                  currentPage === page
                    ? 'bg-[#1F4FD8] text-white shadow-xs'
                    : 'bg-white border border-[#CBD5E1] text-[#475569] hover:bg-slate-100'
                }`}
              >
                {page}
              </button>
            ))}

            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
              className="p-1.5 rounded-lg border border-[#CBD5E1] bg-white text-[#0F172A] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors"
              title="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
