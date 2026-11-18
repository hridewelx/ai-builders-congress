import React from 'react';
import { Plus } from 'lucide-react';
import { Button } from '../../components/Button';
import {
  mockProductsList,
  mockBuyersList,
  mockNorthwindClauses,
} from '../../mocks';

export const ProductsBuyersTab: React.FC = () => {
  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-black text-[#0F172A] tracking-tight">Products & Buyers</h1>
        <p className="text-[13px] text-[#64748B] mt-0.5">
          Product families and buyer clause lists. Clauses are read-only in Version 1.
        </p>
      </div>

      {/* Top 2-Column Split: Products and Buyers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Products Card */}
        <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-[#0F172A]">Products</h2>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
              onClick={() => alert('Add product modal')}
            >
              Product
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#E2E8F0] text-[11px] font-bold text-[#64748B] uppercase tracking-wider pb-2">
                  <th className="pb-2">PRODUCT</th>
                  <th className="pb-2 text-right">FAMILY</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {mockProductsList.map((prod) => (
                  <tr key={prod.name}>
                    <td className="py-2.5 font-medium text-[#0F172A]">{prod.name}</td>
                    <td className="py-2.5 text-right text-[#64748B]">{prod.family}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Buyers Card */}
        <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-[#0F172A]">Buyers</h2>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
              onClick={() => alert('Add buyer modal')}
            >
              Buyer
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#E2E8F0] text-[11px] font-bold text-[#64748B] uppercase tracking-wider pb-2">
                  <th className="pb-2">BUYER</th>
                  <th className="pb-2 text-right">CLAUSES</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {mockBuyersList.map((b) => (
                  <tr key={b.name}>
                    <td className="py-2.5 font-medium text-[#0F172A]">{b.name}</td>
                    <td className="py-2.5 text-right text-[#64748B]">{b.clausesSummary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Bottom Card: Buyer Clause List */}
      <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-xs p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[15px] font-bold text-[#0F172A]">Northwind Apparel · clause list</h2>
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#F1F5F9] text-[#64748B]">
            Read-only
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-[#E2E8F0] text-[11px] font-bold text-[#64748B] uppercase tracking-wider pb-2">
                <th className="pb-2">DEFECT TYPE</th>
                <th className="pb-2 text-center">SEVERITY</th>
                <th className="pb-2 text-right">CLAUSE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {mockNorthwindClauses.map((clause) => (
                <tr key={clause.defectType}>
                  <td className="py-3 font-medium text-[#0F172A]">{clause.defectType}</td>
                  <td className="py-3 text-center">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                        clause.severity === 'Critical'
                          ? 'bg-[#FEE2E2] text-[#B91C1C]'
                          : clause.severity === 'Major'
                          ? 'bg-[#FEF3C7] text-[#B45309]'
                          : 'bg-[#E0F2FE] text-[#0369A1]'
                      }`}
                    >
                      {clause.severity}
                    </span>
                  </td>
                  <td className="py-3 text-right font-mono text-[12.5px] text-[#475569]">
                    {clause.clause}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
