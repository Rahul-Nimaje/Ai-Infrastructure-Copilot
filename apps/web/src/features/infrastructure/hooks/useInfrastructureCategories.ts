import { useGetServersQuery } from "@/features/infrastructure/services/infrastructure-api";
import { buildInfrastructureCategories } from "@/features/infrastructure/utils/infrastructure.utils";

export function useInfrastructureCategories() {
  const { data, isLoading } = useGetServersQuery();
  const servers = data?.data ?? [];

  return {
    categories: buildInfrastructureCategories(servers),
    isLoading,
  };
}
