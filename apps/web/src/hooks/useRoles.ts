import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useToastMutation } from "./useToastMutation";

export function useRoles(selectedRoleId?: string | null) {
  const rolesQuery = useQuery({
    queryKey: ["roles"],
    queryFn: () => apiFetch<any[]>("/api/v1/rbac/roles"),
    placeholderData: [],
  });

  const permissionsQuery = useQuery({
    queryKey: ["permissions"],
    queryFn: () => apiFetch<any[]>("/api/v1/rbac/permissions"),
    placeholderData: [],
  });

  const activeRolePermissionsQuery = useQuery({
    queryKey: ["role-permissions", selectedRoleId],
    queryFn: () => {
      if (!selectedRoleId) return [];
      return apiFetch<any[]>(`/api/v1/rbac/roles/${selectedRoleId}/permissions`);
    },
    enabled: !!selectedRoleId,
    placeholderData: [],
  });

  const assignedUsersQuery = useQuery({
    queryKey: ["role-users", selectedRoleId],
    queryFn: () => {
      if (!selectedRoleId) return [];
      return apiFetch<any[]>(`/api/v1/rbac/roles/${selectedRoleId}/users`);
    },
    enabled: !!selectedRoleId,
    placeholderData: [],
  });

  const createRole = useToastMutation<any, any, any>({
    mutationFn: (payload: any) =>
      apiFetch<any>("/api/v1/rbac/roles", { method: "POST", body: payload }),
    invalidateKeys: [["roles"]],
    successTitle: "Role Created",
    successDescription: "Successfully created custom enterprise role.",
    errorTitle: "Error Creating Role",
  });

  const updateRole = useToastMutation<any, any, { id: string; payload: any }>({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      apiFetch<any>(`/api/v1/rbac/roles/${id}`, { method: "PUT", body: payload }),
    invalidateKeys: [["roles"]],
    successTitle: "Role Updated",
    successDescription: "Successfully updated role details.",
    errorTitle: "Error Updating Role",
  });

  const deleteRole = useToastMutation<any, any, string>({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/rbac/roles/${id}`, { method: "DELETE" }),
    invalidateKeys: [["roles"]],
    successTitle: "Role Deleted",
    successDescription: "Successfully deleted role.",
    errorTitle: "Error Deleting Role",
  });

  const savePermissions = useToastMutation<any, any, { id: string; permissionIds: string[] }>({
    mutationFn: ({ id, permissionIds }: { id: string; permissionIds: string[] }) =>
      apiFetch(`/api/v1/rbac/roles/${id}/permissions`, {
        method: "PUT",
        body: { permission_ids: permissionIds },
      }),
    invalidateKeys: [["role-permissions", selectedRoleId]],
    successTitle: "Permissions Saved",
    successDescription: "Successfully updated authorization matrix.",
    errorTitle: "Error Saving Permissions",
  });

  const assignUserRole = useToastMutation<any, any, { userId: string; roleId: string }>({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      apiFetch(`/api/v1/rbac/users/${userId}/roles`, {
        method: "POST",
        body: { role_ids: [roleId] },
      }),
    invalidateKeys: [["role-users", selectedRoleId]],
    successTitle: "User Assigned",
    successDescription: "Successfully assigned role to user.",
    errorTitle: "Error Assigning User",
  });

  const unassignUserRole = useToastMutation<any, any, { userId: string; roleId: string }>({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      apiFetch(`/api/v1/rbac/users/${userId}/roles/${roleId}`, {
        method: "DELETE",
      }),
    invalidateKeys: [["role-users", selectedRoleId]],
    successTitle: "User Unassigned",
    successDescription: "Successfully removed role from user.",
    errorTitle: "Error Unassigning User",
  });

  return {
    roles: rolesQuery.data || [],
    isRolesLoading: rolesQuery.isLoading,
    permissions: permissionsQuery.data || [],
    activeRolePermissions: activeRolePermissionsQuery.data || [],
    assignedUsers: assignedUsersQuery.data || [],
    createRole,
    updateRole,
    deleteRole,
    savePermissions,
    assignUserRole,
    unassignUserRole,
  };
}
