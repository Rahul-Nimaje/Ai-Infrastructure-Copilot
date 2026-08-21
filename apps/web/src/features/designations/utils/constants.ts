export const DESIGNATION_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
] as const;

export const DESIGNATION_TABLE_COLUMNS = [
  { key: "name", label: "Designation Name", sortable: true },
  { key: "department_name", label: "Department", sortable: true },
  { key: "description", label: "Description", sortable: false },
  { key: "status", label: "Status", sortable: true },
  { key: "created_at", label: "Created Date", sortable: true },
] as const;
