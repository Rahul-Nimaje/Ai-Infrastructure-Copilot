export const DEFAULT_WINRM_SSL_PORT = "5986";
export const DEFAULT_WINRM_HTTP_PORT = "5985";

export const WINRM_PORT_DEFAULTS = [DEFAULT_WINRM_HTTP_PORT, DEFAULT_WINRM_SSL_PORT] as const;

export const ACCOUNT_STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "invited", label: "Invited" },
  { value: "disabled", label: "Disabled" },
] as const;
