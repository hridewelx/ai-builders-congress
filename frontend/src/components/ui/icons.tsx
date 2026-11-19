import * as Lucide from "lucide-react";
import type { ComponentType } from "react";

const ALIASES: Record<string, string> = {
  "circle-check": "CircleCheck",
  "circle-x": "CircleX",
  "circle-alert": "CircleAlert",
  "check-circle": "CircleCheck",
  "x-circle": "CircleX",
  "alert-circle": "CircleAlert",
  "alert-octagon": "OctagonAlert",
  "triangle-alert": "TriangleAlert",
  "plus-circle": "CirclePlus",
  "git-commit": "GitCommit",
  "git-branch": "GitBranch",
  "git-pull-request": "GitPullRequest",
  "panel-left-close": "PanelLeftClose",
  "panel-left-open": "PanelLeftOpen",
  "maximize-2": "Maximize2",
  "mouse-pointer-2": "MousePointer2",
  "refresh-cw": "RefreshCw",
  "rotate-ccw": "RotateCcw",
  "list-filter": "ListFilter",
  "circle-dot": "CircleDot",
  "square-check": "SquareCheck",
  "square-x": "SquareX",
  "badge-check": "BadgeCheck",
  "arrow-up-right": "ArrowUpRight",
  "arrow-up-down": "ArrowUpDown",
  "user-plus": "UserPlus",
  "book-open": "BookOpen",
  "sliders": "SlidersHorizontal",
  "list": "List",
  "grid": "Grid2x2",
  "check": "Check",
  "loader-circle": "LoaderCircle",
  "scan-line": "ScanLine",
  "file-text": "FileText",
  "clipboard-check": "ClipboardCheck",
  "external-link": "ExternalLink",
  "hard-drive": "HardDrive",
  "user-check": "UserCheck",
  "package-check": "PackageCheck",
  "panel-top": "PanelTop",
  "zoom-in": "ZoomIn",
  "zoom-out": "ZoomOut",
};

function componentFor(name: string): ComponentType<{ size?: number; strokeWidth?: number; className?: string }> {
  const key = ALIASES[name] || name.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("");
  const found = (Lucide as unknown as Record<string, ComponentType<never>>)[key];
  return (found || Lucide.Circle) as ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
}

export function Icon({
  name,
  size = 18,
  stroke = 1.8,
  className = "icon",
}: {
  name: string;
  size?: number;
  stroke?: number;
  className?: string;
}) {
  const Component = componentFor(name);
  return <Component size={size} strokeWidth={stroke} className={className} />;
}
