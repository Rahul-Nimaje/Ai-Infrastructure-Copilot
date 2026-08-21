"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Role, Permission, User } from "@ai-infra-copilot/shared-types";
import {
  Plus,
  Shield,
  Lock,
  Trash2,
  Users,
  Check,
  UserPlus,
  UserMinus,
  Settings,
  Grid,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";

import {
  PageHeader,
  SearchInput,
  TextField,
  FormActions,
  Modal,
} from "@/components/common";

import { useRoles, useUsers } from "@/hooks";
import { roleSchema, type RoleFormValues } from "@/schemas";
import type { DirtyPermissionsMap, RoleTab } from "../types";
import { ACTIONS, MODULES } from "../utils/constants";


export function RolesManager() {
  // Active States
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<RoleTab>("matrix");

  // Modals & Forms States
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignUserSearch, setAssignUserSearch] = useState("");

  // Unsaved matrix changes: maps permission code -> boolean (granted/revoked)
  const [dirtyPermissions, setDirtyPermissions] = useState<DirtyPermissionsMap>({});

  // Confirmation Dialog States
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    confirmText: string;
    variant: "info" | "warning" | "destructive";
    requireTypeConfirmation: boolean;
    typeConfirmationWord: string;
    actionType: "delete" | "save_matrix" | "assign" | "unassign";
    targetId?: string;
    extraData?: any;
  }>({
    isOpen: false,
    title: "",
    description: "",
    confirmText: "Confirm",
    variant: "info",
    requireTypeConfirmation: false,
    typeConfirmationWord: "",
    actionType: "delete",
  });

  // 1. Roles Query & Mutation hook
  const {
    roles,
    isRolesLoading,
    permissions,
    activeRolePermissions,
    assignedUsers,
    createRole,
    updateRole,
    deleteRole,
    savePermissions,
    assignUserRole,
    unassignUserRole,
  } = useRoles(selectedRoleId);

  // Set default selected role once loaded
  useEffect(() => {
    if (!selectedRoleId && roles.length > 0) {
      setSelectedRoleId(roles[0].id);
    }
  }, [roles, selectedRoleId]);

  const selectedRole = roles.find((r: Role) => r.id === selectedRoleId) || null;

  // React Hook Form for Create
  const createForm = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: { name: "", description: "" },
  });

  // React Hook Form for Update (Settings)
  const updateForm = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: { name: "", description: "" },
  });

  // Synchronize update form values with selected role
  useEffect(() => {
    if (selectedRole) {
      updateForm.reset({
        name: selectedRole.name,
        description: selectedRole.description || "",
      });
    }
  }, [selectedRole, updateForm]);

  // Query All users (for role assignment dialog) using our useUsers hook
  const { data: allUsers } = useUsers({
    page: 1,
    size: 50,
    search: assignUserSearch,
  });

  // Permission calculation helpers
  const getPermissionCode = (moduleKey: string, actionKey: string): string => {
    if (moduleKey === "dashboard") return "dashboard.read";
    if (moduleKey === "settings") return "settings.manage";
    return `${moduleKey}.${actionKey}`;
  };

  const isPermissionGranted = (code: string): boolean => {
    if (dirtyPermissions[code] !== undefined) {
      return dirtyPermissions[code];
    }
    return activeRolePermissions.some((p: Permission) => p.code === code);
  };

  const handleCheckboxChange = (code: string, checked: boolean) => {
    if (selectedRole?.is_system_role) return;
    setDirtyPermissions((prev) => ({
      ...prev,
      [code]: checked,
    }));
  };

  const hasUnsavedMatrixChanges = Object.keys(dirtyPermissions).length > 0;

  const handleSaveMatrix = () => {
    if (!selectedRole) return;

    const finalPermissions: string[] = [];
    permissions.forEach((p: Permission) => {
      const code = p.code;
      const isGranted = isPermissionGranted(code);
      if (isGranted) {
        finalPermissions.push(p.id);
      }
    });

    savePermissions.mutate(
      { id: selectedRole.id, permissionIds: finalPermissions },
      {
        onSuccess: () => {
          setDirtyPermissions({});
        },
      }
    );
  };

  const handleDiscardMatrix = () => {
    setDirtyPermissions({});
  };

  const handleCreateRoleSubmit = (values: RoleFormValues) => {
    createRole.mutate(values, {
      onSuccess: (role) => {
        setSelectedRoleId(role.id);
        setShowCreateModal(false);
        createForm.reset();
      },
    });
  };

  const handleUpdateRoleSubmit = (values: RoleFormValues) => {
    if (!selectedRole) return;
    updateRole.mutate({
      id: selectedRole.id,
      payload: values,
    });
  };

  const handleConfirmAction = () => {
    if (confirmDialog.actionType === "delete" && selectedRole) {
      deleteRole.mutate(selectedRole.id, {
        onSuccess: () => {
          setSelectedRoleId(roles[0]?.id || null);
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
        },
      });
    } else if (confirmDialog.actionType === "save_matrix") {
      handleSaveMatrix();
      setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
    } else if (confirmDialog.actionType === "unassign" && confirmDialog.extraData) {
      unassignUserRole.mutate(
        {
          userId: confirmDialog.extraData.userId,
          roleId: confirmDialog.extraData.roleId,
        },
        {
          onSuccess: () => {
            setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
          },
        }
      );
    }
  };

  const headerActions = [
    {
      label: "Create Custom Role",
      icon: Plus,
      onClick: () => setShowCreateModal(true),
      className: "bg-gradient-to-r from-primary to-indigo-600 shadow-md text-white font-semibold",
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Role-Based Access Control (RBAC)"
        description="Configure roles, permissions, authorization matrices, and user assignments."
        actions={headerActions}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4 items-start">
        {/* Left side: Roles List */}
        <Card className="lg:col-span-1 border-border/60 shadow-sm bg-card/65 backdrop-blur-sm">
          <CardHeader className="p-4 border-b border-border/60">
            <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Enterprise Roles
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2 space-y-1">
            {isRolesLoading ? (
              <div className="p-4 text-center text-xs text-muted-foreground animate-pulse">Loading roles...</div>
            ) : (
              roles.map((role: Role) => {
                const isSelected = role.id === selectedRoleId;
                return (
                  <button
                    key={role.id}
                    onClick={() => {
                      setSelectedRoleId(role.id);
                      setDirtyPermissions({});
                      setActiveTab("matrix");
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg text-left text-sm transition-all ${
                      isSelected
                        ? "bg-primary/10 text-primary font-bold shadow-sm"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {role.is_system_role ? (
                        <span title="System Role">
                          <Lock className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
                        </span>
                      ) : (
                        <Shield className="h-3.5 w-3.5 flex-shrink-0 text-primary" />
                      )}
                      <span className="truncate">{role.name}</span>
                    </div>
                    {role.is_system_role && (
                      <Badge
                        variant="muted"
                        className="text-[9px] py-0 px-1 font-semibold uppercase tracking-wider scale-90 border border-border"
                      >
                        System
                      </Badge>
                    )}
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Right side: Detailed View */}
        <div className="lg:col-span-3 space-y-6">
          {selectedRole ? (
            <Card className="border-border/60 shadow-md bg-card/65 backdrop-blur-sm overflow-hidden">
              {/* Header */}
              <div className="p-6 border-b border-border/60 flex flex-col gap-4 md:flex-row md:items-center md:justify-between bg-muted/10">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold">{selectedRole.name}</h2>
                    {selectedRole.is_system_role ? (
                      <Badge variant="muted" className="border border-border text-muted-foreground bg-muted/40 font-mono text-xs">
                        System Managed
                      </Badge>
                    ) : (
                      <Badge variant="muted" className="border border-primary/20 text-primary bg-primary/5 font-mono text-xs">
                        Custom Role
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedRole.description || "No description provided."}
                  </p>
                </div>

                {/* Tabs selection */}
                <div className="flex bg-muted p-1 rounded-lg border border-border">
                  <button
                    onClick={() => setActiveTab("matrix")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                      activeTab === "matrix" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Grid className="h-3.5 w-3.5" />
                    Permissions
                  </button>
                  <button
                    onClick={() => setActiveTab("users")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                      activeTab === "users" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Users className="h-3.5 w-3.5" />
                    Operators ({assignedUsers.length})
                  </button>
                  <button
                    onClick={() => setActiveTab("settings")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                      activeTab === "settings" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Settings className="h-3.5 w-3.5" />
                    Settings
                  </button>
                </div>
              </div>

              {/* Tab 1: Permissions Matrix */}
              {activeTab === "matrix" && (
                <div className="p-0">
                  {selectedRole.is_system_role && (
                    <div className="m-6 p-3 rounded-lg border border-yellow-500/20 bg-yellow-500/5 text-xs text-yellow-600 flex items-start gap-2">
                      <Lock className="h-4 w-4 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="font-bold">System Role Notice:</span> This role is baked into the security core. Its permission mappings cannot be altered to preserve system stability.
                      </div>
                    </div>
                  )}

                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[800px] border-collapse text-left text-xs">
                      <thead>
                        <tr className="border-b border-border bg-muted/20 text-muted-foreground font-bold uppercase tracking-wider">
                          <th className="p-4 w-[250px]">Module</th>
                          {ACTIONS.map((action) => (
                            <th key={action.key} className="p-4 text-center w-[90px]">
                              {action.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {MODULES.map((mod) => (
                          <tr key={mod.key} className="hover:bg-muted/10">
                            <td className="p-4 font-semibold text-foreground text-sm">{mod.label}</td>
                            {ACTIONS.map((action) => {
                              const code = getPermissionCode(mod.key, action.key);
                              const isGranted = isPermissionGranted(code);
                              const isAvailable = permissions.some((p: Permission) => p.code === code);

                              return (
                                <td key={action.key} className="p-4 text-center">
                                  {isAvailable ? (
                                    <input
                                      type="checkbox"
                                      checked={isGranted}
                                      disabled={selectedRole.is_system_role}
                                      onChange={(e) => handleCheckboxChange(code, e.target.checked)}
                                      className={`rounded border-border h-4 w-4 ${
                                        selectedRole.is_system_role
                                          ? "opacity-50 cursor-not-allowed text-muted"
                                          : "text-primary focus:ring-primary cursor-pointer"
                                      }`}
                                    />
                                  ) : (
                                    <span className="text-[10px] text-muted-foreground/40 font-mono">—</span>
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Save Matrix changes bar */}
                  {hasUnsavedMatrixChanges && (
                    <div className="sticky bottom-0 border-t border-primary/20 bg-primary/5 p-4 flex items-center justify-between animate-in slide-in-from-bottom-4 duration-300">
                      <span className="text-sm font-semibold text-primary">You have unsaved changes in the permissions matrix.</span>
                      <div className="flex gap-2">
                        <Button variant="outline" onClick={handleDiscardMatrix}>
                          Discard
                        </Button>
                        <Button onClick={handleSaveMatrix} className="bg-gradient-to-r from-primary to-indigo-600 text-white font-semibold">
                          Save Changes
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Assigned Users */}
              {activeTab === "users" && (
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">Authorized Operators</h3>
                    <Button onClick={() => setShowAssignModal(true)} size="sm" className="gap-1 bg-primary text-white font-semibold shadow-sm">
                      <UserPlus className="h-3.5 w-3.5" />
                      Assign User
                    </Button>
                  </div>

                  {assignedUsers.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-8 border border-dashed border-border rounded-lg text-center gap-2">
                      <Users className="h-8 w-8 text-muted-foreground/60" />
                      <p className="text-xs font-semibold">No users assigned to this role</p>
                      <p className="text-[10px] text-muted-foreground">Assign this role to operators to grant access.</p>
                    </div>
                  ) : (
                    <div className="divide-y divide-border/60 border border-border rounded-lg overflow-hidden bg-card/40">
                      {assignedUsers.map((user: User) => (
                        <div key={user.id} className="flex items-center justify-between p-3.5 hover:bg-muted/20 transition-colors">
                          <div className="flex items-center gap-3">
                            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                              {user.full_name
                                .split(" ")
                                .map((n) => n[0])
                                .slice(0, 2)
                                .join("")}
                            </div>
                            <div>
                              <div className="text-sm font-semibold">{user.full_name}</div>
                              <div className="text-xs text-muted-foreground">{user.email}</div>
                            </div>
                          </div>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setConfirmDialog({
                                isOpen: true,
                                title: "Revoke Role Assignment",
                                description: `Are you sure you want to remove the "${selectedRole.name}" role from ${user.full_name}? This may immediately revoke their access rights to related systems.`,
                                confirmText: "Revoke Access",
                                variant: "destructive",
                                requireTypeConfirmation: false,
                                typeConfirmationWord: "",
                                actionType: "unassign",
                                extraData: { userId: user.id, roleId: selectedRole.id },
                              })
                            }
                            className="h-8 text-xs font-semibold text-destructive hover:bg-destructive/10"
                          >
                            <UserMinus className="h-3.5 w-3.5 mr-1" />
                            Revoke
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              )}

              {/* Tab 3: Settings */}
              {activeTab === "settings" && (
                <CardContent className="p-6 space-y-6">
                  {selectedRole.is_system_role ? (
                    <div className="flex flex-col items-center justify-center p-8 text-center gap-2">
                      <Lock className="h-8 w-8 text-muted-foreground/60" />
                      <p className="text-sm font-bold">System Role Settings Restricted</p>
                      <p className="text-xs text-muted-foreground max-w-sm">
                        Metadata and lifecycle for system-defined roles are managed by the kernel and cannot be renamed or deleted.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <form onSubmit={updateForm.handleSubmit(handleUpdateRoleSubmit)} className="space-y-4">
                        <TextField
                          name="name"
                          control={updateForm.control}
                          label="Role Name"
                          required
                        />
                        <TextField
                          name="description"
                          control={updateForm.control}
                          label="Description"
                        />
                        <FormActions className="mt-2 border-t-0 pt-0">
                          <Button
                            type="submit"
                            disabled={updateRole.isPending}
                            className="bg-primary text-white font-semibold"
                          >
                            {updateRole.isPending ? "Saving..." : "Update Details"}
                          </Button>
                        </FormActions>
                      </form>

                      <div className="h-px bg-border" />

                      <div className="space-y-3 rounded-lg border border-destructive/20 bg-destructive/5 p-5">
                        <h4 className="text-sm font-bold text-destructive">Danger Zone</h4>
                        <p className="text-xs text-muted-foreground max-w-md">
                          Deleting this role will immediately unassign it from all active users. This action is soft-deleted but will cause immediate service disruption.
                        </p>
                        <Button
                          variant="destructive"
                          onClick={() =>
                            setConfirmDialog({
                              isOpen: true,
                              title: `Delete Custom Role: ${selectedRole.name}`,
                              description: `Are you sure you want to delete the "${selectedRole.name}" role? All assigned operators will lose this role authorization. Type "${selectedRole.name}" below to confirm:`,
                              confirmText: "Delete Role",
                              variant: "destructive",
                              requireTypeConfirmation: true,
                              typeConfirmationWord: selectedRole.name,
                              actionType: "delete",
                            })
                          }
                          className="font-semibold text-white"
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" />
                          Delete Role
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
              Please select or create a role.
            </div>
          )}
        </div>
      </div>

      {/* Create Custom Role Dialog */}
      <Modal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        title="Create Custom Role"
        size="sm"
        isLoading={createRole.isPending}
        footer={
          <>
            <Button variant="outline" type="button" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              form="create-role-form"
              disabled={createRole.isPending}
              className="bg-gradient-to-r from-primary to-indigo-600 text-white font-semibold"
            >
              {createRole.isPending ? "Creating..." : "Create Role"}
            </Button>
          </>
        }
      >
        <form id="create-role-form" onSubmit={createForm.handleSubmit(handleCreateRoleSubmit)} className="space-y-4 px-1">
          <TextField
            name="name"
            control={createForm.control}
            label="Role Name"
            required
            placeholder="e.g. Server Operator"
          />
          <TextField
            name="description"
            control={createForm.control}
            label="Description"
            placeholder="e.g. Read-write access to servers only"
          />
        </form>
      </Modal>

      {/* Assign Users Modal */}
      <Modal
        open={showAssignModal}
        onOpenChange={setShowAssignModal}
        title="Assign User to Role"
        description={`Select users to associate with the "${selectedRole?.name}" role.`}
        size="md"
        footer={
          <Button onClick={() => setShowAssignModal(false)} className="bg-primary text-white font-semibold">
            Done
          </Button>
        }
      >
        <div className="space-y-4 px-1">
          <SearchInput
            placeholder="Filter users by name or email..."
            value={assignUserSearch}
            onChange={setAssignUserSearch}
          />

          <div className="max-h-[300px] overflow-y-auto divide-y divide-border border border-border rounded-lg">
            {!allUsers || !allUsers.items || allUsers.items.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground">No users match your criteria</div>
            ) : (
              allUsers.items.map((user: User) => {
                const isAlreadyAssigned = assignedUsers.some((au: User) => au.id === user.id);
                return (
                  <div key={user.id} className="flex items-center justify-between p-3">
                    <div>
                      <div className="text-sm font-semibold">{user.full_name}</div>
                      <div className="text-xs text-muted-foreground">{user.email}</div>
                    </div>

                    {isAlreadyAssigned ? (
                      <Badge variant="muted" className="text-[10px] py-1 px-2 font-mono border border-border">
                        <Check className="h-3 w-3 mr-1 inline-block" />
                        Assigned
                      </Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          if (selectedRole) {
                            assignUserRole.mutate({
                              userId: user.id,
                              roleId: selectedRole.id,
                            });
                          }
                        }}
                        className="h-8 text-xs bg-muted/40 font-semibold"
                        disabled={assignUserRole.isPending}
                      >
                        <UserPlus className="h-3.5 w-3.5 mr-1" />
                        Assign
                      </Button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </Modal>

      {/* Confirmation Dialog Component */}
      <ConfirmationDialog
        isOpen={confirmDialog.isOpen}
        onClose={() => setConfirmDialog((prev) => ({ ...prev, isOpen: false }))}
        onConfirm={handleConfirmAction}
        title={confirmDialog.title}
        description={confirmDialog.description}
        confirmText={confirmDialog.confirmText}
        variant={confirmDialog.variant}
        requireTypeConfirmation={confirmDialog.requireTypeConfirmation}
        typeConfirmationWord={confirmDialog.typeConfirmationWord}
        isLoading={deleteRole.isPending || savePermissions.isPending}
      />
    </div>
  );
}
