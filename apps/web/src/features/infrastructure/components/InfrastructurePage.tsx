"use client";

import { useInfrastructureCategories } from "@/features/infrastructure/hooks/useInfrastructureCategories";
import { CategoryCard } from "@/features/infrastructure/components/CategoryCard";

export function InfrastructurePage() {
  const { categories, isLoading } = useInfrastructureCategories();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold">Infrastructure</h1>
        <p className="text-sm text-muted-foreground">All monitored infrastructure categories at a glance</p>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
          {categories.map((category) => (
            <CategoryCard key={category.key} category={category} />
          ))}
        </div>
      )}
    </div>
  );
}
