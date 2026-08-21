import { apiSlice } from "@/store/api-slice";
import type { Device, DeviceScan } from "@ai-infra-copilot/shared-types";

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
    getDeviceHardware: builder.query<any, string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/hardware`,
    }),
    getDeviceSoftware: builder.query<any, string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/software`,
    }),
    getDeviceHistory: builder.query<any, string>({
      query: (deviceId) => `/api/v1/devices/${deviceId}/history`,
    }),
    startScan: builder.mutation<DeviceScan, { target_range: string; scan_type: string }>({
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
    collectInventory: builder.mutation<any, string>({
      query: (deviceId) => ({
        url: `/api/v1/inventory/collect/${deviceId}`,
        method: "POST",
      }),
      invalidatesTags: ["Devices"],
    }),
    collectAllInventory: builder.mutation<any, void>({
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
  useStartScanMutation,
  useStopScanMutation,
  useCollectInventoryMutation,
  useCollectAllInventoryMutation,
} = discoveryApi;
