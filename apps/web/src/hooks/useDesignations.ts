import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useToastMutation } from "./useToastMutation";

interface FetchDesignationsParams {
  page?: number;
  size?: number;
  search?: string;
  departmentId?: string;
  status?: string;
}

export function useDesignations(params: FetchDesignationsParams = {}) {
  const query = useQuery({
    queryKey: ["designations", params],
    queryFn: async () => {
      const queryParams = new URLSearchParams();
      if (params.page) queryParams.append("page", params.page.toString());
      if (params.size) queryParams.append("size", params.size.toString());
      if (params.search) queryParams.append("search", params.search);
      if (params.departmentId) queryParams.append("departmentId", params.departmentId);
      if (params.status) queryParams.append("status", params.status);

      return apiFetch<{ items: any[]; total: number }>(`/api/v1/designations?${queryParams.toString()}`);
    },
  });

  const createDesignation = useToastMutation<any, any, any>({
    mutationFn: (payload: any) =>
      apiFetch("/api/v1/designations", { method: "POST", body: payload }),
    invalidateKeys: [["designations"]],
    successTitle: "Designation Created",
    successDescription: (data) => `Successfully created designation "${data?.name}"`,
    errorTitle: "Error Creating Designation",
  });

  const updateDesignation = useToastMutation<any, any, { id: string; payload: any }>({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      apiFetch(`/api/v1/designations/${id}`, { method: "PUT", body: payload }),
    invalidateKeys: [["designations"]],
    successTitle: "Designation Updated",
    successDescription: (data) => `Successfully updated designation "${data?.name}"`,
    errorTitle: "Error Updating Designation",
  });

  const deleteDesignation = useToastMutation<any, any, string>({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/designations/${id}`, { method: "DELETE" }),
    invalidateKeys: [["designations"]],
    successTitle: "Designation Deleted",
    successDescription: "Successfully deleted designation.",
    errorTitle: "Error Deleting Designation",
  });

  return {
    ...query,
    createDesignation,
    updateDesignation,
    deleteDesignation,
  };
}
