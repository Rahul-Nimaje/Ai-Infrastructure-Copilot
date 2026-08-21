"use client";

import { useState } from "react";
import type { Device } from "@ai-infra-copilot/shared-types";
import {
  Network,
  Play,
  Square,
  RefreshCw,
  Clock,
  Radio,
  History,
  ShieldAlert,
  Database,
  ChevronRight,
  Shield,
  Lock,
  Server,
  Printer,
  Monitor
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  StatusBadge
} from "@/components/common";

import {
  DEVICE_DETAIL_TABS,
  DEVICE_TYPE_OPTIONS,
  VENDOR_OPTIONS,
  LATENCY_OPTIONS,
  LAST_SEEN_OPTIONS,
  SCAN_TYPE_OPTIONS,
  PORT_LABELS,
  DANGEROUS_PORTS,
  DEFAULT_TARGET_RANGE,
  DEFAULT_SCAN_TYPE
} from "@/utils/constants";

import { getDeviceIconColor } from "@/utils/mappers";
import { formatBytes, bytesToGB, mhzToGhz, formatDateTime } from "@/utils/formatters";

import {
  useGetDiscoveryDevicesQuery,
  useGetDiscoveryScansQuery,
  useGetDeviceHardwareQuery,
  useGetDeviceSoftwareQuery,
  useGetDeviceHistoryQuery,
  useStartScanMutation,
  useStopScanMutation,
  useCollectInventoryMutation,
  useCollectAllInventoryMutation,
} from "@/features/discovery/services/discovery-api";

