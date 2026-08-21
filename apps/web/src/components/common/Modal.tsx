"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

const SIZE_CLASSES: Record<"sm" | "md" | "lg" | "xl", string> = {
  sm: "sm:max-w-md",
  md: "sm:max-w-lg",
  lg: "sm:max-w-2xl",
  xl: "sm:max-w-4xl",
};

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  size?: "sm" | "md" | "lg" | "xl";
  isLoading?: boolean;
  closeOnOverlayClick?: boolean;
  /**
   * Radix's modal focus-trap assumes all interactive content lives inside
   * DialogContent's own DOM subtree. Any content this modal renders in its
   * own portal (e.g. an AsyncSelect dropdown) sits outside that subtree, so
   * Radix keeps yanking focus back — clicks land, but the search input never
   * actually receives focus. Pass `modal={false}` for any modal that hosts
   * an AsyncSelect (or similar portaled popover) to disable that trap.
   */
  modal?: boolean;
  footer?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  size = "md",
  isLoading = false,
  closeOnOverlayClick = true,
  modal = true,
  footer,
  className,
  children,
}: ModalProps) {
  const preventClose = isLoading || !closeOnOverlayClick;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} modal={modal}>
      <DialogContent
        className={cn(SIZE_CLASSES[size], className)}
        onPointerDownOutside={(e) => {
          if (preventClose) e.preventDefault();
        }}
        onEscapeKeyDown={(e) => {
          if (isLoading) e.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <div className="max-h-[65vh] overflow-y-auto">{children}</div>

        {footer && <DialogFooter>{footer}</DialogFooter>}
      </DialogContent>
    </Dialog>
  );
}
