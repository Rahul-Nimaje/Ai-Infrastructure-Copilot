export type ScanPort = {
  port: number;
  service: string;
};

export type ScanCandidate = {
  ip_address: string;
  hostname_guess: string;
  likely_os_type: string;
  open_ports: ScanPort[];
};