export function DiscoveryDashboard() {
  const { toast } = useToast();

  // Search & Filter States
  const [search, setSearch] = useState("");
  const [deviceType, setDeviceType] = useState("");
  const [vendor, setVendor] = useState("");
  const [status, setStatus] = useState("");
  const [responseTime, setResponseTime] = useState("");
  const [lastSeen, setLastSeen] = useState("");
  const [sortBy, setSortBy] = useState("last_seen_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);

  // Scan Config State
  const [targetRange, setTargetRange] = useState(DEFAULT_TARGET_RANGE);
  const [scanType, setScanType] = useState(DEFAULT_SCAN_TYPE);

  // Selected device for side drawer detail view
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);

  // 1. Query Devices List (Paginated, Filtered)
  const { data: devicesData, isLoading: isDevicesLoading, refetch: refetchDevices } = useGetDiscoveryDevicesQuery({
    page,
    size: pageSize,
    sort_by: sortBy,
    sort_order: sortOrder,
    search,
    device_type: deviceType,
    vendor,
    status,
    response_time: responseTime,
    last_seen: lastSeen,
  }, { pollingInterval: 5000 });

  // 2. Query Active/Past Scans
  const { data: scansList = [], isLoading: isScansLoading } = useGetDiscoveryScansQuery(undefined, {
    pollingInterval: 3000,
  });

  // Check if there is an active running scan right now
  const activeScan = scansList.find((s) => s.status === "running" || s.status === "pending");

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

  // Mutations
  const [startScan, { isLoading: isStartScanLoading }] = useStartScanMutation();
  const [stopScan, { isLoading: isStopScanLoading }] = useStopScanMutation();
  const [collectInventory, { isLoading: isCollectPending }] = useCollectInventoryMutation();
  const [collectAllInventory, { isLoading: isCollectAllPending }] = useCollectAllInventoryMutation();

  const handleStartScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (activeScan) return;
    try {
      await startScan({ target_range: targetRange, scan_type: scanType }).unwrap();
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

  // Stats derivation
  const totalDiscovered = devicesData?.total || 0;
  const onlineDevicesCount = devicesData?.items?.filter((d) => d.status.toLowerCase() === "online").length || 0;
  
  // Calculate average response time
  const onlineWithPing = devicesData?.items?.filter((d) => d.response_time !== null && d.response_time > 0) || [];
  const avgPing = onlineWithPing.length > 0
    ? (onlineWithPing.reduce((acc, curr) => acc + Number(curr.response_time || 0), 0) / onlineWithPing.length).toFixed(1)
    : "—";

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
            <div className="font-semibold text-foreground text-sm">{device.name}</div>
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
        description="Scan subnet ranges to automatically discover infrastructure assets, hardware models, and open ports."
      >
        <Button
          onClick={() => handleCollectAllInventory()}
          disabled={isCollectAllPending}
          className="gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-xs font-bold shadow-md text-white"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isCollectAllPending ? "animate-spin" : ""}`} />
          Collect All Inventory
        </Button>
      </PageHeader>

      {/* Discovery Dashboard Stats using StatCard */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard
          label="Total Discovered"
          value={totalDiscovered}
          description="Assets registered in database"
          icon={Database}
        />
        <StatCard
          label="Live Online"
          value={onlineDevicesCount}
          description="Active hosts reachable on last poll"
          icon={Radio}
          iconColor="text-emerald-600"
          iconBgColor="bg-emerald-500/10"
          gradient="from-card to-emerald-500/5"
          pulse
        />
        <StatCard
          label="Avg Latency"
          value={`${avgPing} ms`}
          description="Average ping response speed"
          icon={Clock}
          iconColor="text-amber-600"
          iconBgColor="bg-amber-500/10"
          gradient="from-card to-amber-500/5"
        />
        <Card className={`border-border/60 transition-colors ${activeScan ? "bg-primary/5 border-primary/30" : "bg-card"}`}>
          <CardContent className="p-6 flex items-center justify-between">
            <div className="space-y-1 flex-1">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Scan Status</span>
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold uppercase tracking-wide">
                  {activeScan ? activeScan.status : "Idle"}
                </span>
                {activeScan && (
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                  </span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground">
                {activeScan ? `Scanning range: ${activeScan.target_range}` : "No sweep currently running"}
              </p>
            </div>
            <div className={`rounded-xl p-3 ${activeScan ? "bg-primary/20 text-primary animate-spin duration-3000" : "bg-muted text-muted-foreground"}`}>
              <RefreshCw className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left column: Scan Controls & History */}
        <div className="lg:col-span-1 space-y-6">
          {/* Start Scan Control */}
          <Card className="border-border/60 shadow-md">
            <CardHeader>
              <CardTitle>Discovery Control Center</CardTitle>
              <CardDescription>Initiate a new subnet sweep to populate inventory.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleStartScan} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="targetRange">Subnet Target (CIDR range) *</Label>
                  <Input
                    id="targetRange"
                    required
                    placeholder="10.20.4.0/24"
                    value={targetRange}
                    onChange={(e) => setTargetRange(e.target.value)}
                    disabled={!!activeScan}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="scanType">Discovery Profile</Label>
                  <select
                    id="scanType"
                    value={scanType}
                    onChange={(e) => setScanType(e.target.value)}
                    disabled={!!activeScan}
                    className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {SCAN_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                {activeScan ? (
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={handleStopScan}
                    disabled={isStopScanLoading}
                    className="w-full gap-2 font-bold shadow"
                  >
                    <Square className="h-4 w-4 fill-white" />
                    Terminate Current Scan
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    disabled={isStartScanLoading}
                    className="w-full gap-2 font-bold bg-gradient-to-r from-primary to-indigo-600 shadow-md text-white"
                  >
                    <Play className="h-4 w-4 fill-white" />
                    Launch Scan Sweep
                  </Button>
                )}
              </form>
            </CardContent>
          </Card>

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
                      <span>Type: <span className="capitalize">{scan.scan_type.replace("_", " ")}</span></span>
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
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4 text-xs">
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
              setSelectedDevice(device);
              setActiveTab("overview");
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
            {/* Overview Tab */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {(selectedDevice as any).auth_success !== undefined && (selectedDevice as any).auth_success !== null && (
                  <div className={`p-4 rounded-lg border flex items-start gap-3 ${
                    (selectedDevice as any).auth_success 
                       ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400"
                      : "border-destructive/20 bg-destructive/5 text-destructive"
                  }`}>
                    {(selectedDevice as any).auth_success ? (
                      <Shield className="h-5 w-5 shrink-0 mt-0.5 text-emerald-500" />
                    ) : (
                      <ShieldAlert className="h-5 w-5 shrink-0 mt-0.5 text-destructive" />
                    )}
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider">
                        {(selectedDevice as any).auth_success ? "Credentials Authenticated" : "Authentication Failure"}
                      </h4>
                      <p className="text-xs mt-1 opacity-90">
                        {(selectedDevice as any).auth_success 
                          ? "Secure protocol connection established successfully during last sweep."
                          : (selectedDevice as any).auth_error || "SSH/WinRM/SNMP credentials failed or were not found."
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
                    { label: "Response Time", value: selectedDevice.response_time !== null ? `${selectedDevice.response_time} ms` : "—", mono: true },
                    { label: "Device Type", value: selectedDevice.device_type.replace("_", " ") },
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
                    No hardware inventory records exist. Collect telemetry on the Overview tab first.
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

            {/* Operating System Tab */}
            {activeTab === "os" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading OS details...</p>
                ) : !hardwareDetails?.inventory ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No operating system records exist. Collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <InfoGrid
                    items={[
                      { label: "OS Name & Edition", value: `${hardwareDetails.inventory.os_name} (${hardwareDetails.inventory.os_edition || "Standard"})`, colSpan: 2 },
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

            {/* CPU Tab */}
            {activeTab === "cpu" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading processor profile...</p>
                ) : !hardwareDetails?.processors?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No processor records exist. Collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.processors.map((proc: any) => (
                      <div key={proc.id} className="rounded-lg border border-border p-4 bg-muted/5 space-y-3">
                        <div className="flex justify-between items-start">
                          <div>
                            <span className="text-[10px] font-bold text-muted-foreground uppercase">Processor Model</span>
                            <h4 className="text-sm font-bold text-foreground mt-0.5">{proc.processor_name}</h4>
                          </div>
                          <StatusBadge status="active" />
                        </div>
                        <InfoGrid
                          columns={3}
                          items={[
                            { label: "Physical Cores", value: proc.cores },
                            { label: "Logical Threads", value: proc.logical_processors },
                            { label: "Current Speed", value: mhzToGhz(proc.current_speed_mhz) },
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
                    No memory records exist. Collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.memory.map((mem: any) => (
                      <div key={mem.id} className="space-y-4">
                        <InfoGrid
                          columns={3}
                          items={[
                            { label: "Total RAM", value: bytesToGB(mem.total_ram_bytes) },
                            { label: "Available RAM", value: bytesToGB(mem.available_ram_bytes, 1) },
                            { label: "DIMM Slots", value: mem.memory_slots },
                          ]}
                        />

                        {mem.ram_modules && mem.ram_modules.length > 0 && (
                          <div>
                            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-2 text-[10px]">Installed Modules</span>
                            <div className="mt-2 rounded-lg border border-border overflow-hidden text-xs">
                              <table className="w-full text-left">
                                <thead>
                                  <tr className="bg-muted/40 border-b border-border font-bold">
                                    <th className="p-2">Slot</th>
                                    <th className="p-2">Capacity</th>
                                    <th className="p-2">Frequency/Type</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border/60">
                                  {mem.ram_modules.map((mod: any, idx: number) => (
                                    <tr key={idx} className="hover:bg-muted/10">
                                      <td className="p-2 font-mono">{mod.slot}</td>
                                      <td className="p-2">{mod.size}</td>
                                      <td className="p-2">{mod.type || "DDR4"}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
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
                    No storage records exist. Collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.storage.map((disk: any) => {
                      const pctUsed = disk.capacity_bytes
                        ? (((disk.capacity_bytes - disk.free_space_bytes) / disk.capacity_bytes) * 100).toFixed(0)
                        : 0;

                      return (
                        <div key={disk.id} className="rounded-lg border border-border p-4 bg-muted/5 space-y-3">
                          <div className="flex justify-between items-start">
                            <div>
                              <span className="text-[10px] font-bold text-muted-foreground uppercase">Disk Unit Model</span>
                              <h4 className="text-sm font-bold text-foreground mt-0.5">{disk.disk_model || "Generic Disk"}</h4>
                            </div>
                            <span className="text-[10px] font-mono text-muted-foreground">S/N: {disk.serial_number || "—"}</span>
                          </div>

                          <div className="space-y-1">
                            <div className="flex justify-between text-xs text-muted-foreground">
                              <span>Capacity: <span className="font-semibold text-foreground">{bytesToGB(disk.capacity_bytes)}</span></span>
                              <span>Free Space: <span className="font-semibold text-foreground">{bytesToGB(disk.free_space_bytes)} ({100 - Number(pctUsed)}%)</span></span>
                            </div>
                            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-1.5 rounded-full ${Number(pctUsed) > 90 ? "bg-destructive" : "bg-primary"}`}
                                style={{ width: `${pctUsed}%` }}
                              />
                            </div>
                          </div>

                          {disk.partitions && disk.partitions.length > 0 && (
                            <div className="pt-2 border-t border-border/40 text-[10px] space-y-1">
                              <span className="font-bold text-muted-foreground uppercase">Logical Volumes</span>
                              <div className="flex gap-2 flex-wrap">
                                {disk.partitions.map((part: any, idx: number) => (
                                  <StatusBadge key={idx} status={`${part.name} (${bytesToGB(part.size_bytes)})`} />
                                ))}
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

            {/* Network Interfaces Tab */}
            {activeTab === "network" && (
              <div className="space-y-4">
                {isHardwareLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Loading interface metrics...</p>
                ) : !hardwareDetails?.interfaces?.length ? (
                  <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
                    No network interface profile exists. Collect telemetry on the Overview tab first.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {hardwareDetails.interfaces.map((net: any) => (
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
                    No software directory exists. Collect telemetry on the Overview tab first.
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
                          {softwareDetails.installed_software.map((sw: any) => (
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
                    No services directory exists. Collect telemetry on the Overview tab first.
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
                          {softwareDetails.services.map((srv: any) => (
                            <tr key={srv.id} className="hover:bg-muted/10">
                              <td className="p-2">
                                <div className="font-semibold text-foreground">{srv.display_name || srv.name}</div>
                                <div className="text-[10px] text-muted-foreground font-mono">{srv.name}</div>
                              </td>
                              <td className="p-2">
                                <StatusBadge status={srv.status} />
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

            {/* History Tab */}
            {activeTab === "history" && (
              <Timeline
                loading={isHistoryLoading}
                events={(allHistoryDetails?.scan_history || []).map((hist: any) => ({
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
                events={(allHistoryDetails?.ip_history || []).map((hist: any) => ({
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
                events={(allHistoryDetails?.inventory_history || []).map((hist: any) => ({
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
