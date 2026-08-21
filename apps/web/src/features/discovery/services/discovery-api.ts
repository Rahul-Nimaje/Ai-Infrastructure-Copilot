import { apiSlice } from "@/store/api-slice";
import type {
  Device,
  DeviceScan,
  DeviceHardwareProfile,
  DeviceSoftwareProfile,
  DeviceHistoryBundle,
  DeviceProcess,
  DeviceSecurityPosture,
  DevicePortInfo,
} from "@ai-infra-copilot/shared-types";

export const discoveryApi = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getDiscoveryDevices: builder.query<
      { items: Device[]; total: number; page: number; size: number },
      Record<string, string | number>
    >({
      query: (params) => {
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, val]) => {
          if (val !== undefined && val !== null && val !== "") {
            queryParams.append(key, val.toString());
          }
        });
        return `/api/v1/discovery/devices?${queryParams.toString()}`;
      },
      providesTags: ["Devices"],
    }),
    getDiscoveryScans: builder.query<DeviceScan[], void>({
      query: () => "/api/v1/discovery/scan",
      providesTags: ["Scans"],
    }),
    getDeviceHardware: builder.query<DeviceHardwareProfile, string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/hardware`,
      providesTags: (_r, _e, deviceId) => [{ type: "Devices", id: deviceId }],
    }),
    getDeviceSoftware: builder.query<DeviceSoftwareProfile, string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/software`,
      providesTags: (_r, _e, deviceId) => [{ type: "Devices", id: deviceId }],
    }),
    getDeviceHistory: builder.query<DeviceHistoryBundle, string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/history`,
      providesTags: (_r, _e, deviceId) => [{ type: "Devices", id: deviceId }],
    }),
    // New for the full-inventory-scan feature — typed against the same
    // {data|list} shapes the backend's discovery/schemas.py returns.
    getDeviceProcesses: builder.query<DeviceProcess[], string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/processes`,
      providesTags: (_r, _e, deviceId) => [{ type: "Devices", id: deviceId }],
    }),
    getDeviceSecurity: builder.query<DeviceSecurityPosture | null, string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/security`,
      providesTags: (_r, _e, deviceId) => [{ type: "Devices", id: deviceId }],
    }),
    getDevicePorts: builder.query<DevicePortInfo[], string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/ports`,
      providesTags: (_r, _e, deviceId) => [{ type: "Devices", id: deviceId }],
    }),
    startScan: builder.mutation<DeviceScan, { target_range: string; scan_mode: "quick" | "standard" | "full" }>({
      query: (payload) => ({
        url: "/api/v1/discovery/scan",
        method: "POST",
        body: payload,
      }),
      invalidatesTags: ["Scans"],
    }),
    stopScan: builder.mutation<DeviceScan, string>({
      query: (scanId) => ({
        url: `/api/v1/discovery/scan/${scanId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Scans"],
    }),
    collectInventory: builder.mutation<{ status: string; device_id: string }, string>({
      query: (deviceId) => ({
        url: `/api/v1/inventory/collect/${deviceId}`,
        method: "POST",
      }),
      invalidatesTags: ["Devices"],
    }),
    collectAllInventory: builder.mutation<{ status: string; total_devices: number }, void>({
      query: () => ({
        url: "/api/v1/inventory/collect-all",
        method: "POST",
      }),
      invalidatesTags: ["Devices"],
    }),
  }),
});

export const {
  useGetDiscoveryDevicesQuery,
  useGetDiscoveryScansQuery,
  useGetDeviceHardwareQuery,
  useGetDeviceSoftwareQuery,
  useGetDeviceHistoryQuery,
  useGetDeviceProcessesQuery,
  useGetDeviceSecurityQuery,
  useGetDevicePortsQuery,
  useStartScanMutation,
  useStopScanMutation,
  useCollectInventoryMutation,
  useCollectAllInventoryMutation,
} = discoveryApi;
