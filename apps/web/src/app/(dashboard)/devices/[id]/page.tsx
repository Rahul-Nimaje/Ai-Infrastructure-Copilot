import { use } from "react";
import { DeviceDetailPage } from "@/features/discovery/components/DeviceDetailPage";

interface PageProps {
  params: Promise<{
    id: string;
  }>;
}

export default function Page({ params }: PageProps) {
  const resolvedParams = use(params);
  return <DeviceDetailPage deviceId={resolvedParams.id} />;
}
