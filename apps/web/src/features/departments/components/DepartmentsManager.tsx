"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Edit, Trash2, Building2 } from "lucide-react";

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

import { useDepartments } from "@/hooks";
import { departmentSchema, type DepartmentFormValues } from "@/schemas";
import { DEPARTMENT_STATUS_OPTIONS } from "../utils/constants";
import { formatDateTime } from "@/utils/formatters";
import type { Department } from "../types";


export function DepartmentsManager() {
  // Filters & Pagination State
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Form Modal State
  const [showFormModal, setShowFormModal] = useState(false);
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);

  // Delete Dialog State
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deptToDelete, setDeptToDelete] = useState<Department | null>(null);

  // Custom hook for departments queries/mutations
  const {
    data: deptsData,
    isLoading,
    createDepartment,
    updateDepartment,
    deleteDepartment,
  } = useDepartments({
    page,
    size: pageSize,
    search,
    status: statusFilter,
  });

  // RHF Setup
  const { control, handleSubmit, reset } = useForm<DepartmentFormValues>({
    resolver: zodResolver(departmentSchema),
    defaultValues: {
      name: "",
      description: "",
      status: "active",
    },
  });

  // Reset form when modal opens/closes or selectedDept changes
  useEffect(() => {
    if (selectedDept) {
      reset({
        name: selectedDept.name,
        description: selectedDept.description || "",
        status: selectedDept.status as "active" | "inactive",
      });
    } else {
      reset({
        name: "",
        description: "",
        status: "active",
      });
    }
  }, [selectedDept, showFormModal, reset]);

  const handleCreateClick = () => {
    setSelectedDept(null);
    setShowFormModal(true);
  };

  const handleEditClick = (dept: Department) => {
    setSelectedDept(dept);
    setShowFormModal(true);
  };

  const handleDeleteClick = (dept: Department) => {
    setDeptToDelete(dept);
    setShowDeleteDialog(true);
  };

  const onSubmit = (values: DepartmentFormValues) => {
    const payload = {
      name: values.name.trim(),
      description: values.description?.trim() || null,
      status: values.status,
    };

    if (selectedDept) {
      updateDepartment.mutate(
        { id: selectedDept.id, payload },
        {
          onSuccess: () => {
            setShowFormModal(false);
            setSelectedDept(null);
          },
        }
      );
    } else {
      createDepartment.mutate(payload, {
        onSuccess: () => {
          setShowFormModal(false);
        },
      });
    }
  };

  const headerActions = [
    {
      label: "Add Department",
      icon: Plus,
      onClick: handleCreateClick,
      className: "bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white shadow-md font-semibold",
    },
  ];

  const columns = [
    {
      key: "name",
      header: "Department Name",
      render: (dept: Department) => <span className="font-semibold text-foreground">{dept.name}</span>,
    },
    {
      key: "description",
      header: "Description",
      render: (dept: Department) => <span className="text-muted-foreground">{dept.description || "—"}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (dept: Department) => <StatusBadge status={dept.status} />,
    },
    {
      key: "created_at",
      header: "Created Date",
      render: (dept: Department) => <span className="text-muted-foreground">{formatDateTime(dept.created_at)}</span>,
    },
    {
      key: "actions",
      header: "Actions",
      headerClassName: "text-right",
      className: "text-right",
      render: (dept: Department) => (
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditClick(dept)}
            className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted p-0"
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteClick(dept)}
            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 p-0"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  const isMutating = createDepartment.isPending || updateDepartment.isPending;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Departments"
        description="Manage company departments dynamically and track team hierarchies."
        actions={headerActions}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Total Departments"
          value={deptsData?.total ?? 0}
          description="Registered departments"
          icon={Building2}
        />
      </div>

      <div className="border border-border/60 shadow-sm bg-card/60 backdrop-blur-md rounded-lg p-4 flex flex-col gap-4 md:flex-row md:items-end">
        <div className="flex-1 flex flex-col gap-1.5">
          <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Search</Label>
          <SearchInput
            placeholder="Search departments..."
            value={search}
            onChange={(val) => {
              setSearch(val);
              setPage(1);
            }}
          />
        </div>

        <FilterSelect
          label="Status"
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(val);
            setPage(1);
          }}
          options={DEPARTMENT_STATUS_OPTIONS}
          size="md"
          className="w-full md:w-[200px]"
        />
      </div>

      <DataTable
        columns={columns}
        data={deptsData?.items || []}
        loading={isLoading}
        loadingMessage="Loading departments directory..."
        emptyIcon={Building2}
        emptyTitle="No departments found"
        emptyDescription="Add a department or adjust filters to see records."
        rowKey={(dept: Department) => dept.id}
        page={page}
        pageSize={pageSize}
        total={deptsData?.total || 0}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        paginationLabel="departments"
      />

      <Modal
        open={showFormModal}
        onOpenChange={(open) => {
          if (!open) {
            setShowFormModal(false);
            setSelectedDept(null);
          }
        }}
        title={selectedDept ? "Edit Department" : "Add Department"}
        size="md"
        isLoading={isMutating}
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowFormModal(false);
                setSelectedDept(null);
              }}
              disabled={isMutating}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="department-form"
              disabled={isMutating}
              className="shadow-sm bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white font-semibold"
            >
              Save Changes
            </Button>
          </>
        }
      >
        <form id="department-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-1">
          <TextField
            name="name"
            control={control}
            label="Department Name"
            required
            placeholder="e.g. IT Infrastructure, Human Resources"
            disabled={isMutating}
          />

          <TextAreaField
            name="description"
            control={control}
            label="Description"
            placeholder="Explain the purpose of this department..."
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
          setDeptToDelete(null);
        }}
        onConfirm={async () => {
          if (deptToDelete) {
            deleteDepartment.mutate(deptToDelete.id, {
              onSuccess: () => {
                setShowDeleteDialog(false);
                setDeptToDelete(null);
              },
            });
          }
        }}
        title="Delete Department"
        description={`Are you sure you want to delete the department "${deptToDelete?.name}"? This will soft-delete the department and make it unavailable for new selections.`}
        confirmText="Delete"
        variant="destructive"
      />
    </div>
  );
}
