"use client";

import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X, AlertTriangle, AlertCircle, Info } from "lucide-react";
import { Button } from "./button";
import { Input } from "./input";
import { Label } from "./label";

interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "info" | "warning" | "destructive";
  requireTypeConfirmation?: boolean;
  typeConfirmationWord?: string;
  isLoading?: boolean;
  closeOnClickOutside?: boolean;
}

export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "info",
  requireTypeConfirmation = false,
  typeConfirmationWord = "CONFIRM",
  isLoading = false,
  closeOnClickOutside = true,
}: ConfirmationDialogProps) {
  const [mounted, setMounted] = useState(false);
  const [confirmInput, setConfirmInput] = useState("");
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Handle focus trapping and Esc key
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      
      // Prevent scrolling of background page
      document.body.style.overflow = "hidden";

      // Focus management
      const timer = setTimeout(() => {
        if (requireTypeConfirmation && inputRef.current) {
          inputRef.current.focus();
        } else if (dialogRef.current) {
          // Focus the dialog container or first button
          const focusable = dialogRef.current.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          if (focusable.length > 1) {
            // Focus cancel button (index 1 usually) for destructive, or confirm button for info
            const focusTarget = variant === "destructive" ? (focusable[1] as HTMLElement) : (focusable[2] as HTMLElement);
            focusTarget?.focus();
          } else {
            dialogRef.current.focus();
          }
        }
      }, 50);

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          onClose();
        }

        // Focus trap
        if (e.key === "Tab" && dialogRef.current) {
          const focusableElements = dialogRef.current.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          const firstElement = focusableElements[0] as HTMLElement;
          const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

          if (e.shiftKey) {
            if (document.activeElement === firstElement) {
              lastElement.focus();
              e.preventDefault();
            }
          } else {
            if (document.activeElement === lastElement) {
              firstElement.focus();
              e.preventDefault();
            }
          }
        }
      };

      window.addEventListener("keydown", handleKeyDown);
      return () => {
        document.body.style.overflow = "unset";
        window.removeEventListener("keydown", handleKeyDown);
        previousFocusRef.current?.focus();
      };
    }
  }, [isOpen, requireTypeConfirmation, variant, onClose]);

  // Reset input when dialog closes/opens
  useEffect(() => {
    if (!isOpen) {
      setConfirmInput("");
    }
  }, [isOpen]);

  if (!mounted || !isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (closeOnClickOutside && e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleConfirm = async () => {
    if (requireTypeConfirmation && confirmInput !== typeConfirmationWord) {
      return;
    }
    await onConfirm();
    onClose();
  };

  // Variant styling
  const variantIcons = {
    info: <Info className="h-6 w-6 text-blue-500" />,
    warning: <AlertTriangle className="h-6 w-6 text-amber-500" />,
    destructive: <AlertCircle className="h-6 w-6 text-red-500" />,
  };

  const variantColors = {
    info: "border-blue-500/20 bg-blue-500/5",
    warning: "border-amber-500/20 bg-amber-500/5",
    destructive: "border-red-500/20 bg-red-500/5",
  };

  const confirmButtonVariant = {
    info: "default" as const,
    warning: "default" as const, // could style with warning color
    destructive: "destructive" as const,
  };

  const isConfirmDisabled =
    isLoading || (requireTypeConfirmation && confirmInput !== typeConfirmationWord);

  return createPortal(
    <div
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby="dialog-description"
        tabIndex={-1}
        className="relative w-full max-w-md overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow-2xl animate-in zoom-in-95 duration-200"
      >
        {/* Header decoration based on variant */}
        <div className={`flex items-center gap-3 border-b border-border p-4 ${variantColors[variant]}`}>
          {variantIcons[variant]}
          <h2 id="dialog-title" className="text-lg font-semibold tracking-tight">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <p id="dialog-description" className="text-sm text-muted-foreground leading-relaxed">
            {description}
          </p>

          {requireTypeConfirmation && (
            <div className="space-y-2 rounded-lg border border-border bg-muted/40 p-4">
              <Label htmlFor="confirmation-input" className="text-xs font-semibold text-foreground">
                To confirm, type <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-destructive border border-border">{typeConfirmationWord}</span> below:
              </Label>
              <Input
                ref={inputRef}
                id="confirmation-input"
                type="text"
                autoComplete="off"
                placeholder={typeConfirmationWord}
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
                className="mt-1"
                disabled={isLoading}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t border-border bg-muted/30 p-4">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            {cancelText}
          </Button>
          <Button
            variant={confirmButtonVariant[variant]}
            onClick={handleConfirm}
            disabled={isConfirmDisabled}
            className={variant === "warning" ? "bg-amber-600 hover:bg-amber-700 text-white" : ""}
          >
            {isLoading ? "Processing..." : confirmText}
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
}
