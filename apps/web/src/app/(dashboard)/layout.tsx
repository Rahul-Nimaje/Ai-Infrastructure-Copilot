"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { usePathname } from "next/navigation";
import { MfaSetupCard } from "@/components/mfa-setup-card";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { useAuthStore } from "@/lib/auth-store";
import { SocketProvider } from "@/providers/socket-provider";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const accessToken = useAuthStore((s) => s.accessToken);

  const isDeviceDetailPage = pathname?.includes("/devices/");

  useEffect(() => {
    if (!accessToken) {
      router.replace("/login");
    }
  }, [accessToken, router]);

  if (!accessToken) return null;

  return (
    <SocketProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <main className="flex-1 overflow-y-auto p-6">
            <MfaSetupCard />
            {children}
          </main>
        </div>
      </div>
    </SocketProvider>
  );
}
