import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { User } from "@ai-infra-copilot/shared-types";
import { useToastMutation } from "./useToastMutation";

interface FetchUsersParams {
  page: number;
  size: number;
  search?: string;
  status?: string;
  departmentId?: string;
  role?: string;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

export function useUsers(params: FetchUsersParams) {
  const query = useQuery({
    queryKey: ["users", params],
    queryFn: async () => {
      const queryParams = new URLSearchParams({
        page: params.page.toString(),
        size: params.size.toString(),
        sort_by: params.sortBy || "created_at",
        sort_order: params.sortOrder || "desc",
      });
      if (params.search) queryParams.append("search", params.search);
      if (params.status) queryParams.append("status", params.status);
      if (params.departmentId) queryParams.append("department", params.departmentId);
      if (params.role) queryParams.append("role", params.role);

      return apiFetch<{ items: User[]; total: number; page: number; size: number }>(
        `/api/v1/users?${queryParams.toString()}`
      );
    },
  });

  const createUser = useToastMutation<User, any, any>({
    mutationFn: (payload: any) =>
      apiFetch<User>("/api/v1/users", {
        method: "POST",
        body: payload,
      }),
    invalidateKeys: [["users"]],
    successTitle: "User Created",
    successDescription: (data) => `Successfully registered new user "${data.full_name}"`,
    errorTitle: "Error Creating User",
  });

  const updateUser = useToastMutation<User, any, { id: string; payload: any }>({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      apiFetch<User>(`/api/v1/users/${id}`, {
        method: "PUT",
        body: payload,
      }),
    invalidateKeys: [["users"]],
    successTitle: "User Updated",
    successDescription: (data) => `Successfully updated profile of "${data.full_name}"`,
    errorTitle: "Error Updating User",
  });

  const deleteUser = useToastMutation<any, any, string>({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/users/${id}`, {
        method: "DELETE",
      }),
    invalidateKeys: [["users"]],
    successTitle: "User Deleted",
    successDescription: "Successfully soft-deleted user account.",
    errorTitle: "Error Deleting User",
  });

  const bulkAction = useToastMutation<any, any, { ids: string[]; action: string }>({
    mutationFn: (payload: { ids: string[]; action: string }) =>
      apiFetch("/api/v1/users/bulk", {
        method: "POST",
        body: payload,
      }),
    invalidateKeys: [["users"]],
    successTitle: "Bulk Action Completed",
    successDescription: (_, variables) => `Successfully performed bulk action: ${variables.action}`,
    errorTitle: "Bulk Action Failed",
  });

  const importCsv = useToastMutation<any, any, File>({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const token = localStorage.getItem("auth_token") || "";
      const res = await fetch("/api/v1/users/import", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message || "CSV Import failed");
      }
      return res.json();
    },
    invalidateKeys: [["users"]],
    successTitle: "Import Completed",
    successDescription: (res) =>
      `Successfully imported ${res.success_count || 0} users. Errors: ${res.errors?.length || 0}`,
    errorTitle: "Import Error",
    errorDescription: (err) => err.message || "Failed to process CSV file.",
  });

  return {
    ...query,
    createUser,
    updateUser,
    deleteUser,
    bulkAction,
    importCsv,
  };
}
