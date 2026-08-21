export const DEPARTMENT_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
] as const;

export const DEPARTMENT_TABLE_COLUMNS = [
  { key: "name", label: "Department Name", sortable: true },
  { key: "description", label: "Description", sortable: false },
  { key: "status", label: "Status", sortable: true },
  { key: "created_at", label: "Created Date", sortable: true },
] as const;
