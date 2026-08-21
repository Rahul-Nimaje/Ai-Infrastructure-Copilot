import { CircleAlert } from "lucide-react";
import { EmptyState } from "@/components/common";
import { navLabelFor } from "@/components/layout/nav-config";

function fallbackLabel(slug: string): string {
  return slug
    .split("-")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

export default async function ModulePlaceholderPage({ params }: { params: Promise<{ module: string }> }) {
  const { module } = await params;
  const title = navLabelFor(`/${module}`) ?? fallbackLabel(module);
  return <EmptyState icon={CircleAlert} title={title} description="This module isn't wired up yet." />;
}
