// ─── Vendor filter options ────────────────────────────────────
export const VENDOR_OPTIONS = [
  { value: "", label: "All Vendors" },
  { value: "Cisco", label: "Cisco Systems" },
  { value: "Juniper", label: "Juniper Networks" },
  { value: "HP", label: "Hewlett Packard" },
  { value: "Dell", label: "Dell Systems" },
  { value: "Ubiquiti", label: "Ubiquiti" },
  { value: "Microsoft", label: "Microsoft" },
  { value: "Linux", label: "Linux Generic" },
] as const;

// ─── Latency / response time filter options ───────────────────
export const LATENCY_OPTIONS = [
  { value: "", label: "All Latencies" },
  { value: "under_10", label: "Fast (<10ms)" },
  { value: "10_to_50", label: "Medium (10–50ms)" },
  { value: "over_50", label: "Slow (>50ms)" },
] as const;

// ─── Last seen filter options ─────────────────────────────────
export const LAST_SEEN_OPTIONS = [
  { value: "", label: "Any Time" },
  { value: "last_hour", label: "Within 1 Hour" },
  { value: "last_24h", label: "Within 24 Hours" },
  { value: "last_week", label: "Within 7 Days" },
] as const;
