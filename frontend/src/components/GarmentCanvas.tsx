import React from 'react';
import type { DefectProposal } from '../mocks';

interface GarmentCanvasProps {
  proposals?: DefectProposal[];
  activeProposalId?: string;
  onSelectProposal?: (id: string) => void;
  editorMode?: boolean; // When true, shows drag handles as in 09-defect-confirmation.png
  className?: string;
}

export const GarmentCanvas: React.FC<GarmentCanvasProps> = ({
  proposals = [],
  activeProposalId,
  onSelectProposal,
  editorMode = false,
  className = '',
}) => {
  return (
    <div
      className={`relative w-full aspect-[4/3.5] bg-[#1B2436] rounded-[16px] overflow-hidden select-none flex items-center justify-center ${className}`}
    >
      {/* Knitwear Graphic (SVG) */}
      <svg
        viewBox="0 0 400 350"
        className="w-full h-full object-contain p-2"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Subtle background grid pattern */}
        <defs>
          <pattern id="knit-grid" width="12" height="12" patternUnits="userSpaceOnUse">
            <path
              d="M 12 0 L 0 0 0 12"
              fill="none"
              stroke="rgba(255, 255, 255, 0.04)"
              strokeWidth="0.8"
            />
          </pattern>
        </defs>
        <rect width="400" height="350" fill="url(#knit-grid)" />

        {/* T-Shirt / Garment Silhouette */}
        <g id="garment-body">
          <path
            d="M 140 60
               C 165 78, 235 78, 260 60
               L 310 95
               L 260 145
               L 260 300
               L 140 300
               L 140 145
               L 90 95
               Z"
            fill="#8EA3C0"
            stroke="#A5B8D2"
            strokeWidth="1.5"
            className="filter drop-shadow-md"
          />
          {/* Collar neck cut */}
          <path
            d="M 165 60 C 180 82, 220 82, 235 60"
            stroke="#1B2436"
            strokeWidth="3.5"
            strokeLinecap="round"
          />
        </g>
      </svg>

      {/* Bounding Box Overlays */}
      {proposals.map((prop) => {
        const isHole = prop.type.toLowerCase().includes('hole');
        const borderColor = isHole ? '#EF4444' : '#EA580C';
        const bgColor = isHole ? 'rgba(239, 68, 68, 0.22)' : 'rgba(234, 88, 12, 0.22)';
        const tagBgColor = isHole ? '#EF4444' : '#EA580C';

        const isActive = activeProposalId === prop.id || proposals.length === 1;

        return (
          <div
            key={prop.id}
            onClick={() => onSelectProposal && onSelectProposal(prop.id)}
            style={{
              left: `${prop.box.x}%`,
              top: `${prop.box.y}%`,
              width: `${prop.box.width}%`,
              height: `${prop.box.height}%`,
              backgroundColor: bgColor,
              borderColor: borderColor,
            }}
            className={`absolute border-[2px] rounded-sm transition-all cursor-pointer ${
              isActive ? 'ring-2 ring-white/50' : 'opacity-90 hover:opacity-100'
            }`}
          >
            {/* Tag Pill on Top-Left */}
            <div
              style={{ backgroundColor: tagBgColor }}
              className="absolute -top-5 left-0 px-1.5 py-0.5 rounded-t text-white text-[10px] font-bold tracking-tight whitespace-nowrap shadow-xs"
            >
              {editorMode ? prop.type : `${prop.type} ${prop.score}`}
            </div>

            {/* If in editor mode (09-defect-confirmation.png), show corner draggable resize handles */}
            {editorMode && (
              <>
                <span className="absolute -top-1 -left-1 w-2.5 h-2.5 bg-white border border-[#EF4444] rounded-full cursor-nwse-resize shadow-xs" />
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-white border border-[#EF4444] rounded-full cursor-nesw-resize shadow-xs" />
                <span className="absolute -bottom-1 -left-1 w-2.5 h-2.5 bg-white border border-[#EF4444] rounded-full cursor-nesw-resize shadow-xs" />
                <span className="absolute -bottom-1 -right-1 w-2.5 h-2.5 bg-white border border-[#EF4444] rounded-full cursor-nwse-resize shadow-xs" />
              </>
            )}
          </div>
        );
      })}
    </div>
  );
};
