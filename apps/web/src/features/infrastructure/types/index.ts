export interface RealCategory {
  kind: "real";
  key: string;
  name: string;
  count: number;
  cpu: number;
  mem: number;
  disk: number;
  healthy: number;
  warning: number;
  critical: number;
  href: string;
}

export interface PlaceholderCategory {
  kind: "placeholder";
  key: string;
  name: string;
}

export type InfrastructureCategory = RealCategory | PlaceholderCategory;
