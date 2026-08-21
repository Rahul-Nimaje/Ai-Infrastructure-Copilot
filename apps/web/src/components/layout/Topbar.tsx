"use client";

import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useQuery } from "@tanstack/react-query";
import { Bell, ChevronDown, Moon, Search, Sparkles, Sun } from "lucide-react";
import type { Server } from "@ai-infra-copilot/shared-types";

import { apiFetch } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";

function orgLabelFromEmail(email: string | undefined): string {
  const domain = email?.split("@")[1]?.split(".")[0];
  if (!domain) return "Organization";
  return domain[0].toUpperCase() + domain.slice(1);
}

export function Topbar() {
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const user = useAuthStore((s) => s.user);

  const { data } = useQuery({
    queryKey: ["servers"],
    queryFn: () => apiFetch<{ data: Server[] }>("/api/v1/servers"),
  });
  const servers = data?.data ?? [];
  const healthyCount = servers.filter((s) => s.health_status === "healthy").length;

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "?";

  return (
    <div className="flex h-[57px] min-h-[57px] items-center gap-2.5 border-b border-border bg-card px-[18px]">
      <div className="flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm">
        <span className="font-bold">{orgLabelFromEmail(user?.email)}</span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
      </div>

      <div className="flex w-[340px] items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-muted-foreground">
        <Search className="h-4 w-4 flex-shrink-0" />
        <span className="text-sm">Search servers, users, scripts…</span>
        <span className="ml-auto rounded border border-border bg-muted px-1 font-mono text-[10.5px]">⌘K</span>
      </div>

      <div className="flex-1" />

      {servers.length > 0 && (
        <div className="flex flex-shrink-0 items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span>
            {healthyCount}/{servers.length} healthy
          </span>
        </div>
      )}

      <button
        className="flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
        title="Notifications"
      >
        <Bell className="h-[17px] w-[17px]" />
      </button>

      <button
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        className="flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
        title="Toggle theme"
      >
        {theme === "dark" ? <Sun className="h-[17px] w-[17px]" /> : <Moon className="h-[17px] w-[17px]" />}
      </button>

      <div className="h-6 w-px flex-shrink-0 bg-border" />

      <button
        onClick={() => router.push("/ai-chat")}
        className="flex flex-shrink-0 items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-bold text-primary-foreground hover:opacity-90"
      >
        <Sparkles className="h-3.5 w-3.5" />
        Ask Copilot
      </button>

      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11.5px] font-extrabold text-primary">
        {initials}
      </div>
    </div>
  );
}
