"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Edit, Trash2, Briefcase } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";

import {
  PageHeader,
  SearchInput,
  FilterSelect,
  DataTable,
  StatusBadge,
  StatCard,
  TextField,
  TextAreaField,
  SelectField,
  Modal,
} from "@/components/common";

import { useDesignations, useDepartments } from "@/hooks";
import { designationSchema, type DesignationFormValues } from "@/schemas";
import { DESIGNATION_STATUS_OPTIONS } from "../utils/constants";
import { formatDateTime } from "@/utils/formatters";
import type { Designation } from "../types";


export function DesignationsManager() {
  // Filters & Pagination State
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Form Modal State
  const [showFormModal, setShowFormModal] = useState(false);
  const [selectedDesg, setSelectedDesg] = useState<Designation | null>(null);

  // Delete Dialog State
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [desgToDelete, setDesgToDelete] = useState<Designation | null>(null);

  // Fetch departments (for select lists)
  const { data: activeDeptsData } = useDepartments({ status: "active" });
  const { data: allDeptsData } = useDepartments({ size: 100 });

  const activeDepts = activeDeptsData?.items || [];
  const allDepts = allDeptsData?.items || [];

  // Fetch designations using custom hook
  const {
    data: desgData,
    isLoading,
    createDesignation,
    updateDesignation,
    deleteDesignation,
  } = useDesignations({
    page,
    size: pageSize,
    search,
    departmentId: deptFilter,
    status: statusFilter,
  });

  // RHF Setup
  const { control, handleSubmit, reset } = useForm<DesignationFormValues>({
    resolver: zodResolver(designationSchema),
    defaultValues: {
      name: "",
      department_id: "",
      description: "",
      status: "active",
    },
  });

  // Reset form when modal opens/closes or selectedDesg changes
  useEffect(() => {
    if (selectedDesg) {
      reset({
        name: selectedDesg.name,
        department_id: selectedDesg.department_id,
        description: selectedDesg.description || "",
        status: selectedDesg.status as "active" | "inactive",
      });
    } else {
      reset({
        name: "",
        department_id: "",
        description: "",
        status: "active",
      });
    }
  }, [selectedDesg, showFormModal, reset]);

  const handleCreateClick = () => {
    setSelectedDesg(null);
    setShowFormModal(true);
  };

  const handleEditClick = (desg: Designation) => {
    setSelectedDesg(desg);
    setShowFormModal(true);
  };

  const handleDeleteClick = (desg: Designation) => {
    setDesgToDelete(desg);
    setShowDeleteDialog(true);
  };

  const onSubmit = (values: DesignationFormValues) => {
    const payload = {
      name: values.name.trim(),
      department_id: values.department_id,
      description: values.description?.trim() || null,
      status: values.status,
    };

    if (selectedDesg) {
      updateDesignation.mutate(
        { id: selectedDesg.id, payload },
        {
          onSuccess: () => {
            setShowFormModal(false);
            setSelectedDesg(null);
          },
        }
      );
    } else {
      createDesignation.mutate(payload, {
        onSuccess: () => {
          setShowFormModal(false);
        },
      });
    }
  };

  const isMutating = createDesignation.isPending || updateDesignation.isPending;

  // Include selected designation's department if it is not in the active departments list
  const hasInactiveSelectedDept =
    selectedDesg &&
    control._defaultValues.department_id &&
    !activeDepts.some((d) => d.id === control._defaultValues.department_id);

  const inactiveDeptName = selectedDesg?.department_name || "Selected Department";

  const departmentFormOptions = [
    ...(activeDepts.map((d) => ({ value: d.id, label: d.name })) || []),
    ...(hasInactiveSelectedDept
      ? [{ value: control._defaultValues.department_id as string, label: `${inactiveDeptName} (Inactive)` }]
      : []),
  ];

  const headerActions = [
    {
      label: "Add Designation",
      icon: Plus,
      onClick: handleCreateClick,
      className: "bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white shadow-md font-semibold",
    },
  ];

  const columns = [
    {
      key: "name",
      header: "Designation Name",
      render: (desg: Designation) => <span className="font-semibold text-foreground">{desg.name}</span>,
    },
    {
      key: "department_name",
      header: "Department",
      render: (desg: Designation) => <span className="text-muted-foreground font-medium">{desg.department_name || "Unknown Department"}</span>,
    },
    {
      key: "description",
      header: "Description",
      render: (desg: Designation) => <span className="text-muted-foreground">{desg.description || "—"}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (desg: Designation) => <StatusBadge status={desg.status} />,
    },
    {
      key: "created_at",
      header: "Created Date",
      render: (desg: Designation) => <span className="text-muted-foreground">{formatDateTime(desg.created_at)}</span>,
    },
    {
      key: "actions",
      header: "Actions",
      headerClassName: "text-right",
      className: "text-right",
      render: (desg: Designation) => (
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditClick(desg)}
            className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted p-0"
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteClick(desg)}
            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 p-0"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  const departmentFilterOptions = [
    { value: "", label: "All Departments" },
    ...(allDepts.map((d) => ({ value: d.id, label: d.name })) || []),
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Designations"
        description="Structure corporate roles and map designations to active departments."
        actions={headerActions}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Total Designations"
          value={desgData?.total ?? 0}
          description="Registered roles"
          icon={Briefcase}
        />
      </div>

      <div className="border border-border/60 shadow-sm bg-card/60 backdrop-blur-md rounded-lg p-4 flex flex-col gap-4 md:flex-row md:items-end">
        <div className="flex-1 flex flex-col gap-1.5">
          <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Search</Label>
          <SearchInput
            placeholder="Search designations..."
            value={search}
            onChange={(val) => {
              setSearch(val);
              setPage(1);
            }}
          />
        </div>

        <FilterSelect
          label="Department"
          value={deptFilter}
          onChange={(val) => {
            setDeptFilter(val);
            setPage(1);
          }}
          options={departmentFilterOptions}
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
          options={DESIGNATION_STATUS_OPTIONS}
          size="md"
          className="w-full md:w-[150px]"
        />
      </div>

      <DataTable
        columns={columns}
        data={desgData?.items || []}
        loading={isLoading}
        loadingMessage="Loading designations directory..."
        emptyIcon={Briefcase}
        emptyTitle="No designations found"
        emptyDescription="Add a designation or adjust filters to see records."
        rowKey={(desg: Designation) => desg.id}
        page={page}
        pageSize={pageSize}
        total={desgData?.total || 0}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        paginationLabel="designations"
      />

      <Modal
        open={showFormModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowFormModal(false);
            setSelectedDesg(null);
          }
        }}
        title={selectedDesg ? "Edit Designation" : "Add Designation"}
        size="md"
        isLoading={isMutating}
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowFormModal(false);
                setSelectedDesg(null);
              }}
              disabled={isMutating}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="designation-form"
              disabled={isMutating}
              className="shadow-sm bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white font-semibold"
            >
              Save Changes
            </Button>
          </>
        }
      >
        <form id="designation-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-1">
          <SelectField
            name="department_id"
            control={control}
            label="Department"
            required
            placeholder="Select Department"
            options={departmentFormOptions}
            disabled={isMutating}
          />

          <TextField
            name="name"
            control={control}
            label="Designation Name"
            required
            placeholder="e.g. Software Engineer, Senior HR Manager"
            disabled={isMutating}
          />

          <TextAreaField
            name="description"
            control={control}
            label="Description"
            placeholder="Explain the job duties or responsibilities..."
            disabled={isMutating}
          />

          <SelectField
            name="status"
            control={control}
            label="Status"
            options={[
              { value: "active", label: "Active" },
              { value: "inactive", label: "Inactive" },
            ]}
            disabled={isMutating}
          />
        </form>
      </Modal>

      <ConfirmationDialog
        isOpen={showDeleteDialog}
        onClose={() => {
          setShowDeleteDialog(false);
          setDesgToDelete(null);
        }}
        onConfirm={async () => {
          if (desgToDelete) {
            deleteDesignation.mutate(desgToDelete.id, {
              onSuccess: () => {
                setShowDeleteDialog(false);
                setDesgToDelete(null);
              },
            });
          }
        }}
        title="Delete Designation"
        description={`Are you sure you want to delete the designation "${desgToDelete?.name}"? This will soft-delete the designation and make it unavailable for user assignments.`}
        confirmText="Delete"
        variant="destructive"
      />
    </div>
  );
}
