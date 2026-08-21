import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast, type ToastVariant } from "@/providers/toast-provider";

interface UseToastMutationOptions<TData, TError, TVariables, TContext> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  invalidateKeys?: any[][];
  successTitle?: string;
  successDescription?: string | ((data: TData, variables: TVariables) => string);
  successVariant?: ToastVariant;
  errorTitle?: string;
  errorDescription?: string | ((error: any, variables: TVariables) => string);
  onSuccess?: (data: TData, variables: TVariables, context: TContext) => void;
  onError?: (error: TError, variables: TVariables, context: TContext | undefined) => void;
}

export function useToastMutation<TData = any, TError = any, TVariables = any, TContext = any>({
  mutationFn,
  invalidateKeys,
  successTitle = "Success",
  successDescription,
  successVariant = "success",
  errorTitle = "Error",
  errorDescription,
  onSuccess,
  onError,
}: UseToastMutationOptions<TData, TError, TVariables, TContext>) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<TData, TError, TVariables, TContext>({
    mutationFn,
    onSuccess: (data, variables, context) => {
      if (invalidateKeys) {
        invalidateKeys.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key });
        });
      }

      const desc = typeof successDescription === "function"
        ? successDescription(data, variables)
        : successDescription;

      // Allow overriding variant dynamically (e.g. for import CSV status checking)
      let finalVariant = successVariant;
      if (data && typeof data === "object" && "errors" in data && Array.isArray(data.errors) && data.errors.length > 0) {
        finalVariant = "info";
      }

      if (successTitle || desc) {
        toast({
          title: successTitle,
          description: desc,
          variant: finalVariant,
        });
      }

      onSuccess?.(data, variables, context);
    },
    onError: (error: TError, variables, context) => {
      const desc = typeof errorDescription === "function"
        ? errorDescription(error, variables)
        : errorDescription || (error as any)?.message || "An unexpected error occurred.";

      toast({
        title: errorTitle,
        description: desc,
        variant: "destructive",
      });

      onError?.(error, variables, context);
    },
  });
}
