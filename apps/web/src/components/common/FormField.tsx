"use client";

import React from "react";
import { useController, Control, FieldPath, FieldValues } from "react-hook-form";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

// ─── Generic FormField Wrapper ─────────────────────────────────
export interface FormFieldWrapperProps {
  label?: string;
  required?: boolean;
  error?: string;
  helperText?: string;
  className?: string;
  children: React.ReactNode;
}

export function FormField({
  label,
  required,
  error,
  helperText,
  className = "",
  children,
}: FormFieldWrapperProps) {
  return (
    <div className={cn("flex flex-col gap-1.5 w-full", className)}>
      {label && (
        <Label className="text-sm font-semibold text-foreground">
          {label}
          {required && <span className="text-destructive ml-1">*</span>}
        </Label>
      )}
      {children}
      {error && <p className="text-xs text-destructive font-medium">{error}</p>}
      {!error && helperText && <p className="text-xs text-muted-foreground">{helperText}</p>}
    </div>
  );
}

// ─── Base Field Props for RHF Integration ──────────────────────
export interface BaseFieldProps<TFieldValues extends FieldValues = FieldValues> {
  name: FieldPath<TFieldValues>;
  control: Control<TFieldValues>;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  helperText?: string;
  onChange?: (val: any) => void;
}

// ─── TextField Component ───────────────────────────────────────
export function TextField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  placeholder,
  className,
  helperText,
  type = "text",
  onChange,
}: BaseFieldProps<TFieldValues> & { type?: string }) {
  const {
    field,
    fieldState: { error },
  } = useController({ name, control });

  return (
    <FormField
      label={label}
      required={required}
      error={error?.message}
      helperText={helperText}
      className={className}
    >
      <Input
        {...field}
        type={type}
        disabled={disabled}
        placeholder={placeholder}
        value={field.value ?? ""}
        onChange={(e) => {
          field.onChange(e);
          onChange?.(e.target.value);
        }}
        className={cn(error && "border-destructive focus-visible:ring-destructive")}
      />
    </FormField>
  );
}

// ─── NumberField Component ─────────────────────────────────────
export function NumberField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  placeholder,
  className,
  helperText,
  onChange,
}: BaseFieldProps<TFieldValues>) {
  const {
    field,
    fieldState: { error },
  } = useController({ name, control });

  return (
    <FormField
      label={label}
      required={required}
      error={error?.message}
      helperText={helperText}
      className={className}
    >
      <Input
        {...field}
        type="number"
        disabled={disabled}
        placeholder={placeholder}
        value={field.value ?? ""}
        onChange={(e) => {
          const val = e.target.value === "" ? null : Number(e.target.value);
          field.onChange(val);
          onChange?.(val);
        }}
        className={cn(error && "border-destructive focus-visible:ring-destructive")}
      />
    </FormField>
  );
}

// ─── PasswordField Component ───────────────────────────────────
export function PasswordField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  placeholder,
  className,
  helperText,
  onChange,
}: BaseFieldProps<TFieldValues>) {
  return (
    <TextField
      name={name}
      control={control}
      label={label}
      required={required}
      disabled={disabled}
      placeholder={placeholder}
      className={className}
      helperText={helperText}
      type="password"
      onChange={onChange}
    />
  );
}

// ─── TextAreaField Component ───────────────────────────────────
export function TextAreaField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  placeholder,
  className,
  helperText,
  rows = 3,
  onChange,
}: BaseFieldProps<TFieldValues> & { rows?: number }) {
  const {
    field,
    fieldState: { error },
  } = useController({ name, control });

  return (
    <FormField
      label={label}
      required={required}
      error={error?.message}
      helperText={helperText}
      className={className}
    >
      <textarea
        {...field}
        rows={rows}
        disabled={disabled}
        placeholder={placeholder}
        value={field.value ?? ""}
        onChange={(e) => {
          field.onChange(e);
          onChange?.(e.target.value);
        }}
        className={cn(
          "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          error && "border-destructive focus-visible:ring-destructive"
        )}
      />
    </FormField>
  );
}

