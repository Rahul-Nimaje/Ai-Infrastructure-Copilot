"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Device } from "@ai-infra-copilot/shared-types";
import {
  Network,
  RefreshCw,
  Clock,
  Radio,
  History,
  ShieldAlert,
  Database,
  ChevronRight,
  Shield,
  Server,
  Printer,
  Monitor,
  KeyRound,
  XCircle,
  CheckCircle2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/providers/toast-provider";

import {
  PageHeader,
  StatCard,
  SearchInput,
  FilterSelect,
  DataTable,
  Drawer,
  InfoGrid,
  Timeline,
  StatusBadge,
  ProgressBar,
} from "@/components/common";

import {
  DEVICE_DETAIL_TABS,
  DEVICE_TYPE_OPTIONS,
  VENDOR_OPTIONS,
  LATENCY_OPTIONS,
  LAST_SEEN_OPTIONS,
  SCAN_STATUS_FILTER_OPTIONS,
  PORT_LABELS,
  DANGEROUS_PORTS,
} from "@/utils/constants";

import { getDeviceIconColor } from "@/utils/mappers";
import { formatBytes, bytesToGB, mhzToGhz, formatDateTime } from "@/utils/formatters";
import type { StartScanFormValues } from "@/schemas/discovery-scan.schema";

import {
  useGetDiscoveryDevicesQuery,
  useGetDiscoveryScansQuery,
  useGetDeviceHardwareQuery,
  useGetDeviceSoftwareQuery,
  useGetDeviceHistoryQuery,
  useGetDeviceProcessesQuery,
  useGetDeviceSecurityQuery,
  useStartScanMutation,
  useStopScanMutation,
  useCollectInventoryMutation,
  useCollectAllInventoryMutation,
} from "@/features/discovery/services/discovery-api";
import { ScanControlPanel } from "@/features/discovery/components/ScanControlPanel";
import { computeDeviceStats } from "@/features/discovery/utils/scan-stats";

export function DiscoveryDashboard() {
  const router = useRouter();
  const { toast } = useToast();

  // Search & Filter States
  const [search, setSearch] = useState("");
  const [deviceType, setDeviceType] = useState("");
  const [vendor, setVendor] = useState("");
  const [status, setStatus] = useState("");
  const [scanStatus, setScanStatus] = useState("");
  const [responseTime, setResponseTime] = useState("");
  const [lastSeen, setLastSeen] = useState("");
  const [sortBy] = useState("last_seen_at");
  const [sortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);

  // Selected device for side drawer detail view
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);

  // 1. Query Active/Past Scans (Poll only when a scan is active)
  const { data: scansList = [], isLoading: isScansLoading } = useGetDiscoveryScansQuery(undefined, {
    pollingInterval: 0,
  });

  // Check if there is an active running scan right now
  const activeScan = scansList.find((s) =>
    ["pending", "discovering", "identifying", "scanning", "running"].includes(s.status)
  );

  // 2. Query Devices List (Paginated, Filtered, poll only when scan is active)
  const { data: devicesData, isLoading: isDevicesLoading, refetch: refetchDevices } = useGetDiscoveryDevicesQuery({
    page,
    size: pageSize,
    sort_by: sortBy,
    sort_order: sortOrder,
    search,
    device_type: deviceType,
    vendor,
    status,
    scan_status: scanStatus,
    response_time: responseTime,
    last_seen: lastSeen,
  }, { pollingInterval: activeScan ? 5000 : 0 });

  // Re-query scans with polling enabled when scan is active
  const { data: _scansListActive } = useGetDiscoveryScansQuery(undefined, {
    pollingInterval: activeScan ? 3000 : 0,
    skip: !activeScan,
  });

  const [activeTab, setActiveTab] = useState("overview");

  // 3. Query Detailed Hardware Profile
  const { data: hardwareDetails = null, isLoading: isHardwareLoading, refetch: refetchHardware } = useGetDeviceHardwareQuery(
    selectedDevice?.id ?? "",
    { skip: !selectedDevice }
  );

  // 4. Query Detailed Software & Services Profile
  const { data: softwareDetails = null, isLoading: isSoftwareLoading, refetch: refetchSoftware } = useGetDeviceSoftwareQuery(
    selectedDevice?.id ?? "",
    { skip: !selectedDevice }
  );

  // 5. Query Combined History (IP changes, scans, inventory changes)
  const { data: allHistoryDetails = null, isLoading: isHistoryLoading, refetch: refetchHistory } = useGetDeviceHistoryQuery(
    selectedDevice?.id ?? "",
    { skip: !selectedDevice }
  );

  // 6. Query Processes (Full-scan only data)
  const { data: processes = [], isLoading: isProcessesLoading } = useGetDeviceProcessesQuery(
    selectedDevice?.id ?? "",
    { skip: !selectedDevice }
  );

  // 7. Query Security Posture (Full-scan only data)
  const { data: security = null, isLoading: isSecurityLoading } = useGetDeviceSecurityQuery(
    selectedDevice?.id ?? "",
    { skip: !selectedDevice }
  );

  // Mutations
  const [startScan, { isLoading: isStartScanLoading }] = useStartScanMutation();
  const [stopScan, { isLoading: isStopScanLoading }] = useStopScanMutation();
  const [collectInventory, { isLoading: isCollectPending }] = useCollectInventoryMutation();
  const [collectAllInventory, { isLoading: isCollectAllPending }] = useCollectAllInventoryMutation();

  const handleStartScan = async (values: StartScanFormValues) => {
    if (activeScan) return;
    try {
      await startScan(values).unwrap();
      toast({
        title: "Scan Started",
        description: "Network discovery scan sweep has been initiated successfully.",
        variant: "success"
      });
    } catch (err: any) {
      toast({
        title: "Scan Initialization Failed",
        description: err?.data?.error?.message ?? err?.message ?? "Failed to start network scan sweep.",
        variant: "destructive"
      });
    }
  };

  const handleStopScan = async () => {
    if (!activeScan) return;
    try {
      await stopScan(activeScan.id).unwrap();
      toast({
        title: "Scan Terminated",
        description: "Network discovery scan sweep has been stopped.",
        variant: "info"
      });
    } catch (err: any) {
      toast({
        title: "Scan Termination Failed",
        description: err?.data?.error?.message ?? err?.message ?? "Failed to stop scan.",
        variant: "destructive"
      });
    }
  };

  const handleCollectInventory = async (deviceId: string) => {
    try {
      await collectInventory(deviceId).unwrap();
      toast({
        title: "Collection Initiated",
        description: "Hardware and software inventory collection has been scheduled in the background.",
        variant: "success"
      });
      setTimeout(() => {
        refetchDevices();
        refetchHardware();
        refetchSoftware();
        refetchHistory();
      }, 3000);
    } catch (err: any) {
      toast({
        title: "Collection Failed",
        description: err?.data?.error?.message ?? err?.message ?? "Failed to trigger inventory collection.",
        variant: "destructive"
      });
    }
  };

  const handleCollectAllInventory = async () => {
    try {
      await collectAllInventory().unwrap();
      toast({
        title: "Batch Collection Enqueued",
        description: "Scheduled inventory collection tasks for all online hosts.",
        variant: "success"
      });
    } catch (err: any) {
      toast({
        title: "Batch Collection Failed",
        description: err?.data?.error?.message ?? err?.message ?? "Failed to trigger batch inventory collection.",
        variant: "destructive"
      });
    }
  };

  const getDeviceIcon = (type: string) => {
    const colorClass = getDeviceIconColor(type);
    const t = type?.toLowerCase();
    if (t?.includes("server")) return <Server className={`h-4 w-4 ${colorClass}`} />;
    if (t?.includes("printer")) return <Printer className={`h-4 w-4 ${colorClass}`} />;
    if (t?.includes("switch") || t?.includes("router") || t?.includes("firewall")) {
      return <Network className={`h-4 w-4 ${colorClass}`} />;
    }
    return <Monitor className={`h-4 w-4 ${colorClass}`} />;
  };

  // Stats derivation (section 13 — Total/Online/Offline/Scanning/Completed/Failed/Credentials Required)
  const stats = computeDeviceStats(devicesData?.items || [], devicesData?.total || 0);

  // Columns definition for DataTable
  const tableColumns = [
    {
      key: "name",
      header: "Device Name / IP",
      sortable: false,
      render: (device: Device) => (
        <div className="flex items-center gap-2.5">
          {getDeviceIcon(device.device_type)}
          <div>
            <Link href={`/discovery/devices/${device.id}`} className="font-semibold text-foreground text-sm hover:text-primary hover:underline transition-colors">
              {device.name}
            </Link>
            <div className="text-muted-foreground font-mono text-[10px]">{device.ip_address || "—"}</div>
          </div>
        </div>
      ),
    },
    {
      key: "mac_address",
      header: "MAC Address",
      render: (device: Device) => <span className="font-mono text-muted-foreground text-[10px]">{device.mac_address || "—"}</span>,
    },
    {
      key: "operating_system",
      header: "OS / Hardware",
      render: (device: Device) => (
        <div>
          <div className="font-semibold">{device.operating_system || "Unknown OS"}</div>
          <div className="text-[10px] text-muted-foreground">{device.vendor} {device.model}</div>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (device: Device) => <StatusBadge status={device.status} />,
    },
    {
      key: "scan_status",
      header: "Scan Status",
      render: (device: Device) => device.scan_status ? <StatusBadge status={device.scan_status} /> : <span className="text-muted-foreground">—</span>,
    },
    {
      key: "response_time",
      header: "Latency",
      render: (device: Device) => (
        <span className="font-mono font-bold text-foreground">
          {device.response_time !== null ? `${device.response_time} ms` : "—"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      headerClassName: "text-right",
      className: "text-right",
      render: () => <ChevronRight className="h-4 w-4 inline-block text-muted-foreground" />,
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Reusable PageHeader */}
      <PageHeader
        title="Network Device Discovery"
        description="Scan subnet ranges to progressively discover, identify, and inventory infrastructure assets."
      >
        <div className="flex items-center gap-2">
          <Link href="/settings">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs font-semibold">
              <KeyRound className="h-3.5 w-3.5 text-amber-500" />
              Manage Credentials
            </Button>
          </Link>
          <Button
            onClick={() => handleCollectAllInventory()}
            disabled={isCollectAllPending}
            className="gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-xs font-bold shadow-md text-white"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isCollectAllPending ? "animate-spin" : ""}`} />
            Collect All Inventory
          </Button>
        </div>
      </PageHeader>

      {/* Discovery Dashboard Stats using StatCard */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4 lg:grid-cols-7">
        <StatCard label="Total" value={stats.total} icon={Database} />
        <StatCard label="Online" value={stats.online} icon={Radio} iconColor="text-emerald-600" iconBgColor="bg-emerald-500/10" pulse />
        <StatCard label="Offline" value={stats.offline} icon={XCircle} iconColor="text-muted-foreground" iconBgColor="bg-muted" />
        <StatCard label="Scanning" value={stats.scanning} icon={RefreshCw} iconColor="text-blue-600" iconBgColor="bg-blue-500/10" />
        <StatCard label="Completed" value={stats.completed} icon={CheckCircle2} iconColor="text-emerald-600" iconBgColor="bg-emerald-500/10" />
        <StatCard label="Failed" value={stats.failed} icon={ShieldAlert} iconColor="text-destructive" iconBgColor="bg-destructive/10" />
        <StatCard label="Creds Required" value={stats.credentialsRequired} icon={KeyRound} iconColor="text-amber-600" iconBgColor="bg-amber-500/10" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left column: Scan Controls & History */}
        <div className="lg:col-span-1 space-y-6">
          <ScanControlPanel
            activeScan={activeScan}
            onStartScan={handleStartScan}
            onStopScan={handleStopScan}
            isStartLoading={isStartScanLoading}
            isStopLoading={isStopScanLoading}
          />

          {/* Scans History */}
          <Card className="border-border/60 shadow-sm max-h-[350px] overflow-y-auto">
            <CardHeader className="p-4 border-b border-border/60">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <History className="h-4 w-4 text-muted-foreground" />
                Scan History Audit
              </CardTitle>
            </CardHeader>
            <CardContent className="p-2 divide-y divide-border/60">
              {isScansLoading ? (
                <div className="p-4 text-center text-xs text-muted-foreground animate-pulse">Loading scan history...</div>
              ) : scansList.length === 0 ? (
                <div className="p-4 text-center text-xs text-muted-foreground">No scans logged yet.</div>
              ) : (
                scansList.map((scan) => (
                  <div key={scan.id} className="p-3 hover:bg-muted/10 transition-colors text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold font-mono">{scan.target_range}</span>
                      <StatusBadge status={scan.status} />
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Found: <span className="font-bold text-foreground">{scan.devices_found} devices</span></span>
                      <span>Mode: <span className="capitalize">{scan.scan_type.replace("_", " ")}</span></span>
                    </div>
                    {scan.error_message && (
                      <p className="text-[10px] text-destructive italic bg-destructive/5 p-1 rounded border border-destructive/10">
                        {scan.error_message}
                      </p>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right column: Devices List with Filters */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex flex-col gap-4 bg-card border border-border/60 rounded-lg p-6 shadow-md">
            {/* Filters Header */}
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <h3 className="text-lg font-bold">Discovered Devices</h3>
                <p className="text-xs text-muted-foreground">Network nodes mapped during scans.</p>
              </div>
              <SearchInput
                placeholder="Search hostname, IP, MAC..."
                value={search}
                onChange={(val) => {
                  setSearch(val);
                  setPage(1);
                }}
                className="w-full md:w-[220px]"
              />
            </div>

            {/* Filter select inputs */}
            <div className="grid grid-cols-2 gap-2 md:grid-cols-5 text-xs">
              <FilterSelect
                label="Type"
                value={deviceType}
                onChange={(val) => {
                  setDeviceType(val);
                  setPage(1);
                }}
                options={DEVICE_TYPE_OPTIONS}
              />
              <FilterSelect
                label="Vendor"
                value={vendor}
                onChange={(val) => {
                  setVendor(val);
                  setPage(1);
                }}
                options={VENDOR_OPTIONS}
              />
              <FilterSelect
                label="Scan Status"
                value={scanStatus}
                onChange={(val) => {
                  setScanStatus(val);
                  setPage(1);
                }}
                options={SCAN_STATUS_FILTER_OPTIONS}
              />
              <FilterSelect
                label="Latency"
                value={responseTime}
                onChange={(val) => {
                  setResponseTime(val);
                  setPage(1);
                }}
                options={LATENCY_OPTIONS}
              />
              <FilterSelect
                label="Last Seen"
                value={lastSeen}
                onChange={(val) => {
                  setLastSeen(val);
                  setPage(1);
                }}
                options={LAST_SEEN_OPTIONS}
              />
            </div>
          </div>

          {/* DataTable Component replaces inline table and pagination */}
          <DataTable
            columns={tableColumns}
            data={devicesData?.items || []}
            loading={isDevicesLoading}
            loadingMessage="Loading discovered devices inventory..."
            rowKey={(device: Device) => device.id}
            onRowClick={(device: Device) => {
              router.push(`/discovery/devices/${device.id}`);
            }}
            isRowActive={(device: Device) => selectedDevice?.id === device.id}
            page={page}
            pageSize={pageSize}
            total={devicesData?.total || 0}
            onPageChange={setPage}
            paginationLabel="discovered nodes"
          />
        </div>
      </div>

      {/* Side drawer for detailed device info */}
      <Drawer
        open={!!selectedDevice}
        onClose={() => setSelectedDevice(null)}
        title={selectedDevice?.name || "Device Details"}
        subtitle={selectedDevice?.ip_address || "No IP Address"}
        headerIcon={selectedDevice ? getDeviceIcon(selectedDevice.device_type) : null}
        tabs={DEVICE_DETAIL_TABS}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      >
        {selectedDevice && (
          <>
            <div className="flex justify-end pb-2">
              <Link href={`/discovery/devices/${selectedDevice.id}`}>
                <Button variant="outline" size="sm" className="gap-1.5 text-xs font-bold text-primary border-primary/30 hover:bg-primary/10 shadow-sm">
                  Open Dedicated Device Page ↗
                </Button>
              </Link>
            </div>

            {/* Overview Tab */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {selectedDevice.scan_status === "credentials_required" && (
                  <div className="p-4 rounded-lg border border-amber-500/20 bg-amber-500/5 text-amber-700 dark:text-amber-400 flex items-start gap-3">
                    <KeyRound className="h-5 w-5 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider">Credentials Required</h4>
                      <p className="text-xs mt-1 opacity-90">
                        No matching credential was found for this device&apos;s protocol. Add a WinRM/SSH/SNMP
                        credential to the organization&apos;s credential store, then re-run Full Scan or Collect
                        Telemetry.
                      </p>
                    </div>
                  </div>
                )}

                {selectedDevice.auth_success !== undefined && selectedDevice.auth_error !== null && (
                  <div className={`p-4 rounded-lg border flex items-start gap-3 ${
                    selectedDevice.auth_success
                       ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400"
                      : "border-destructive/20 bg-destructive/5 text-destructive"
                  }`}>
                    {selectedDevice.auth_success ? (
                      <Shield className="h-5 w-5 shrink-0 mt-0.5 text-emerald-500" />
                    ) : (
                      <ShieldAlert className="h-5 w-5 shrink-0 mt-0.5 text-destructive" />
                    )}
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider">
                        {selectedDevice.auth_success ? "Credentials Authenticated" : "Authentication Failure"}
                      </h4>
                      <p className="text-xs mt-1 opacity-90">
                        {selectedDevice.auth_success
                          ? "Secure protocol connection established successfully during last sweep."
                          : selectedDevice.auth_error || "SSH/WinRM/SNMP credentials failed or were not found."
                        }
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex justify-between items-center bg-muted/20 p-4 rounded-lg border border-border/60">
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Hardware Telemetry</h4>
                    <p className="text-xs text-muted-foreground">Collect detailed CPU, memory, storage, and software lists.</p>
                  </div>
                  <Button
                    onClick={() => handleCollectInventory(selectedDevice.id)}
                    disabled={isCollectPending || selectedDevice.status.toLowerCase() !== "online"}
                    size="sm"
                    className="gap-1.5 text-xs font-bold bg-primary text-white"
                  >
                    <RefreshCw className={`h-3 w-3 ${isCollectPending ? "animate-spin" : ""}`} />
                    Collect Telemetry
                  </Button>
                </div>

                <InfoGrid
                  items={[
                    { label: "Status", value: <StatusBadge status={selectedDevice.status} /> },
                    { label: "Scan Status", value: selectedDevice.scan_status ? <StatusBadge status={selectedDevice.scan_status} /> : "—" },
                    { label: "Response Time", value: selectedDevice.response_time !== null ? `${selectedDevice.response_time} ms` : "—", mono: true },
                    { label: "Device Type", value: selectedDevice.device_type.replace("_", " ") },
                    { label: "Identification Confidence", value: selectedDevice.identification_confidence || "—" },
                    { label: "Operating System", value: selectedDevice.operating_system },
                    { label: "Manufacturer", value: selectedDevice.vendor },
                    { label: "Model Specs", value: selectedDevice.model },
                    { label: "First Discovered", value: formatDateTime(selectedDevice.first_seen_at || selectedDevice.created_at), colSpan: 2 },
                    { label: "Last Seen", value: formatDateTime(selectedDevice.last_seen_at), colSpan: 2 },
                  ]}
                />
              </div>
            )}

            {/* Hardware Tab */}
            {activeTab === "hardware" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading hardware specs...</p>
                ) : !hardwareDetails?.inventory ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No hardware inventory records exist. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <InfoGrid
                    items={[
                      { label: "Computer Name", value: hardwareDetails.inventory.computer_name, mono: true },
                      { label: "Chassis Serial", value: hardwareDetails.inventory.serial_number, mono: true },
                      { label: "Manufacturer", value: hardwareDetails.inventory.manufacturer },
                      { label: "Model", value: hardwareDetails.inventory.model },
                      { label: "BIOS Version", value: hardwareDetails.inventory.bios_version, mono: true },
                      { label: "Motherboard", value: hardwareDetails.inventory.motherboard, mono: true },
                      { label: "Active Domain", value: hardwareDetails.inventory.domain, mono: true },
                      { label: "Workgroup", value: hardwareDetails.inventory.workgroup, mono: true },
                    ]}
                  />
                )}
              </div>
            )}

            {/* CPU Tab */}
            {activeTab === "cpu" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading processor profile...</p>
                ) : !hardwareDetails?.processors?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No processor records exist. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.processors.map((proc) => (
                      <div key={proc.id} className="rounded-lg border border-border p-4 bg-muted/5 space-y-3">
                        <div className="flex justify-between items-start">
                          <div>
                            <span className="text-[10px] font-bold text-muted-foreground uppercase">Processor Model</span>
                            <h4 className="text-sm font-bold text-foreground mt-0.5">{proc.processor_name}</h4>
                          </div>
                          {proc.socket_designation && <span className="text-[10px] font-mono text-muted-foreground">{proc.socket_designation}</span>}
                        </div>
                        <InfoGrid
                          columns={3}
                          items={[
                            { label: "Physical Cores", value: proc.cores },
                            { label: "Logical Threads", value: proc.logical_processors },
                            { label: "Current Speed", value: mhzToGhz(proc.current_speed_mhz) },
                            { label: "Max Speed", value: mhzToGhz(proc.max_speed_mhz) },
                          ]}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Memory Tab */}
            {activeTab === "memory" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading memory profile...</p>
                ) : !hardwareDetails?.memory?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No memory records exist. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.memory.map((mem, idx) => {
                      const usedPct = mem.total_ram_bytes && mem.available_ram_bytes
                        ? Math.round(((mem.total_ram_bytes - mem.available_ram_bytes) / mem.total_ram_bytes) * 100)
                        : null;
                      return (
                      <div key={idx} className="space-y-4">
                        <InfoGrid
                          columns={3}
                          items={[
                            { label: "Total RAM", value: bytesToGB(mem.total_ram_bytes) },
                            { label: "Available RAM", value: bytesToGB(mem.available_ram_bytes, 1) },
                            { label: "Configured Speed", value: mem.configured_speed_mhz ? `${mem.configured_speed_mhz} MHz` : "—" },
                          ]}
                        />
                        {usedPct !== null && <ProgressBar value={usedPct} label="Memory Used" size="sm" />}

                        {mem.ram_modules && mem.ram_modules.length > 0 && (
                          <div>
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-2 text-[10px]">Installed Modules</span>
                            <div className="mt-2 rounded-lg border border-border overflow-hidden text-xs">
                              <table className="w-full text-left">
                                <thead>
                                  <tr className="bg-muted/40 border-b border-border font-bold">
                                    <th className="p-2">Slot</th>
                                    <th className="p-2">Manufacturer</th>
                                    <th className="p-2">Capacity</th>
                                    <th className="p-2">Speed</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border/60">
                                  {mem.ram_modules.map((mod, midx) => (
                                    <tr key={midx} className="hover:bg-muted/10">
                                      <td className="p-2 font-mono">{mod.slot || "—"}</td>
                                      <td className="p-2">{mod.manufacturer || "—"}</td>
                                      <td className="p-2">{mod.capacity ?? "—"}</td>
                                      <td className="p-2">{mod.speed_mhz ?? "—"}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Storage Tab */}
            {activeTab === "storage" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading storage details...</p>
                ) : !hardwareDetails?.storage?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No storage records exist. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.storage.map((disk, idx) => {
                      const pctUsed = disk.capacity_bytes && disk.free_space_bytes !== null
                        ? Math.round(((disk.capacity_bytes - (disk.free_space_bytes ?? 0)) / disk.capacity_bytes) * 100)
                        : 0;

                      return (
                        <div key={disk.id ?? idx} className="rounded-lg border border-border p-4 bg-muted/5 space-y-3">
                          <div className="flex justify-between items-start">
                            <div>
                              <span className="text-[10px] font-bold text-muted-foreground uppercase">
                                {disk.media_type ? `${disk.media_type} Disk` : "Disk Unit"}
                              </span>
                              <h4 className="text-sm font-bold text-foreground mt-0.5">{disk.disk_model || "Unknown Disk Model"}</h4>
                            </div>
                            <span className="text-[10px] font-mono text-muted-foreground">S/N: {disk.serial_number || "—"}</span>
                          </div>

                          <InfoGrid
                            columns={3}
                            items={[
                              { label: "Interface", value: disk.interface_type || "—" },
                              { label: "Health", value: disk.health_status || "—" },
                              { label: "Capacity", value: bytesToGB(disk.capacity_bytes) },
                            ]}
                          />
                          <ProgressBar value={pctUsed} label="Disk Used" sublabel={`Free: ${bytesToGB(disk.free_space_bytes)}`} size="sm" />

                          {disk.partitions && disk.partitions.length > 0 && (
                            <div className="pt-2 border-t border-border/40 text-[10px] space-y-1">
                              <span className="font-bold text-muted-foreground uppercase">Logical Volumes</span>
                              <div className="flex gap-2 flex-wrap">
                                {disk.partitions.map((part, pidx) => (
                                  <StatusBadge key={pidx} status={`${part.name} (${bytesToGB(part.size_bytes)})`} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                {hardwareDetails?.partitions && hardwareDetails.partitions.length > 0 && (
                  <div className="rounded-lg border border-border overflow-hidden text-xs">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase p-2 block">All Partitions</span>
                    <table className="w-full text-left">
                      <thead>
                        <tr className="bg-muted/40 border-b border-border font-bold">
                          <th className="p-2">Mount / Node</th>
                          <th className="p-2">Filesystem</th>
                          <th className="p-2">Used</th>
                          <th className="p-2">Free</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {hardwareDetails.partitions.map((part) => (
                          <tr key={part.id} className="hover:bg-muted/10">
                            <td className="p-2 font-mono">{part.mount_point || part.device_node || "—"}</td>
                            <td className="p-2">{part.filesystem_type || "—"}</td>
                            <td className="p-2">{bytesToGB(part.used_bytes)}</td>
                            <td className="p-2">{bytesToGB(part.free_space_bytes)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Operating System Tab */}
            {activeTab === "os" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading OS details...</p>
                ) : !hardwareDetails?.inventory ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No operating system records exist. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <InfoGrid
                    items={[
                      { label: "OS Name & Edition", value: `${hardwareDetails.inventory.os_name || "Unknown"} ${hardwareDetails.inventory.os_edition ? `(${hardwareDetails.inventory.os_edition})` : ""}`, colSpan: 2 },
                      { label: "OS Version", value: hardwareDetails.inventory.os_version, mono: true },
                      { label: "OS Build", value: hardwareDetails.inventory.os_build, mono: true },
                      { label: "Time Zone", value: hardwareDetails.inventory.os_timezone },
                      { label: "Uptime", value: hardwareDetails.inventory.uptime, mono: true },
                      { label: "Antivirus", value: hardwareDetails.inventory.antivirus || "Not Detected" },
                      { label: "Encryption / BitLocker", value: hardwareDetails.inventory.bitlocker_status || "Not Detected" },
                      { label: "Local Firewall", value: hardwareDetails.inventory.firewall_status || "Not Detected" },
                      { label: "Installation Date", value: formatDateTime(hardwareDetails.inventory.os_install_date) },
                      { label: "Last Boot Timestamp", value: formatDateTime(hardwareDetails.inventory.os_last_boot), colSpan: 2 },
                    ]}
                  />
                )}
              </div>
            )}

            {/* Network Interfaces Tab */}
            {activeTab === "network" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading interface metrics...</p>
                ) : !hardwareDetails?.interfaces?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No network interface profile exists. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.interfaces.map((net) => (
                      <div key={net.id} className="rounded-lg border border-border p-4 bg-muted/5 space-y-3">
                        <div className="flex justify-between items-center">
                          <h4 className="text-xs font-bold text-foreground font-mono uppercase tracking-wide flex items-center gap-1.5">
                            <Network className="h-3.5 w-3.5 text-indigo-500" />
                            {net.interface_name}
                          </h4>
                          <StatusBadge status={net.status === "up" ? "active" : "failed"} />
                        </div>
                        <InfoGrid
                          items={[
                            { label: "IP Addresses", value: net.ip_addresses?.join(", "), colSpan: 2, mono: true },
                            { label: "MAC Address", value: net.mac_address, mono: true },
                            { label: "Default Gateway", value: net.gateway, mono: true },
                            { label: "DNS Servers", value: net.dns_servers?.join(", "), mono: true },
                            { label: "DHCP Connection", value: net.dhcp_enabled ? "Enabled" : "Static IP" },
                            { label: "Link Speed", value: net.speed_mbps ? `${net.speed_mbps} Mbps` : "—" },
                          ]}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Software Tab */}
            {activeTab === "software" && (
              <div className="space-y-4">
                {isSoftwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading software register...</p>
                ) : !softwareDetails?.installed_software?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No software directory exists. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div>
                    <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-3 text-[10px]">
                      Installed Software ({softwareDetails.installed_software.length})
                    </span>
                    <div className="rounded-lg border border-border overflow-hidden text-xs max-h-[400px] overflow-y-auto">
                      <table className="w-full text-left">
                        <thead>
                          <tr className="bg-muted/40 border-b border-border font-bold">
                            <th className="p-2">Name</th>
                            <th className="p-2">Version</th>
                            <th className="p-2">Publisher</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60">
                          {softwareDetails.installed_software.map((sw) => (
                            <tr key={sw.id} className="hover:bg-muted/10">
                              <td className="p-2 font-semibold text-foreground">{sw.name}</td>
                              <td className="p-2 font-mono text-muted-foreground text-[10px]">{sw.version || "—"}</td>
                              <td className="p-2 text-muted-foreground">{sw.publisher || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Services Tab */}
            {activeTab === "services" && (
              <div className="space-y-4">
                {isSoftwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading service registry...</p>
                ) : !softwareDetails?.services?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No services directory exists. Run a Full Scan or collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div>
                    <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-3 text-[10px]">
                      System Services ({softwareDetails.services.length})
                    </span>
                    <div className="rounded-lg border border-border overflow-hidden text-xs max-h-[400px] overflow-y-auto">
                      <table className="w-full text-left">
                        <thead>
                          <tr className="bg-muted/40 border-b border-border font-bold">
                            <th className="p-2">Display Name</th>
                            <th className="p-2">Status</th>
                            <th className="p-2">Start Type</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60">
                          {softwareDetails.services.map((srv) => (
                            <tr key={srv.id} className="hover:bg-muted/10">
                              <td className="p-2">
                                <div className="font-semibold text-foreground">{srv.display_name || srv.name}</div>
                                <div className="text-[10px] text-muted-foreground font-mono">{srv.name}</div>
                              </td>
                              <td className="p-2">
                                <StatusBadge status={srv.status || "unknown"} />
                              </td>
                              <td className="p-2 text-muted-foreground capitalize text-[10px]">{srv.start_type || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Processes Tab */}
            {activeTab === "processes" && (
              <div className="space-y-4">
                {isProcessesLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading process snapshot...</p>
                ) : !processes.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No process snapshot exists. Run a Full Scan to capture running processes.
                  </div>
                ) : (
                  <div>
                    <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-3 text-[10px]">
                      Running Processes ({processes.length}) — snapshot at {formatDateTime(processes[0]?.collected_at)}
                    </span>
                    <div className="rounded-lg border border-border overflow-hidden text-xs max-h-[400px] overflow-y-auto">
                      <table className="w-full text-left">
                        <thead>
                          <tr className="bg-muted/40 border-b border-border font-bold">
                            <th className="p-2">PID</th>
                            <th className="p-2">Name</th>
                            <th className="p-2">User</th>
                            <th className="p-2">CPU %</th>
                            <th className="p-2">Memory</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60">
                          {processes.map((proc) => (
                            <tr key={proc.id} className="hover:bg-muted/10">
                              <td className="p-2 font-mono">{proc.pid}</td>
                              <td className="p-2 font-semibold text-foreground">{proc.name}</td>
                              <td className="p-2 text-muted-foreground">{proc.user_name || "—"}</td>
                              <td className="p-2 font-mono">{proc.cpu_percent ?? "—"}</td>
                              <td className="p-2 font-mono">{formatBytes(proc.memory_bytes)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Open Ports Tab */}
            {activeTab === "ports" && (
              <div className="space-y-3">
                {!selectedDevice.open_ports?.ports?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No open ports discovered on last sweep.
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-2">
                    {selectedDevice.open_ports.ports.map((port: number) => {
                      const isDangerous = DANGEROUS_PORTS.has(port);
                      return (
                        <div
                          key={port}
                          className={`rounded border p-2.5 flex flex-col justify-between h-[60px] ${
                            isDangerous
                              ? "border-destructive/30 bg-destructive/5 text-destructive"
                              : "border-border bg-muted/10 text-foreground"
                          }`}
                        >
                          <span className="text-xs font-mono font-extrabold">{port}</span>
                          <span className="text-[10px] truncate opacity-90">{PORT_LABELS[port] || "Service"}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Security Tab */}
            {activeTab === "security" && (
              <div className="space-y-4">
                {isSecurityLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading security posture...</p>
                ) : !security ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No security posture recorded. Run a Full Scan to collect Defender/firewall/SELinux status.
                  </div>
                ) : (
                  <InfoGrid
                    items={[
                      { label: "Antivirus Product", value: security.antivirus_product || "Not Detected" },
                      { label: "Antivirus Up To Date", value: security.antivirus_up_to_date === null ? "—" : security.antivirus_up_to_date ? "Yes" : "No" },
                      { label: "Firewall Enabled", value: security.firewall_enabled === null ? "—" : security.firewall_enabled ? "Enabled" : "Disabled" },
                      { label: "BitLocker Status", value: security.bitlocker_status || "Not Applicable" },
                      { label: "Secure Boot", value: security.secure_boot_enabled === null ? "—" : security.secure_boot_enabled ? "Enabled" : "Disabled" },
                      { label: "Pending Updates", value: security.pending_updates_count ?? "—" },
                      { label: "SELinux", value: security.selinux_status || "—" },
                      { label: "AppArmor", value: security.apparmor_status || "—" },
                      { label: "UFW Active", value: security.ufw_active === null ? "—" : security.ufw_active ? "Yes" : "No" },
                      { label: "SSH Root Login", value: security.ssh_root_login_enabled === null ? "—" : security.ssh_root_login_enabled ? "Enabled (risk)" : "Disabled" },
                      { label: "SSH Password Auth", value: security.ssh_password_auth_enabled === null ? "—" : security.ssh_password_auth_enabled ? "Enabled" : "Disabled" },
                      { label: "Last Update Installed", value: formatDateTime(security.last_update_installed_at) },
                    ]}
                  />
                )}
              </div>
            )}

            {/* Scan History Tab */}
            {activeTab === "scan_history" && (
              <Timeline
                loading={isHistoryLoading}
                events={(allHistoryDetails?.scan_history || []).map((hist) => ({
                  id: hist.id,
                  timestamp: hist.created_at,
                  badge: {
                    label: `Latency: ${hist.response_time !== null ? `${hist.response_time} ms` : "—"}`,
                    variant: "muted",
                  },
                  content: (
                    <div className="flex items-center gap-1.5">
                      <span>Status:</span>
                      <StatusBadge status={hist.status} />
                    </div>
                  ),
                }))}
                emptyMessage="No sweep scans history associated with this device."
              />
            )}

            {/* IP History Tab */}
            {activeTab === "ip_history" && (
              <Timeline
                loading={isHistoryLoading}
                events={(allHistoryDetails?.ip_history || []).map((hist) => ({
                  id: hist.id,
                  timestamp: hist.changed_at,
                  content: (
                    <p className="font-mono">
                      {hist.old_ip || "None"} &rarr; {hist.new_ip}
                    </p>
                  ),
                }))}
                emptyMessage="No IP address reassignment history found."
              />
            )}

            {/* Inventory History Tab */}
            {activeTab === "inventory_history" && (
              <Timeline
                loading={isHistoryLoading}
                events={(allHistoryDetails?.inventory_history || []).map((hist) => ({
                  id: hist.id,
                  timestamp: hist.created_at,
                  badge: {
                    label: hist.change_type,
                    variant: "muted",
                  },
                  content: (
                    <div>
                      <p className="text-foreground mt-0.5">{hist.description}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">Component: {hist.component}</p>
                    </div>
                  ),
                }))}
                emptyMessage="No configuration changes recorded in inventory logs."
              />
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}
