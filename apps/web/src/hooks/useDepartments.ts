import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useToastMutation } from "./useToastMutation";

interface FetchDepartmentsParams {
  page?: number;
  size?: number;
  search?: string;
  status?: string;
}

export function useDepartments(params: FetchDepartmentsParams = {}) {
  const query = useQuery({
    queryKey: ["departments", params],
    queryFn: async () => {
      const queryParams = new URLSearchParams();
      if (params.page) queryParams.append("page", params.page.toString());
      if (params.size) queryParams.append("size", params.size.toString());
      if (params.search) queryParams.append("search", params.search);
      if (params.status) queryParams.append("status", params.status);

      return apiFetch<{ items: any[]; total: number }>(`/api/v1/departments?${queryParams.toString()}`);
    },
  });

  const createDepartment = useToastMutation<any, any, any>({
    mutationFn: (payload: any) =>
      apiFetch("/api/v1/departments", { method: "POST", body: payload }),
    invalidateKeys: [["departments"]],
    successTitle: "Department Created",
    successDescription: (data) => `Successfully created department "${data?.name}"`,
    errorTitle: "Error Creating Department",
  });

  const updateDepartment = useToastMutation<any, any, { id: string; payload: any }>({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      apiFetch(`/api/v1/departments/${id}`, { method: "PUT", body: payload }),
    invalidateKeys: [["departments"]],
    successTitle: "Department Updated",
    successDescription: (data) => `Successfully updated department "${data?.name}"`,
    errorTitle: "Error Updating Department",
  });

  const deleteDepartment = useToastMutation<any, any, string>({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/departments/${id}`, { method: "DELETE" }),
    invalidateKeys: [["departments"]],
    successTitle: "Department Deleted",
    successDescription: "Successfully deleted department.",
    errorTitle: "Error Deleting Department",
  });

  return {
    ...query,
    createDepartment,
    updateDepartment,
    deleteDepartment,
  };
}
