// ─── Department filter options (for user management) ──────────
export const DEPARTMENT_OPTIONS = [
  { value: "", label: "All Departments" },
  { value: "IT Infrastructure", label: "IT Infrastructure" },
  { value: "Security Operations", label: "Security Operations" },
  { value: "Software Development", label: "Software Development" },
  { value: "Support & Helpdesk", label: "Support & Helpdesk" },
  { value: "Human Resources", label: "Human Resources" },
  { value: "Management", label: "Management" },
] as const;

// ─── User table columns ──────────────────────────────────────
export const USER_TABLE_COLUMNS = [
  { key: "full_name", label: "Full Name", sortable: true },
  { key: "username", label: "Username", sortable: true },
  { key: "email", label: "Email", sortable: false },
  { key: "employee_id", label: "Employee ID", sortable: false },
  { key: "department", label: "Department & Role", sortable: false },
  { key: "roles", label: "Roles Granted", sortable: false },
  { key: "status", label: "Status", sortable: true },
] as const;