// ─── SelectField Component ─────────────────────────────────────
export interface SelectOption {
  value: string;
  label: string;
}

export function SelectField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  placeholder,
  className,
  helperText,
  options,
  onChange,
}: BaseFieldProps<TFieldValues> & { options: readonly SelectOption[] | SelectOption[] }) {
  const {
    field,
    fieldState: { error },
  } = useController({ name, control });

  return (
    <FormField
      label={label}
      required={required}
      error={error?.message}
      helperText={helperText}
      className={className}
    >
      <select
        {...field}
        disabled={disabled}
        value={field.value ?? ""}
        onChange={(e) => {
          field.onChange(e);
          onChange?.(e.target.value);
        }}
        className={cn(
          "h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50",
          error && "border-destructive focus-visible:ring-destructive"
        )}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </FormField>
  );
}

// ─── CheckboxField Component ───────────────────────────────────
export function CheckboxField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  className,
  helperText,
  onChange,
}: BaseFieldProps<TFieldValues>) {
  const {
    field,
    fieldState: { error },
  } = useController({ name, control });

  return (
    <div className={cn("flex flex-col gap-1 w-full", className)}>
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={!!field.value}
          disabled={disabled}
          onChange={(e) => {
            field.onChange(e.target.checked);
            onChange?.(e.target.checked);
          }}
          className="h-4 w-4 rounded border-input text-primary focus:ring-ring disabled:opacity-50"
        />
        {label && (
          <span className="text-sm font-medium text-foreground">
            {label}
            {required && <span className="text-destructive ml-1">*</span>}
          </span>
        )}
      </label>
      {error && <p className="text-xs text-destructive font-medium">{error.message}</p>}
      {!error && helperText && <p className="text-xs text-muted-foreground">{helperText}</p>}
    </div>
  );
}

// ─── SwitchField Component ─────────────────────────────────────
export function SwitchField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  className,
  helperText,
  onChange,
}: BaseFieldProps<TFieldValues>) {
  const {
    field,
    fieldState: { error },
  } = useController({ name, control });

  return (
    <div className={cn("flex flex-col gap-1 w-full", className)}>
      <label className="flex items-center justify-between cursor-pointer select-none">
        {label && (
          <span className="text-sm font-medium text-foreground">
            {label}
            {required && <span className="text-destructive ml-1">*</span>}
          </span>
        )}
        <div className="relative">
          <input
            type="checkbox"
            checked={!!field.value}
            disabled={disabled}
            onChange={(e) => {
              field.onChange(e.target.checked);
              onChange?.(e.target.checked);
            }}
            className="sr-only peer"
          />
          <div className="w-9 h-5 bg-muted peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-background after:border-border after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary" />
        </div>
      </label>
      {error && <p className="text-xs text-destructive font-medium">{error.message}</p>}
      {!error && helperText && <p className="text-xs text-muted-foreground">{helperText}</p>}
    </div>
  );
}

// ─── DatePickerField Component ─────────────────────────────────
export function DatePickerField<TFieldValues extends FieldValues = FieldValues>({
  name,
  control,
  label,
  required,
  disabled,
  placeholder,
  className,
  helperText,
  onChange,
}: BaseFieldProps<TFieldValues>) {
  const {
    field,
    fieldState: { error },
  } = useController({ name, control });

  return (
    <FormField
      label={label}
      required={required}
      error={error?.message}
      helperText={helperText}
      className={className}
    >
      <Input
        {...field}
        type="date"
        disabled={disabled}
        placeholder={placeholder}
        value={field.value ?? ""}
        onChange={(e) => {
          field.onChange(e);
          onChange?.(e.target.value);
        }}
        className={cn(error && "border-destructive focus-visible:ring-destructive")}
      />
    </FormField>
  );
}

// ─── FormLayout helper components ──────────────────────────────
export function FormGrid({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("grid grid-cols-1 md:grid-cols-2 gap-4", className)}>{children}</div>;
}

export function FormActions({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("flex items-center justify-end gap-3 border-t border-border pt-4 mt-6", className)}>{children}</div>;
}
