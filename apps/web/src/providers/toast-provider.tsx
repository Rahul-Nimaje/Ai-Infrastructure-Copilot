"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastVariant = "success" | "destructive" | "info";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastContextType {
  toast: (options: Omit<Toast, "id">) => void;
  toasts: Toast[];
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    ({ title, description, variant = "info", duration = 4000 }: Omit<Toast, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, title, description, variant, duration }]);

      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ toast, toasts, dismiss }}>
      {children}
      {/* Toast Container */}
      <div className="fixed bottom-4 right-4 z-[9999] flex w-full max-w-md flex-col gap-2 p-4 md:bottom-6 md:right-6">
        {toasts.map((t) => {
          const Icon =
            t.variant === "success"
              ? CheckCircle2
              : t.variant === "destructive"
              ? AlertCircle
              : Info;

          return (
            <div
              key={t.id}
              className={cn(
                "group pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden rounded-lg border p-4 shadow-lg transition-all duration-300 animate-slide-in-right",
                // Glassmorphism and variant background
                t.variant === "success" && "border-emerald-500/30 bg-emerald-950/80 text-emerald-200 backdrop-blur-md",
                t.variant === "destructive" && "border-destructive/30 bg-destructive/90 text-destructive-foreground backdrop-blur-md",
                t.variant === "info" && "border-border/60 bg-background/95 text-foreground backdrop-blur-md"
              )}
            >
              <Icon className={cn("h-5 w-5 shrink-0 mt-0.5", 
                t.variant === "success" && "text-emerald-400",
                t.variant === "destructive" && "text-white",
                t.variant === "info" && "text-primary"
              )} />
              
              <div className="flex-1 space-y-1">
                <p className="text-sm font-semibold leading-none">{t.title}</p>
                {t.description && (
                  <p className={cn("text-xs leading-normal opacity-90",
                    t.variant === "destructive" ? "text-red-100" : "text-muted-foreground"
                  )}>
                    {t.description}
                  </p>
                )}
              </div>

              <button
                onClick={() => dismiss(t.id)}
                className={cn(
                  "rounded-md p-1 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100 focus:outline-none",
                  t.variant === "destructive" ? "hover:bg-red-800/55" : "hover:bg-muted"
                )}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
