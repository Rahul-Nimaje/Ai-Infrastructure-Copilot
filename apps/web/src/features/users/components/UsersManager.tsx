"use client";

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { User, Role } from "@ai-infra-copilot/shared-types";
import {
  Plus,
  Edit,
  Trash2,
  X,
  Briefcase,
  Upload,
  Download,
  Shield,
  UserCheck,
  UserX,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { API_BASE_URL, getAccessToken, apiFetch } from "@/lib/api-client";
import { getInitials } from "@/utils/helpers";

import {
  PageHeader,
  SearchInput,
  FilterSelect,
  DataTable,
  StatusBadge,
  TextField,
  SelectField,
  FormField,
  FormGrid,
  Modal,
  AsyncSelect,
} from "@/components/common";

import { useUsers, useRoles } from "@/hooks";
import { userSchema, type UserFormValues } from "@/schemas";
import { DEPARTMENT_OPTIONS, USER_STATUS_OPTIONS } from "../utils/constants";
import type { UserStatus, BulkUserAction } from "../types";


export function UsersManager() {
  // Search, Pagination, Sort, Filter States
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Selection States for Bulk Actions
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Dialog / Modal States
  const [showFormModal, setShowFormModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [formError, setFormError] = useState("");

  // Confirmation Dialog States
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    confirmText: string;
    variant: "info" | "warning" | "destructive";
    requireTypeConfirmation: boolean;
    typeConfirmationWord: string;
    actionType: "delete" | "bulk_delete" | "bulk_activate" | "bulk_deactivate";
    targetId?: string;
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

  // Custom Users hook
  const {
    data: usersData,
    isLoading: isUsersLoading,
    createUser,
    updateUser,
    deleteUser,
    bulkAction,
    importCsv,
  } = useUsers({
    page,
    size: pageSize,
    search,
    status: statusFilter,
    departmentId: departmentFilter,
    role: roleFilter,
    sortBy,
    sortOrder,
  });

  // Fetch Roles
  const { roles: rolesData } = useRoles();

  // RHF Setup
  const { control, handleSubmit, reset, watch, setValue, formState: { errors } } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      fullName: "",
      username: "",
      email: "",
      password: "",
      employeeId: "",
      departmentId: "",
      designationId: "",
      phoneNumber: "",
      status: "active",
      roles: [],
    },
  });

  const departmentId = watch("departmentId");
  const designationId = watch("designationId");
  const selectedRoles = watch("roles") || [];

  // AsyncSelect fetchers for Department / Designation — backed by the real
  // paginated endpoints instead of an unpaginated fetch-all hook, so records
  // beyond a single default page never silently disappear from the picker.
  const fetchDepartmentOptions = useCallback(
    async ({ search, page }: { search: string; page: number }) => {
      const params = new URLSearchParams({ page: String(page), size: "20", status: "active" });
      if (search) params.set("search", search);
      const res = await apiFetch<{ items: { id: string; name: string }[]; total: number }>(
        `/api/v1/departments?${params.toString()}`
      );
      return { items: res.items.map((d) => ({ value: d.id, label: d.name })), total: res.total };
    },
    []
  );

  const fetchDesignationOptions = useCallback(
    async ({ search, page }: { search: string; page: number }) => {
      if (!departmentId) return { items: [], total: 0 };
      const params = new URLSearchParams({
        page: String(page),
        size: "20",
        status: "active",
        departmentId,
      });
      if (search) params.set("search", search);
      const res = await apiFetch<{ items: { id: string; name: string }[]; total: number }>(
        `/api/v1/designations?${params.toString()}`
      );
      return { items: res.items.map((d) => ({ value: d.id, label: d.name })), total: res.total };
    },
    [departmentId]
  );

  // Handle setting role selection array
  const toggleRoleSelection = (roleName: string) => {
    const current = [...selectedRoles];
    const index = current.indexOf(roleName);
    if (index > -1) {
      current.splice(index, 1);
    } else {
      current.push(roleName);
    }
    setValue("roles", current, { shouldValidate: true });
  };

  const handleEditClick = (user: User) => {
    setSelectedUser(user);
    reset({
      fullName: user.full_name,
      username: user.username || "",
      email: user.email,
      password: "",
      employeeId: user.employee_id || "",
      phoneNumber: user.phone_number || "",
      departmentId: (user as any).department_id || "",
      designationId: (user as any).designation_id || "",
      status: user.status as "active" | "invited" | "disabled",
      roles: user.roles || [],
    });
    setFormError("");
    setShowFormModal(true);
  };

  const handleCreateClick = () => {
    setSelectedUser(null);
    reset({
      fullName: "",
      username: "",
      email: "",
      password: "",
      employeeId: "",
      phoneNumber: "",
      departmentId: "",
      designationId: "",
      status: "active",
      roles: [],
    });
    setFormError("");
    setShowFormModal(true);
  };

  const onSubmit = (values: UserFormValues) => {
    setFormError("");

    if (values.roles.length === 0) {
      setFormError("At least one role must be selected");
      return;
    }

    const payload: any = {
      email: values.email,
      username: values.username,
      full_name: values.fullName,
      employee_id: values.employeeId || null,
      phone_number: values.phoneNumber || null,
      department_id: values.departmentId,
      designation_id: values.designationId,
      status: values.status,
      roles: values.roles,
    };

    if (selectedUser) {
      if (values.password) payload.password = values.password;
      updateUser.mutate(
        { id: selectedUser.id, payload },
        {
          onSuccess: () => {
            setShowFormModal(false);
            setSelectedUser(null);
          },
        }
      );
    } else {
      if (!values.password) {
        setFormError("Password is required for new users");
        return;
      }
      payload.password = values.password;
      createUser.mutate(payload, {
        onSuccess: () => {
          setShowFormModal(false);
        },
      });
    }
  };

  const handleConfirmAction = () => {
    if (confirmDialog.actionType === "delete" && confirmDialog.targetId) {
      deleteUser.mutate(confirmDialog.targetId, {
        onSuccess: () => {
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
          setSelectedIds((prev) => prev.filter((id) => id !== confirmDialog.targetId));
        },
      });
    } else if (confirmDialog.actionType === "bulk_delete") {
      bulkAction.mutate(
        { ids: selectedIds, action: "delete" },
        {
          onSuccess: () => {
            setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
            setSelectedIds([]);
          },
        }
      );
    } else if (confirmDialog.actionType === "bulk_activate") {
      bulkAction.mutate(
        { ids: selectedIds, action: "activate" },
        {
          onSuccess: () => {
            setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
            setSelectedIds([]);
          },
        }
      );
    } else if (confirmDialog.actionType === "bulk_deactivate") {
      bulkAction.mutate(
        { ids: selectedIds, action: "deactivate" },
        {
          onSuccess: () => {
            setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
            setSelectedIds([]);
          },
        }
      );
    }
  };

  const handleExport = () => {
    const token = getAccessToken();
    window.open(`${API_BASE_URL}/api/v1/users/export/csv?token=${token || ""}`, "_blank");
  };

  const handleCsvImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      importCsv.mutate(file);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === (usersData?.items?.length || 0)) {
      setSelectedIds([]);
    } else {
      setSelectedIds(usersData?.items?.map((u) => u.id) || []);
    }
  };

  const toggleSelectUser = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]));
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortOrder("asc");
    }
    setPage(1);
  };

  const headerActions = [
    {
      label: "Export CSV",
      icon: Download,
      variant: "outline" as const,
      onClick: handleExport,
    },
    {
      label: "Add User",
      icon: Plus,
      onClick: handleCreateClick,
      className: "bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 shadow-md text-white font-semibold",
    },
  ];

  const columns = [
    {
      key: "full_name",
      header: "Full Name",
      sortable: true,
      render: (user: User) => (
        <div className="flex items-center gap-2">
          {user.profile_picture ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={user.profile_picture}
              alt={user.full_name}
              className="h-7 w-7 rounded-full object-cover border border-border"
            />
          ) : (
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
              {getInitials(user.full_name)}
            </div>
          )}
          {user.full_name}
        </div>
      ),
    },
    {
      key: "username",
      header: "Username",
      sortable: true,
      render: (user: User) => <span className="text-muted-foreground font-mono text-xs">@{user.username || "unset"}</span>,
    },
    {
      key: "email",
      header: "Email",
      render: (user: User) => <span>{user.email}</span>,
    },
    {
      key: "employee_id",
      header: "Employee ID",
      render: (user: User) => <span className="text-muted-foreground">{user.employee_id || "—"}</span>,
    },
    {
      key: "department",
      header: "Department & Role",
      render: (user: User) => (
        <div className="flex flex-col gap-0.5">
          <span className="flex items-center gap-1 text-xs font-semibold">
            <Briefcase className="h-3 w-3 text-muted-foreground" />
            {user.designation || "Not specified"}
          </span>
          <span className="text-xs text-muted-foreground">{user.department || "No Department"}</span>
        </div>
      ),
    },
    {
      key: "roles",
      header: "Roles Granted",
      render: (user: User) => (
        <div className="flex flex-wrap gap-1">
          {user.roles?.map((r) => (
            <Badge key={r} variant="muted" className="text-[10px] border border-border/70 py-0 px-1 bg-muted/40 font-mono">
              {r}
            </Badge>
          )) || <span className="text-xs text-muted-foreground">None</span>}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (user: User) => <StatusBadge status={user.status} />,
    },
    {
      key: "actions",
      header: "Actions",
      headerClassName: "text-right",
      className: "text-right",
      render: (user: User) => (
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => handleEditClick(user)} className="h-8 w-8 p-0">
            <Edit className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setConfirmDialog({
                isOpen: true,
                title: `Delete User: ${user.full_name}`,
                description: `Are you sure you want to delete user ${user.full_name} (@${user.username})? Type "${user.username}" to confirm:`,
                confirmText: "Delete User",
                variant: "destructive",
                requireTypeConfirmation: true,
                typeConfirmationWord: user.username || "",
                actionType: "delete",
                targetId: user.id,
              })
            }
            className="h-8 w-8 p-0 hover:bg-destructive/10"
          >
            <Trash2 className="h-3.5 w-3.5 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  const isMutating = createUser.isPending || updateUser.isPending;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="User Management"
        description="Manage organization users, profile attributes, and roles."
        actions={headerActions}
      >
        <label className="flex items-center gap-2 cursor-pointer rounded-lg border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-muted transition-colors">
          <Upload className="h-4 w-4 text-muted-foreground" />
          <span>Import CSV</span>
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleCsvImport}
            disabled={importCsv.isPending}
          />
        </label>
      </PageHeader>

      {/* Bulk Operations Toolbar */}
      {selectedIds.length > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-primary/20 bg-primary/5 p-4 animate-in slide-in-from-top-4 duration-300">
          <div className="flex items-center gap-2">
            <Badge variant="muted" className="border border-primary/30 text-primary font-bold bg-primary/5">
              {selectedIds.length} Selected
            </Badge>
            <span className="text-sm text-muted-foreground">Apply bulk action to selected users:</span>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setConfirmDialog({
                  isOpen: true,
                  title: "Bulk Activate Users",
                  description: `Are you sure you want to activate the ${selectedIds.length} selected users?`,
                  confirmText: "Activate Users",
                  variant: "info",
                  requireTypeConfirmation: false,
                  typeConfirmationWord: "",
                  actionType: "bulk_activate",
                })
              }
              className="gap-1.5 text-xs font-semibold"
            >
              <UserCheck className="h-3.5 w-3.5" />
              Activate
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setConfirmDialog({
                  isOpen: true,
                  title: "Bulk Deactivate Users",
                  description: `Are you sure you want to disable the ${selectedIds.length} selected users? This will lock their accounts.`,
                  confirmText: "Disable Users",
                  variant: "warning",
                  requireTypeConfirmation: false,
                  typeConfirmationWord: "",
                  actionType: "bulk_deactivate",
                })
              }
              className="gap-1.5 text-xs font-semibold"
            >
              <UserX className="h-3.5 w-3.5" />
              Disable
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() =>
                setConfirmDialog({
                  isOpen: true,
                  title: "Bulk Delete Users",
                  description: `WARNING: You are about to soft-delete ${selectedIds.length} users. Type DELETE to confirm:`,
                  confirmText: "Delete Users",
                  variant: "destructive",
                  requireTypeConfirmation: true,
                  typeConfirmationWord: "DELETE",
                  actionType: "bulk_delete",
                })
              }
              className="gap-1.5 text-xs font-semibold"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete
            </Button>
          </div>
        </div>
      )}

      {/* Filtering & Search Card */}
      <div className="border border-border/60 shadow-sm bg-card/60 backdrop-blur-md rounded-lg p-4 flex flex-col gap-4 md:flex-row md:items-end">
        <div className="flex-1 flex flex-col gap-1.5">
          <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Search</Label>
          <SearchInput
            placeholder="Search name, username, email, employee ID..."
            value={search}
            onChange={(val) => {
              setSearch(val);
              setPage(1);
            }}
          />
        </div>

        <FilterSelect
          label="Department"
          value={departmentFilter}
          onChange={(val) => {
            setDepartmentFilter(val);
            setPage(1);
          }}
          options={DEPARTMENT_OPTIONS}
          size="md"
          className="w-full md:w-[200px]"
        />

        <FilterSelect
          label="Status"
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(val);
            setPage(1);
          }}
          options={USER_STATUS_OPTIONS}
          size="md"
          className="w-full md:w-[150px]"
        />

        {(search || statusFilter || departmentFilter || roleFilter) && (
          <Button
            variant="ghost"
            onClick={() => {
              setSearch("");
              setStatusFilter("");
              setDepartmentFilter("");
              setRoleFilter("");
              setPage(1);
            }}
            className="text-xs font-semibold text-muted-foreground hover:text-foreground h-10 px-3"
          >
            <X className="h-3.5 w-3.5 mr-1" />
            Clear Filters
          </Button>
        )}
      </div>

      {/* Users DataTable */}
      <DataTable
        columns={columns}
        data={usersData?.items || []}
        loading={isUsersLoading}
        loadingMessage="Loading users directory..."
        emptyIcon={Plus}
        emptyTitle="No users found"
        emptyDescription="Try clearing your filters or add a new user to start."
        rowKey={(user: User) => user.id}
        selectable
        selectedIds={selectedIds}
        onSelectAll={toggleSelectAll}
        onSelectRow={toggleSelectUser}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSort={handleSort}
        page={page}
        pageSize={pageSize}
        total={usersData?.total || 0}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        paginationLabel="users"
        minWidth="1000px"
      />

      {/* Create / Edit Form Modal */}
      <Modal
        open={showFormModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowFormModal(false);
            setSelectedUser(null);
          }
        }}
        title={selectedUser ? "Edit User Profile" : "Register New User"}
        description="Enter employee details, credentials, and role authorizations."
        size="lg"
        isLoading={isMutating}
        modal={false}
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowFormModal(false);
                setSelectedUser(null);
              }}
              disabled={isMutating}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="user-form"
              disabled={isMutating}
              className="bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white font-semibold"
            >
              {selectedUser ? "Update User" : "Create User"}
            </Button>
          </>
        }
      >
        <form id="user-form" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-4 px-1">
            {formError && (
                  <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-xs font-semibold text-destructive">
                    {formError}
                  </div>
                )}

                <FormGrid>
                  <TextField
                    name="fullName"
                    control={control}
                    label="Full Name"
                    required
                    placeholder="e.g. John Doe"
                    disabled={isMutating}
                  />
                  <TextField
                    name="username"
                    control={control}
                    label="Username (e.g. jsmith)"
                    required
                    placeholder="e.g. jsmith"
                    disabled={isMutating}
                  />
                </FormGrid>

                <FormGrid>
                  <TextField
                    name="email"
                    control={control}
                    label="Email Address"
                    required
                    type="email"
                    placeholder="e.g. john.doe@corp.internal"
                    disabled={isMutating}
                  />
                  <TextField
                    name="password"
                    control={control}
                    label={selectedUser ? "Password Reset (leave blank to keep)" : "Password"}
                    required={!selectedUser}
                    type="password"
                    placeholder={selectedUser ? "••••••••" : "Min 8 characters"}
                    disabled={isMutating}
                  />
                </FormGrid>

                <FormGrid className="grid-cols-3">
                  <TextField
                    name="employeeId"
                    control={control}
                    label="Employee ID"
                    placeholder="e.g. EMP-001"
                    disabled={isMutating}
                  />
                  <FormField label="Department" required error={errors.departmentId?.message}>
                    <AsyncSelect
                      value={departmentId || null}
                      onChange={(val) => {
                        setValue("departmentId", val || "", { shouldValidate: true });
                        setValue("designationId", "");
                      }}
                      fetchOptions={fetchDepartmentOptions}
                      placeholder="Select Department"
                      disabled={isMutating}
                    />
                  </FormField>
                  <FormField label="Designation" required error={errors.designationId?.message}>
                    <AsyncSelect
                      key={departmentId || "no-department"}
                      value={designationId || null}
                      onChange={(val) => setValue("designationId", val || "", { shouldValidate: true })}
                      fetchOptions={fetchDesignationOptions}
                      placeholder="Select Designation"
                      disabled={isMutating || !departmentId}
                    />
                  </FormField>
                </FormGrid>

                <FormGrid>
                  <TextField
                    name="phoneNumber"
                    control={control}
                    label="Phone Number"
                    placeholder="e.g. +1 (555) 012-3456"
                    disabled={isMutating}
                  />
                  <SelectField
                    name="status"
                    control={control}
                    label="Account Status"
                    options={[
                      { value: "active", label: "Active" },
                      { value: "invited", label: "Invited" },
                      { value: "disabled", label: "Disabled" },
                    ]}
                    disabled={isMutating}
                  />
                </FormGrid>

                {/* Role selection */}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold flex items-center gap-1">
                    <Shield className="h-4 w-4 text-primary" />
                    Assign Enterprise Roles
                  </Label>
                  <p className="text-xs text-muted-foreground mb-3">Roles grant default permissions to modules. Select all that apply.</p>
                  
                  <div className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-muted/20 p-4 max-h-[160px] overflow-y-auto">
                    {rolesData?.map((role: Role) => {
                      const isChecked = selectedRoles.includes(role.name);
                      return (
                        <label
                          key={role.id}
                          className={`flex items-start gap-2.5 p-2 rounded-md border transition-colors cursor-pointer text-xs ${
                            isChecked
                              ? "bg-primary/5 border-primary/30 text-foreground"
                              : "border-border/50 hover:bg-muted/50 text-muted-foreground"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleRoleSelection(role.name)}
                            className="mt-0.5 rounded border-border"
                          />
                          <div className="flex flex-col">
                            <span className="font-semibold">{role.name}</span>
                            <span className="text-[10px] text-muted-foreground line-clamp-1">{role.description}</span>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                  {errors.roles && <p className="text-xs text-destructive font-medium">{errors.roles.message}</p>}
                </div>
          </div>
        </form>
      </Modal>

      {/* Confirmation Dialog */}
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
      />
    </div>
  );
}
