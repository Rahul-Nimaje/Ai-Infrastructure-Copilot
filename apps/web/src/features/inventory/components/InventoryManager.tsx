"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Server } from "@ai-infra-copilot/shared-types";
import { Server as ServerIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";

import {
  PageHeader,
  DataTable,
  StatusBadge,
  TextField,
  NumberField,
  CheckboxField,
  FormActions,
} from "@/components/common";

import { useInventory } from "@/hooks";
import { registerServerSchema, type RegisterServerFormValues } from "@/schemas";
import type { ScanCandidate } from "../types";
import {
  DEFAULT_WINRM_SSL_PORT,
  DEFAULT_WINRM_HTTP_PORT,
  WINRM_PORT_DEFAULTS,
} from "../utils/constants";


export function InventoryManager() {
  const {
    servers,
    isServersLoading,
    registerServer,
    detachServer,
    scanNetwork,
  } = useInventory();

  const [showForm, setShowForm] = useState(false);
  const [showScan, setShowScan] = useState(false);
  const [cidr, setCidr] = useState("");
  const [scanResults, setScanResults] = useState<ScanCandidate[] | null>(null);
  const [serverToDetach, setServerToDetach] = useState<Server | null>(null);

  // RHF Setup for registering server
  const { control, handleSubmit, reset, watch, setValue } = useForm<RegisterServerFormValues>({
    resolver: zodResolver(registerServerSchema),
    defaultValues: {
      hostname: "",
      ipAddress: "",
      osVersion: "",
      username: "",
      secret: "",
      winrmUseSsl: true,
      winrmPort: DEFAULT_WINRM_SSL_PORT,
    },
  });

  const winrmUseSsl = watch("winrmUseSsl");
  const winrmPort = watch("winrmPort");

  // Sync WinRM port default value on SSL toggle if it is one of the standard defaults
  useEffect(() => {
    const knownDefaults = WINRM_PORT_DEFAULTS as unknown as string[];
    if (knownDefaults.includes(winrmPort)) {
      setValue("winrmPort", winrmUseSsl ? DEFAULT_WINRM_SSL_PORT : DEFAULT_WINRM_HTTP_PORT);
    }
  }, [winrmUseSsl, setValue, winrmPort]);

  function applyCandidate(candidate: ScanCandidate) {
    reset({
      hostname: candidate.hostname_guess,
      ipAddress: candidate.ip_address,
      osVersion: "",
      username: "",
      secret: "",
      winrmUseSsl: true,
      winrmPort: DEFAULT_WINRM_SSL_PORT,
    });
    setShowForm(true);
  }

  const handleScanSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cidr) return;
    scanNetwork.mutate(cidr, {
      onSuccess: (result) => {
        setScanResults(result.data);
      },
    });
  };

  const onRegisterSubmit = (values: RegisterServerFormValues) => {
    registerServer.mutate(values, {
      onSuccess: () => {
        setShowForm(false);
        reset();
      },
    });
  };

  const columns = [
    {
      key: "hostname",
      header: "Hostname",
      render: (server: Server) => <span className="font-semibold text-foreground">{server.hostname}</span>,
    },
    {
      key: "os_type",
      header: "OS",
      render: (server: Server) => <span className="capitalize">{server.os_type} {server.os_version}</span>,
    },
    {
      key: "environment",
      header: "Environment",
      render: (server: Server) => <span className="capitalize text-muted-foreground">{server.environment}</span>,
    },
    {
      key: "health_status",
      header: "Health",
      render: (server: Server) => (
        <StatusBadge
          status={
            server.health_status === "healthy"
              ? "active"
              : server.health_status === "critical"
              ? "failed"
              : "warning"
          }
        />
      ),
    },
    {
      key: "actions",
      header: "",
      headerClassName: "text-right",
      className: "text-right",
      render: (server: Server) => (
        <div className="flex justify-end gap-3">
          <Link
            className="text-primary hover:underline text-xs font-semibold"
            href={`/event-log-analyzer?serverId=${server.id}&hostname=${server.hostname}`}
          >
            View events
          </Link>
          <button
            type="button"
            className="text-destructive hover:underline text-xs font-semibold disabled:opacity-50"
            disabled={detachServer.isPending}
            onClick={() => setServerToDetach(server)}
          >
            Detach
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Infrastructure Inventory"
        description="Register and track environment endpoints, virtual hosts, and inventory metrics."
      >
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowScan((v) => !v)} className="text-xs font-semibold">
            {showScan ? "Cancel" : "Scan Device"}
          </Button>
          <Button size="sm" onClick={() => setShowForm((v) => !v)} className="bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-xs font-semibold text-white shadow-sm">
            {showForm ? "Cancel" : "Register Windows Server"}
          </Button>
        </div>
      </PageHeader>

      {showScan && (
        <Card className="border border-border/60 shadow-md">
          <CardHeader>
            <CardTitle>Scan Network for Devices</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <form className="flex items-end gap-4" onSubmit={handleScanSubmit}>
              <div className="flex flex-col gap-1.5 max-w-xs w-full">
                <Label>CIDR range</Label>
                <Input
                  required
                  placeholder="10.20.4.0/24"
                  value={cidr}
                  onChange={(e) => setCidr(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={scanNetwork.isPending} className="bg-primary text-white font-semibold">
                {scanNetwork.isPending ? "Scanning..." : "Scan"}
              </Button>
            </form>

            {scanNetwork.isPending && <p className="text-sm text-muted-foreground animate-pulse">Probing hosts...</p>}

            {scanResults && !scanNetwork.isPending && (
              scanResults.length === 0 ? (
                <p className="text-sm text-muted-foreground">No devices found in that range.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="py-2">Hostname</th>
                      <th>IP address</th>
                      <th>Likely OS</th>
                      <th>Open ports</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {scanResults.map((candidate) => (
                      <tr key={candidate.ip_address} className="border-b border-border">
                        <td className="py-2 font-medium">{candidate.hostname_guess}</td>
                        <td>{candidate.ip_address}</td>
                        <td>{candidate.likely_os_type}</td>
                        <td>{candidate.open_ports.map((p) => p.service).join(", ")}</td>
                        <td className="text-right">
                          <button
                            type="button"
                            className="text-primary underline"
                            onClick={() => applyCandidate(candidate)}
                          >
                            Use candidate
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            )}
          </CardContent>
        </Card>
      )}

      {showForm && (
        <Card className="border border-border/60 shadow-md">
          <CardHeader>
            <CardTitle>Register a Windows Server</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid grid-cols-2 gap-4" onSubmit={handleSubmit(onRegisterSubmit)}>
              <TextField
                name="hostname"
                control={control}
                label="Hostname"
                required
                placeholder="e.g. WIN-SERV01"
                disabled={registerServer.isPending}
              />
              <TextField
                name="ipAddress"
                control={control}
                label="IP Address (optional)"
                placeholder="e.g. 192.168.1.15"
                disabled={registerServer.isPending}
              />
              <TextField
                name="osVersion"
                control={control}
                label="OS Version (optional)"
                placeholder="e.g. Windows Server 2022"
                disabled={registerServer.isPending}
              />
              <div />
              <TextField
                name="username"
                control={control}
                label="WinRM Username"
                required
                placeholder="Administrator"
                disabled={registerServer.isPending}
              />
              <TextField
                name="secret"
                control={control}
                label="WinRM Password"
                required
                type="password"
                placeholder="Password"
                disabled={registerServer.isPending}
              />
              <CheckboxField
                name="winrmUseSsl"
                control={control}
                label="Use HTTPS (requires a cert on the target)"
                disabled={registerServer.isPending}
                className="pt-6"
              />
              <NumberField
                name="winrmPort"
                control={control}
                label="WinRM Port"
                required
                disabled={registerServer.isPending}
              />
              <div className="col-span-2">
                <FormActions className="mt-4 border-t-0 pt-0">
                  <Button type="submit" disabled={registerServer.isPending} className="bg-primary text-white font-semibold shadow-sm">
                    {registerServer.isPending ? "Registering..." : "Register"}
                  </Button>
                </FormActions>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <DataTable
        columns={columns}
        data={servers}
        loading={isServersLoading}
        loadingMessage="Loading registered servers..."
        emptyIcon={ServerIcon}
        emptyTitle="No servers registered yet"
        emptyDescription="Register a Windows Server or perform discovery scans to populate your inventory."
        rowKey={(server: Server) => server.id}
        paginationLabel="servers"
      />

      <ConfirmationDialog
        isOpen={!!serverToDetach}
        onClose={() => setServerToDetach(null)}
        onConfirm={() => {
          if (serverToDetach) detachServer.mutate(serverToDetach.id);
        }}
        title="Detach Server"
        description={`Are you sure you want to detach "${serverToDetach?.hostname}"? This removes it from inventory.`}
        confirmText="Detach"
        variant="destructive"
        isLoading={detachServer.isPending}
      />
    </div>
  );
}
