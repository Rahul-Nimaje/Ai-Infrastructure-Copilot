"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { LucideIcon } from "lucide-react";

// ─── Tab Definition ───────────────────────────────────────────
export interface DrawerTab {
  id: string;
  label: string;
  icon: LucideIcon;
}

// ─── Props ────────────────────────────────────────────────────
interface DrawerProps {
  open: boolean;
  onClose: () => void;

  // Header
  title: string;
  subtitle?: string;
  headerIcon?: React.ReactNode;
  headerExtra?: React.ReactNode;

  // Tabs
  tabs?: DrawerTab[];
  activeTab?: string;
  onTabChange?: (tabId: string) => void;

  // Footer
  footerActions?: React.ReactNode;

  // Content
  children: React.ReactNode;
  className?: string;
}

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  headerIcon,
  headerExtra,
  tabs,
  activeTab,
  onTabChange,
  footerActions,
  children,
  className = "max-w-xl",
}: DrawerProps) {
  if (!open) return null;

  return (
    <div
      className={`fixed inset-y-0 right-0 z-50 w-full ${className} border-l border-border bg-card shadow-2xl p-0 flex flex-col animate-in slide-in-from-right duration-300`}
    >
      {/* Header */}
      <div className="p-6 border-b border-border bg-muted/20 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {headerIcon}
          <div>
            <h3 className="text-lg font-bold text-foreground">{title}</h3>
            {subtitle && (
              <p className="text-xs text-muted-foreground font-mono">{subtitle}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {headerExtra}
          <button
            onClick={onClose}
            className="rounded p-1 hover:bg-muted text-muted-foreground hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      {tabs && tabs.length > 0 && (
        <div className="flex border-b border-border bg-muted/10 overflow-x-auto scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange?.(tab.id)}
                className={`flex items-center gap-1.5 px-4 py-3 border-b-2 text-xs font-bold whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-primary text-primary bg-primary/5"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/5"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      )}

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">{children}</div>

      {/* Footer */}
      {footerActions ? (
        <div className="border-t border-border p-4 bg-muted/20 flex gap-2">
          {footerActions}
        </div>
      ) : (
        <div className="border-t border-border p-4 bg-muted/20 flex gap-2">
          <Button
            onClick={onClose}
            className="w-full text-xs font-semibold bg-primary text-white"
          >
            Done / Close Drawer
          </Button>
        </div>
      )}
    </div>
  );
}
