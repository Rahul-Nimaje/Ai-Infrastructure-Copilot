import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium", {
  variants: {
    variant: {
      default: "bg-primary text-primary-foreground",
      muted: "bg-muted text-muted-foreground",
      success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
      warning: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
      destructive: "bg-destructive text-destructive-foreground",
      info: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
