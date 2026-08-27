"use client";

import { useState } from "react";
import { KeyRound, Plus, Trash2, ShieldCheck, Server, Lock, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useGetCredentialsQuery,
  useCreateCredentialMutation,
  useDeleteCredentialMutation,
  CredentialItem,
} from "../services/credentials-api";

export function CredentialsManager() {
  const { data: credentials = [], isLoading, isError, refetch } = useGetCredentialsQuery();
  const [createCredential, { isLoading: isCreating }] = useCreateCredentialMutation();
  const [deleteCredential, { isLoading: isDeleting }] = useDeleteCredentialMutation();

  const [isOpen, setIsOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState("");
  const [credentialType, setCredentialType] = useState<string>("ssh_password");
  const [username, setUsername] = useState("");
  const [secret, setSecret] = useState("");

  const handleOpen = () => {
    setName("");
    setCredentialType("ssh_password");
    setUsername("");
    setSecret("");
    setFormError(null);
    setIsOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError("Credential name is required.");
      return;
    }
    if (!username.trim() && credentialType !== "snmp_v2c") {
      setFormError("Username is required.");
      return;
    }
    if (!secret.trim()) {
      setFormError("Secret / Password / Community string is required.");
      return;
    }

    try {
      await createCredential({
        name: name.trim(),
        credential_type: credentialType,
        username: username.trim() || "public",
        secret: secret.trim(),
      }).unwrap();
      setIsOpen(false);
    } catch (err: any) {
      setFormError(err?.data?.detail || "Failed to create credential.");
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this credential?")) {
      try {
        await deleteCredential(id).unwrap();
      } catch (err: any) {
        alert(err?.data?.detail || "Failed to delete credential.");
      }
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case "ssh_password":
      case "ssh_key":
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">SSH</span>;
      case "winrm":
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">WinRM</span>;
      case "snmp_v2c":
      case "snmp_v3":
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">SNMP</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-muted text-muted-foreground">{type}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-xl bg-card border border-border">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-bold tracking-tight text-foreground">Discovery Credentials Vault</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            Manage SSH, WinRM, and SNMP authentication credentials used for automated network hardware collection.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} className="gap-1.5 text-xs">
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <Button onClick={handleOpen} size="sm" className="gap-1.5 text-xs font-semibold bg-primary text-white">
            <Plus className="h-4 w-4" />
            Add Credential
          </Button>
        </div>
      </div>

      {/* Content Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-muted-foreground animate-pulse">
            Loading credentials vault...
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-xs text-destructive flex items-center justify-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Failed to load credentials. Ensure you have administrative privileges (`servers.write`).
          </div>
        ) : credentials.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <ShieldCheck className="h-10 w-10 text-muted-foreground/40 mx-auto" />
            <h3 className="text-sm font-semibold text-foreground">No Credentials Configured</h3>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              Add SSH (Linux), WinRM (Windows), or SNMP credentials so full network inventory scans can authenticate and extract hardware specs.
            </p>
            <Button onClick={handleOpen} size="sm" className="gap-1.5 text-xs mt-2">
              <Plus className="h-3.5 w-3.5" />
              Add First Credential
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-muted/50 border-b border-border font-semibold text-muted-foreground">
                  <th className="p-3 pl-4">Name</th>
                  <th className="p-3">Protocol Type</th>
                  <th className="p-3">Username / Identity</th>
                  <th className="p-3">Vault Security</th>
                  <th className="p-3 text-right pr-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {credentials.map((cred: CredentialItem) => (
                  <tr key={cred.id} className="hover:bg-muted/20 transition-colors">
                    <td className="p-3 pl-4 font-semibold text-foreground flex items-center gap-2">
                      <Lock className="h-3.5 w-3.5 text-muted-foreground" />
                      {cred.name}
                    </td>
                    <td className="p-3">{getTypeBadge(cred.credential_type)}</td>
                    <td className="p-3 font-mono text-muted-foreground">{cred.username || "—"}</td>
                    <td className="p-3">
                      <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        AES-256 Encrypted
                      </span>
                    </td>
                    <td className="p-3 text-right pr-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(cred.id)}
                        disabled={isDeleting}
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        title="Delete Credential"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Credential Modal */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-md bg-card border-border">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <KeyRound className="h-4 w-4 text-primary" />
              Add Discovery Credential
            </DialogTitle>
            <DialogDescription className="text-xs">
              Credentials are stored in local encrypted vault storage and used during Full Scans.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 py-2">
            {formError && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {formError}
              </div>
            )}

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Credential Name</Label>
              <Input
                placeholder="e.g., Linux Production Cluster Admin"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Protocol / Credential Type</Label>
              <select
                value={credentialType}
                onChange={(e) => setCredentialType(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="ssh_password">SSH (Password) — Linux / Mac</option>
                <option value="ssh_key">SSH (Private Key) — Linux / Mac</option>
                <option value="winrm">WinRM — Windows Server / Desktop</option>
                <option value="snmp_v2c">SNMP v2c — Network Switches / Routers</option>
                <option value="snmp_v3">SNMP v3 — Secure Network Devices</option>
              </select>
            </div>

            {credentialType !== "snmp_v2c" && (
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Username / Account</Label>
                <Input
                  placeholder={credentialType === "winrm" ? "Administrator" : "root"}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="text-xs font-mono"
                />
              </div>
            )}

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">
                {credentialType === "ssh_key"
                  ? "Private Key Material (PEM)"
                  : credentialType.startsWith("snmp")
                  ? "Community String / Auth Key"
                  : "Password"}
              </Label>
              {credentialType === "ssh_key" ? (
                <textarea
                  rows={4}
                  placeholder="-----BEGIN RSA PRIVATE KEY-----..."
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  className="w-full rounded-md border border-input bg-background p-2 text-xs font-mono shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                />
              ) : (
                <Input
                  type="password"
                  placeholder="••••••••••••"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  className="text-xs"
                />
              )}
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsOpen(false)} className="text-xs">
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isCreating} className="text-xs font-semibold bg-primary text-white">
                {isCreating ? "Saving..." : "Save Credential"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
