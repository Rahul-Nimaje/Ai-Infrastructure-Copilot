"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Router,
  ShieldCheck,
  Terminal,
  Workflow,
} from "lucide-react";


import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/auth-store";
import { AI_CHAT_NAV, BOTTOM_NAV, NAV_GROUPS, TOP_NAV } from "@/components/layout/nav-config";

const BOTTOM_NAV_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "/knowledge-base": BookOpen,
  "/event-log-analyzer": FileText,
  "/powershell-generator": Terminal,
  "/automation": Workflow,
  "/alerts": ShieldCheck,
  "/reports": FileText,
  "/settings": Router,
};


function navRowClasses(active: boolean) {
  return `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"
  }`;
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, clear } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(
    Object.fromEntries(NAV_GROUPS.map((g) => [g.key, g.defaultOpen]))
  );

  function toggleGroup(key: string) {
    setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "?";

  return (
    <aside
      className={`flex h-screen flex-shrink-0 flex-col border-r border-border bg-card transition-[width] duration-150 ${
        collapsed ? "w-[68px]" : "w-[244px]"
      }`}
    >
      <div className="flex min-h-[57px] items-center gap-2.5 border-b border-border p-3.5">
        <div className="flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-lg bg-primary text-xs font-extrabold text-primary-foreground">
          AI
        </div>
        {!collapsed && (
          <div className="min-w-0 overflow-hidden">
            <div className="whitespace-nowrap text-sm font-extrabold">Infra Copilot</div>
          </div>
        )}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="ml-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2.5">
        {TOP_NAV.map((item) => (
          <Link key={item.href} href={item.href} className={navRowClasses(pathname === item.href)}>
            <LayoutDashboard className="h-[17px] w-[17px] flex-shrink-0" />
            {!collapsed && <span className="truncate">{item.label}</span>}
          </Link>
        ))}

        {NAV_GROUPS.map((group) => (
          <div key={group.key}>
            <button
              onClick={() => toggleGroup(group.key)}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-bold text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <Network className="h-[17px] w-[17px] flex-shrink-0" />
              {!collapsed && (
                <>
                  <span className="flex-1 text-left">{group.label}</span>
                  <ChevronDown
                    className={`h-3.5 w-3.5 flex-shrink-0 transition-transform ${
                      openGroups[group.key] ? "" : "-rotate-90"
                    }`}
                  />
                </>
              )}
            </button>
            {(!collapsed ? openGroups[group.key] : true) &&
              group.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-md py-1.5 text-xs font-semibold ${
                    collapsed ? "px-0 text-center" : "px-3 pl-[38px]"
                  } ${
                    pathname === item.href
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {collapsed ? item.label.slice(0, 2).toUpperCase() : item.label}
                </Link>
              ))}
          </div>
        ))}

        <div className="my-2.5 h-px bg-border" />

        {BOTTOM_NAV.map((item) => {
          const Icon = BOTTOM_NAV_ICONS[item.href] ?? FileText;
          return (
            <Link key={item.href} href={item.href} className={navRowClasses(pathname === item.href)}>
              <Icon className="h-[17px] w-[17px] flex-shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}

        <div className="my-2.5 h-px bg-border" />

        <Link href={AI_CHAT_NAV.href} className={navRowClasses(pathname === AI_CHAT_NAV.href)}>
          <MessageSquare className="h-[17px] w-[17px] flex-shrink-0" />
          {!collapsed && <span className="truncate">{AI_CHAT_NAV.label}</span>}
        </Link>
      </nav>

      <div className="flex items-center gap-2.5 border-t border-border p-3">
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-extrabold text-primary">
          {initials}
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1 overflow-hidden">
            <div className="truncate text-xs font-bold">{user?.full_name}</div>
            <div className="truncate text-[11px] text-muted-foreground">{user?.email}</div>
          </div>
        )}
        {!collapsed && (
          <Button variant="ghost" size="sm" title="Sign out" onClick={clear}>
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </aside>
  );
}
