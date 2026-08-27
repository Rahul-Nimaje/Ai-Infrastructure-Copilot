"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Server,
  Monitor,
  Printer,
  Radio,
  Cpu,
  HardDrive,
  Activity,
  Shield,
  ShieldAlert,
  Clock,
  RefreshCw,
  KeyRound,
  CheckCircle2,
  XCircle,
  Package,
  Layers,
  Terminal,
  Zap,
  Network,
  Lock,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/providers/toast-provider";
import {
  StatusBadge,
  ProgressBar,
  Timeline,
} from "@/components/common";

import {
  PORT_LABELS,
  DANGEROUS_PORTS,
} from "@/utils/constants";
import { bytesToGB, formatDateTime } from "@/utils/formatters";

import {
  useGetDeviceByIdQuery,
  useGetDeviceHardwareQuery,
  useGetDeviceSoftwareQuery,
  useGetDeviceHistoryQuery,
  useGetDeviceProcessesQuery,
  useGetDeviceSecurityQuery,
  useGetDevicePortsQuery,
  useCollectInventoryMutation,
} from "@/features/discovery/services/discovery-api";

interface DeviceDetailPageProps {
  deviceId: string;
}

export function DeviceDetailPage({ deviceId }: DeviceDetailPageProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<"overview" | "hardware" | "software" | "processes" | "security" | "history">("overview");
  const [swSearch, setSwSearch] = useState("");
  const [procSearch, setProcSearch] = useState("");

  // Queries
  const { data: device, isLoading: isDeviceLoading, refetch: refetchDevice } = useGetDeviceByIdQuery(deviceId);
  const { data: hardware, isLoading: isHardwareLoading, refetch: refetchHardware } = useGetDeviceHardwareQuery(deviceId);
  const { data: software, isLoading: isSoftwareLoading, refetch: refetchSoftware } = useGetDeviceSoftwareQuery(deviceId);
  const { data: history, isLoading: isHistoryLoading, refetch: refetchHistory } = useGetDeviceHistoryQuery(deviceId);
  const { data: processes = [], isLoading: isProcessesLoading, refetch: refetchProcesses } = useGetDeviceProcessesQuery(deviceId);
  const { data: security, isLoading: isSecurityLoading, refetch: refetchSecurity } = useGetDeviceSecurityQuery(deviceId);
  const { data: ports = [], isLoading: isPortsLoading, refetch: refetchPorts } = useGetDevicePortsQuery(deviceId);

  // Collect Inventory Mutation
  const [collectInventory, { isLoading: isCollecting }] = useCollectInventoryMutation();

  const handleRefresh = () => {
    refetchDevice();
    refetchHardware();
    refetchSoftware();
    refetchHistory();
    refetchProcesses();
    refetchSecurity();
    refetchPorts();
    toast({ title: "Data Refreshed", description: "Latest device telemetry loaded.", variant: "info" });
  };

  const handleCollectTelemetry = async () => {
    try {
      await collectInventory(deviceId).unwrap();
      toast({
        title: "Telemetry Collection Triggered",
        description: "SSH/WinRM inventory task queued. Telemetry will update shortly.",
        variant: "success",
      });
      setTimeout(() => {
        handleRefresh();
      }, 3000);
    } catch (err: any) {
      toast({
        title: "Collection Failed",
        description: err?.data?.detail || "Could not trigger inventory collection.",
        variant: "destructive",
      });
    }
  };

  if (isDeviceLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm font-medium text-muted-foreground animate-pulse">Loading Device Details & Telemetry...</p>
      </div>
    );
  }

  if (!device) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <XCircle className="w-12 h-12 text-destructive" />
        <h2 className="text-xl font-bold text-foreground">Device Not Found</h2>
        <p className="text-sm text-muted-foreground">The requested device does not exist or has been removed.</p>
        <Button variant="outline" onClick={() => router.push("/discovery")}>
          Back to Discovery
        </Button>
      </div>
    );
  }

  const getDeviceIcon = (type: string) => {
    switch ((type || "").toLowerCase()) {
      case "server":
      case "linux":
      case "windows":
        return Server;
      case "printer":
        return Printer;
      case "network":
      case "switch":
      case "router":
        return Radio;
      default:
        return Monitor;
    }
  };

  const DeviceIcon = getDeviceIcon(device.device_type || "");

  // Filter software
  const filteredSoftware = (software?.installed_software || []).filter((s) =>
    s.name.toLowerCase().includes(swSearch.toLowerCase()) ||
    (s.publisher || "").toLowerCase().includes(swSearch.toLowerCase())
  );

  // Filter processes
  const filteredProcesses = (processes || []).filter((p) =>
    p.name.toLowerCase().includes(procSearch.toLowerCase()) ||
    (p.user_name || "").toLowerCase().includes(procSearch.toLowerCase()) ||
    p.pid.toString().includes(procSearch)
  );

  // Helper variables
  const totalRamBytes = hardware?.memory?.[0]?.total_ram_bytes || null;
  const primaryCpu = hardware?.processors?.[0] || null;
  const storagePartitions = hardware?.partitions || [];
  const networkInterfaces = hardware?.interfaces || [];

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link href="/discovery" className="flex items-center gap-1.5 hover:text-foreground transition-colors font-medium">
            <ArrowLeft className="w-4 h-4" />
            Discovery Dashboard
          </Link>
          <span>/</span>
          <span className="text-foreground font-semibold truncate max-w-xs">{device.name || device.ip_address}</span>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} className="gap-1.5 text-xs font-semibold">
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </Button>

          <Link href="/settings">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs font-semibold">
              <KeyRound className="w-3.5 h-3.5" />
              Credentials Manager
            </Button>
          </Link>

          <Button
            size="sm"
            onClick={handleCollectTelemetry}
            disabled={isCollecting}
            className="bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white font-semibold shadow-sm text-xs gap-1.5"
          >
            <Activity className={`w-3.5 h-3.5 ${isCollecting ? "animate-spin" : ""}`} />
            {isCollecting ? "Collecting..." : "Collect Telemetry"}
          </Button>
        </div>
      </div>

      {/* Hero Header Card */}
      <Card className="border border-border/80 shadow-sm bg-card overflow-hidden relative">
        <div className="absolute top-0 left-0 w-1.5 h-full bg-primary" />
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="p-3.5 rounded-xl bg-primary/10 text-primary border border-primary/20 shadow-inner">
                <DeviceIcon className="w-8 h-8" />
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-2xl font-bold tracking-tight text-foreground">{device.name || `Host ${device.ip_address}`}</h1>
                  <StatusBadge status={device.status === "online" ? "active" : "failed"} />
                  {device.scan_status && (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground capitalize border border-border">
                      Scan: {device.scan_status.replace(/_/g, " ")}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-4 text-sm text-muted-foreground flex-wrap mt-1">
                  <span className="flex items-center gap-1 font-mono text-foreground font-medium bg-muted/60 px-2 py-0.5 rounded border border-border/60">
                    IP: {device.ip_address}
                  </span>
                  {device.mac_address && (
                    <span className="font-mono text-xs">MAC: {device.mac_address}</span>
                  )}
                  {device.operating_system && (
                    <span className="flex items-center gap-1 text-foreground font-medium">
                      <Layers className="w-3.5 h-3.5 text-primary" />
                      {device.operating_system}
                    </span>
                  )}
                  {device.vendor && (
                    <span className="text-xs bg-muted px-2 py-0.5 rounded font-medium">{device.vendor}</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-6 border-t md:border-t-0 md:border-l border-border pt-4 md:pt-0 md:pl-6 text-sm">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground font-medium">Response Time</span>
                <span className="font-semibold text-foreground">
                  {device.response_time !== null ? `${device.response_time} ms` : "N/A"}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground font-medium">Last Seen</span>
                <span className="font-semibold text-foreground">
                  {device.last_seen_at ? formatDateTime(device.last_seen_at) : "Never"}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground font-medium">SSH/WinRM Auth</span>
                <span className="flex items-center gap-1 font-semibold">
                  {device.auth_success ? (
                    <span className="text-emerald-500 flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> Authenticated</span>
                  ) : (
                    <span className="text-amber-500 flex items-center gap-1"><XCircle className="w-4 h-4" /> Not Authenticated</span>
                  )}
                </span>
              </div>
            </div>
          </div>

          {device.auth_error && (
            <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              <span><strong>Auth Notice:</strong> {device.auth_error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Primary Telemetry Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border border-border/60 shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-blue-500/10 text-blue-500 border border-blue-500/20">
              <Cpu className="w-6 h-6" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Processor / CPU</span>
              <span className="text-base font-bold text-foreground truncate max-w-[180px]">
                {primaryCpu ? `${primaryCpu.processor_name || "CPU"} (${primaryCpu.cores || 1} Cores)` : "Collecting..."}
              </span>
              <span className="text-xs text-muted-foreground">Architecture: {primaryCpu?.architecture || "x86_64"}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border/60 shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
              <Zap className="w-6 h-6" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Memory (RAM)</span>
              <span className="text-base font-bold text-foreground">
                {totalRamBytes ? `${bytesToGB(totalRamBytes)} GB` : "Collecting..."}
              </span>
              <span className="text-xs text-muted-foreground">Installed RAM capacity</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border/60 shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-purple-500/10 text-purple-500 border border-purple-500/20">
              <HardDrive className="w-6 h-6" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Storage Drives</span>
              <span className="text-base font-bold text-foreground">
                {storagePartitions.length > 0 ? `${storagePartitions.length} Partition(s)` : "Collecting..."}
              </span>
              <span className="text-xs text-muted-foreground">Mounted filesystems</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border/60 shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-amber-500/10 text-amber-500 border border-amber-500/20">
              <Shield className="w-6 h-6" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Open Services / Ports</span>
              <span className="text-base font-bold text-foreground">
                {ports.length > 0 ? `${ports.length} Open Port(s)` : "Scanning..."}
              </span>
              <span className="text-xs font-medium text-amber-500">
                {ports.filter((p) => DANGEROUS_PORTS.has(p.port_number)).length} High-Risk Port(s)
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Interactive Tabs */}
      <div className="flex items-center border-b border-border gap-2 overflow-x-auto">
        <button
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeTab === "overview"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("overview")}
        >
          <Activity className="w-4 h-4" />
          Overview
        </button>

        <button
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeTab === "hardware"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("hardware")}
        >
          <Cpu className="w-4 h-4" />
          Hardware & Storage ({storagePartitions.length})
        </button>

        <button
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeTab === "software"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("software")}
        >
          <Package className="w-4 h-4" />
          Software & Services ({software?.installed_software?.length || 0})
        </button>

        <button
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeTab === "processes"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("processes")}
        >
          <Terminal className="w-4 h-4" />
          Running Processes ({processes.length})
        </button>

        <button
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeTab === "security"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("security")}
        >
          <Shield className="w-4 h-4" />
          Security Audit ({ports.length} Ports)
        </button>

        <button
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${
            activeTab === "history"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("history")}
        >
          <Clock className="w-4 h-4" />
          Audit Log History
        </button>
      </div>

      {/* TAB CONTENT: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 flex flex-col gap-6">
            {/* Storage Drives Breakdown */}
            <Card className="border border-border/60 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <HardDrive className="w-4 h-4 text-primary" />
                  Disk Partitions & Capacity
                </CardTitle>
                <CardDescription>Mounted disk storage filesystems and usage metrics.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                {storagePartitions.length > 0 ? (
                  storagePartitions.map((part, idx) => {
                    const totalGB = part.capacity_bytes ? part.capacity_bytes / (1024 * 1024 * 1024) : 0;
                    const freeGB = part.free_space_bytes ? part.free_space_bytes / (1024 * 1024 * 1024) : 0;
                    const usedGB = Math.max(0, totalGB - freeGB);
                    const pct = totalGB > 0 ? Math.round((usedGB / totalGB) * 100) : 0;

                    return (
                      <div key={idx} className="flex flex-col gap-2 p-3 rounded-lg bg-muted/40 border border-border/60">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-semibold text-foreground flex items-center gap-2">
                            <span className="font-mono text-xs px-2 py-0.5 rounded bg-muted border border-border font-bold">
                              {part.mount_point || "/"}
                            </span>
                            <span className="text-xs text-muted-foreground">({part.filesystem_type || "ext4"})</span>
                          </span>
                          <span className="text-xs font-semibold text-foreground">
                            {usedGB.toFixed(1)} GB used / {totalGB.toFixed(1)} GB total ({pct}%)
                          </span>
                        </div>
                        <ProgressBar value={pct} showPercentLabel={false} variant={pct > 85 ? "destructive" : pct > 70 ? "warning" : "success"} />
                      </div>
                    );
                  })
                ) : (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    {isHardwareLoading ? "Loading storage metrics..." : "No partition metrics collected yet. Click 'Collect Telemetry' to gather disk details."}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Network Interfaces */}
            <Card className="border border-border/60 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Network className="w-4 h-4 text-primary" />
                  Network Interfaces & Addresses
                </CardTitle>
              </CardHeader>
              <CardContent>
                {networkInterfaces.length > 0 ? (
                  <div className="divide-y divide-border">
                    {networkInterfaces.map((iface, idx) => (
                      <div key={idx} className="py-3 flex items-center justify-between gap-4 text-sm">
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-bold text-foreground px-2 py-0.5 rounded bg-muted border border-border text-xs">
                            {iface.interface_name}
                          </span>
                          <span className="font-mono text-xs text-muted-foreground">{iface.mac_address || "N/A"}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="font-mono text-xs font-semibold text-primary">{iface.ip_addresses?.[0] || device.ip_address}</span>
                          <StatusBadge status={iface.status?.toLowerCase() === "up" ? "active" : "inactive"} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-4 text-center">No additional network interface data reported.</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Quick Security & Open Ports Sidebar */}
          <div className="flex flex-col gap-6">
            <Card className="border border-border/60 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Shield className="w-4 h-4 text-primary" />
                  Detected Services & Open Ports
                </CardTitle>
              </CardHeader>
              <CardContent>
                {ports.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {ports.map((p) => {
                      const isRisk = DANGEROUS_PORTS.has(p.port_number);
                      return (
                        <div
                          key={p.port_number}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium ${
                            isRisk
                              ? "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400 font-bold"
                              : "bg-muted border-border text-foreground"
                          }`}
                        >
                          <span className="font-mono font-bold">Port {p.port_number}</span>
                          <span className="text-[11px] opacity-75">({PORT_LABELS[p.port_number] || p.service_name || "Open"})</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-4 text-center">No open ports registered yet.</p>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border/60 shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Lock className="w-4 h-4 text-primary" />
                  System Metadata
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm">
                <div className="flex justify-between py-1 border-b border-border">
                  <span className="text-muted-foreground">Device ID</span>
                  <span className="font-mono text-xs font-medium text-foreground truncate max-w-[160px]">{device.id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border">
                  <span className="text-muted-foreground">Computer Name</span>
                  <span className="font-mono text-xs font-medium text-foreground truncate max-w-[160px]">{hardware?.inventory?.computer_name || device.name}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border">
                  <span className="text-muted-foreground">Serial Number</span>
                  <span className="font-mono text-xs font-medium text-foreground truncate max-w-[160px]">{hardware?.inventory?.serial_number || "N/A"}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Vendor</span>
                  <span className="font-medium text-foreground">{device.vendor || "Linux Target"}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* TAB CONTENT: Hardware */}
      {activeTab === "hardware" && (
        <div className="flex flex-col gap-6">
          <Card className="border border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle>Processor & System Specifications</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-xs text-muted-foreground font-semibold uppercase">CPU Model</span>
                <span className="text-base font-bold text-foreground">{primaryCpu?.processor_name || "Linux Core Processor"}</span>
              </div>
              <div className="p-4 rounded-lg bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-xs text-muted-foreground font-semibold uppercase">Core Count</span>
                <span className="text-base font-bold text-foreground">{primaryCpu?.cores || 1} Cores</span>
              </div>
              <div className="p-4 rounded-lg bg-muted/40 border border-border flex flex-col gap-1">
                <span className="text-xs text-muted-foreground font-semibold uppercase">Architecture</span>
                <span className="text-base font-bold text-foreground">{primaryCpu?.architecture || "x86_64"}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle>Detailed Storage Drives & Partitions</CardTitle>
            </CardHeader>
            <CardContent>
              {storagePartitions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="py-2.5 px-3">Mount Point</th>
                        <th className="py-2.5 px-3">Filesystem</th>
                        <th className="py-2.5 px-3">Total Size</th>
                        <th className="py-2.5 px-3">Free Space</th>
                        <th className="py-2.5 px-3 text-right">Usage</th>
                      </tr>
                    </thead>
                    <tbody>
                      {storagePartitions.map((drive, idx) => {
                        const total = drive.capacity_bytes ? drive.capacity_bytes / (1024 * 1024 * 1024) : 0;
                        const free = drive.free_space_bytes ? drive.free_space_bytes / (1024 * 1024 * 1024) : 0;
                        const used = Math.max(0, total - free);
                        const pct = total > 0 ? Math.round((used / total) * 100) : 0;

                        return (
                          <tr key={idx} className="border-b border-border hover:bg-muted/30">
                            <td className="py-3 px-3 font-mono font-bold text-foreground">{drive.mount_point || "/"}</td>
                            <td className="py-3 px-3 font-mono text-xs">{drive.filesystem_type || "ext4"}</td>
                            <td className="py-3 px-3 font-semibold">{total.toFixed(1)} GB</td>
                            <td className="py-3 px-3 text-emerald-500 font-semibold">{free.toFixed(1)} GB</td>
                            <td className="py-3 px-3 text-right font-bold">{pct}%</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-4 text-center">No storage partition details recorded.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB CONTENT: Software */}
      {activeTab === "software" && (
        <div className="flex flex-col gap-6">
          <Card className="border border-border/60 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Installed Software Packages</CardTitle>
                <CardDescription>Applications and packages discovered on the target device.</CardDescription>
              </div>
              <Input
                placeholder="Search packages..."
                value={swSearch}
                onChange={(e) => setSwSearch(e.target.value)}
                className="max-w-xs text-xs"
              />
            </CardHeader>
            <CardContent>
              {filteredSoftware.length > 0 ? (
                <div className="overflow-x-auto max-h-[450px]">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-card border-b border-border text-left text-muted-foreground">
                      <tr>
                        <th className="py-2.5 px-3">Package Name</th>
                        <th className="py-2.5 px-3">Version</th>
                        <th className="py-2.5 px-3">Publisher / Vendor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSoftware.map((pkg, idx) => (
                        <tr key={idx} className="border-b border-border hover:bg-muted/30">
                          <td className="py-2.5 px-3 font-semibold text-foreground">{pkg.name}</td>
                          <td className="py-2.5 px-3 font-mono text-xs text-primary">{pkg.version || "N/A"}</td>
                          <td className="py-2.5 px-3 text-xs text-muted-foreground">{pkg.publisher || "Debian/Ubuntu"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  {swSearch ? "No software matching search term." : "No software package inventory recorded."}
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="border border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle>System Services</CardTitle>
              <CardDescription>Background daemons and systemd services status.</CardDescription>
            </CardHeader>
            <CardContent>
              {software?.services && software.services.length > 0 ? (
                <div className="overflow-x-auto max-h-[400px]">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-card border-b border-border text-left text-muted-foreground">
                      <tr>
                        <th className="py-2.5 px-3">Service Name</th>
                        <th className="py-2.5 px-3">Display Name</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Startup Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {software.services.map((svc, idx) => (
                        <tr key={idx} className="border-b border-border hover:bg-muted/30">
                          <td className="py-2.5 px-3 font-mono font-bold text-foreground">{svc.name}</td>
                          <td className="py-2.5 px-3 text-xs text-muted-foreground">{svc.display_name || svc.name}</td>
                          <td className="py-2.5 px-3">
                            <StatusBadge status={svc.status?.toLowerCase() === "running" ? "active" : "inactive"} />
                          </td>
                          <td className="py-2.5 px-3 text-xs capitalize">{svc.start_type || "Automatic"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-6 text-center">No service status details recorded.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB CONTENT: Processes */}
      {activeTab === "processes" && (
        <Card className="border border-border/60 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle>Active Running Processes</CardTitle>
              <CardDescription>Live process tree collected during inventory telemetry.</CardDescription>
            </div>
            <Input
              placeholder="Search PID or process..."
              value={procSearch}
              onChange={(e) => setProcSearch(e.target.value)}
              className="max-w-xs text-xs"
            />
          </CardHeader>
          <CardContent>
            {filteredProcesses.length > 0 ? (
              <div className="overflow-x-auto max-h-[500px]">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-card border-b border-border text-left text-muted-foreground">
                    <tr>
                      <th className="py-2.5 px-3">PID</th>
                      <th className="py-2.5 px-3">Process Name</th>
                      <th className="py-2.5 px-3">User</th>
                      <th className="py-2.5 px-3">CPU %</th>
                      <th className="py-2.5 px-3 text-right">Memory (KB)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProcesses.map((proc, idx) => (
                      <tr key={idx} className="border-b border-border hover:bg-muted/30">
                        <td className="py-2.5 px-3 font-mono font-bold text-primary">{proc.pid}</td>
                        <td className="py-2.5 px-3 font-mono text-xs font-semibold text-foreground">{proc.name}</td>
                        <td className="py-2.5 px-3 text-xs text-muted-foreground">{proc.user_name || "root"}</td>
                        <td className="py-2.5 px-3 text-xs font-mono">{proc.cpu_percent?.toFixed(1) ?? "0.0"}%</td>
                        <td className="py-2.5 px-3 text-right font-mono text-xs">{proc.memory_bytes ? (proc.memory_bytes / 1024).toFixed(0) : "0"} KB</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center">
                {procSearch ? "No process matching query." : "No running processes recorded."}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* TAB CONTENT: Security */}
      {activeTab === "security" && (
        <div className="flex flex-col gap-6">
          <Card className="border border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle>Port Security Audit</CardTitle>
              <CardDescription>Audit of network ports and potentially exposed services.</CardDescription>
            </CardHeader>
            <CardContent>
              {ports.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="py-2.5 px-3">Port</th>
                        <th className="py-2.5 px-3">Protocol</th>
                        <th className="py-2.5 px-3">Service</th>
                        <th className="py-2.5 px-3">Risk Assessment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ports.map((p, idx) => {
                        const isRisk = DANGEROUS_PORTS.has(p.port_number);
                        return (
                          <tr key={idx} className="border-b border-border hover:bg-muted/30">
                            <td className="py-3 px-3 font-mono font-bold text-foreground">{p.port_number}</td>
                            <td className="py-3 px-3 font-mono text-xs uppercase">{p.protocol || "tcp"}</td>
                            <td className="py-3 px-3 font-semibold text-primary">{PORT_LABELS[p.port_number] || p.service_name || "Unknown"}</td>
                            <td className="py-3 px-3">
                              {isRisk ? (
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                                  <ShieldAlert className="w-3.5 h-3.5" /> High Exposure Port
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
                                  Standard Service
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-6 text-center">No open port security audit data available.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB CONTENT: History */}
      {activeTab === "history" && (
        <Card className="border border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>Audit Log & Scan Event Timeline</CardTitle>
            <CardDescription>Historical record of discovery scans and inventory updates.</CardDescription>
          </CardHeader>
          <CardContent>
            {history?.scan_history && history.scan_history.length > 0 ? (
              <Timeline
                events={history.scan_history.map((h) => ({
                  id: h.id,
                  timestamp: h.created_at,
                  content: (
                    <div className="flex flex-col gap-0.5">
                      <span className="font-semibold text-foreground">Scan status: {h.status}</span>
                      <span className="text-xs text-muted-foreground">Response time: {h.response_time !== null ? `${h.response_time} ms` : "N/A"}</span>
                    </div>
                  ),
                  badge: {
                    label: h.status,
                    variant: h.status === "completed" || h.status === "online" ? "success" : "destructive",
                  },
                }))}
              />
            ) : (
              <p className="text-sm text-muted-foreground py-6 text-center">No scan event history available.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
