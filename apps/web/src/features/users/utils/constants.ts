export const DEPARTMENT_OPTIONS = [
  { value: "", label: "All Departments" },
  { value: "IT Infrastructure", label: "IT Infrastructure" },
  { value: "Security Operations", label: "Security Operations" },
  { value: "Software Development", label: "Software Development" },
  { value: "Support & Helpdesk", label: "Support & Helpdesk" },
  { value: "Human Resources", label: "Human Resources" },
  { value: "Management", label: "Management" },
] as const;

export const USER_STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "invited", label: "Invited" },
  { value: "disabled", label: "Disabled" },
] as const;
