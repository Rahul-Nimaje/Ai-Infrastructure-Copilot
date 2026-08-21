"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Script, Server } from "@ai-infra-copilot/shared-types";
import { Terminal, Cpu, Play } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import {
  PageHeader,
  TextField,
  FormActions,
} from "@/components/common";

import { usePowerShell, useInventory } from "@/hooks";
import { powerShellSchema, type PowerShellFormValues } from "@/schemas";
import type { PendingTasksMap } from "../types";
import { RISK_BADGE_VARIANTS } from "../utils/constants";

function riskVariant(risk: string): "success" | "warning" | "destructive" | "default" {
  return (RISK_BADGE_VARIANTS as any)[risk] || "default";
}

export function PowerShellGenerator() {
  const [targetServerId, setTargetServerId] = useState<string>("");
  const [pendingTaskByScript, setPendingTaskByScript] = useState<PendingTasksMap>({});


  // Use custom PowerShell hooks
  const { scripts, generateScript, executeScript } = usePowerShell();

  // Reuse inventory servers query
  const { servers, isServersLoading } = useInventory();

  // RHF setup
  const { control, handleSubmit, reset } = useForm<PowerShellFormValues>({
    resolver: zodResolver(powerShellSchema),
    defaultValues: {
      description: "",
    },
  });

  const onSubmit = (values: PowerShellFormValues) => {
    generateScript.mutate(
      { description: values.description },
      {
        onSuccess: () => {
          reset();
        },
      }
    );
  };

  const handleExecute = (scriptId: string) => {
    if (!targetServerId) return;

    executeScript.mutate(
      { scriptId, targetServerId },
      {
        onSuccess: (res) => {
          setPendingTaskByScript((prev) => ({
            ...prev,
            [scriptId]: { taskId: res.data.task_id, status: res.data.status },
          }));
        },
      }
    );
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="PowerShell Generator"
        description="Describe administration tasks to generate, review, and request execution of PowerShell scripts."
      />

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2 border-border bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-bold text-muted-foreground uppercase tracking-wider">
              Describe what you want to do
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <TextField
                name="description"
                control={control}
                label="Task Prompt"
                required
                placeholder="e.g. Restart the W3SVC IIS service and report its status"
                disabled={generateScript.isPending}
              />
              <FormActions className="mt-2 border-t-0 pt-0">
                <Button
                  type="submit"
                  disabled={generateScript.isPending}
                  className="bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95 text-white shadow-md font-semibold"
                >
                  {generateScript.isPending ? "Generating..." : "Generate Script"}
                </Button>
              </FormActions>
            </form>
          </CardContent>
        </Card>

        <Card className="border-border bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <Cpu className="h-4 w-4 text-primary" />
              Target Server for Execution
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Select Windows Host</Label>
              <select
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                value={targetServerId}
                onChange={(e) => setTargetServerId(e.target.value)}
                disabled={isServersLoading}
              >
                <option value="">Choose server...</option>
                {servers?.map((s: Server) => (
                  <option key={s.id} value={s.id}>
                    {s.hostname} ({s.ip_address || "no IP"})
                  </option>
                ))}
              </select>
            </div>
            {!targetServerId && (
              <p className="text-xs text-muted-foreground italic">
                You must specify a target server before requesting execution of generated scripts.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <h2 className="text-sm font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <Terminal className="h-4 w-4 text-primary" />
          Generated Scripts Directory
        </h2>

        {scripts.length === 0 ? (
          <Card className="border border-dashed border-border/80 p-8 flex flex-col items-center justify-center text-center">
            <Terminal className="h-8 w-8 text-muted-foreground/60 mb-2" />
            <h3 className="text-sm font-bold">No scripts generated yet</h3>
            <p className="text-xs text-muted-foreground max-w-xs mt-1">
              Submit a prompt above to generate a new PowerShell task script.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {scripts.map((script: Script) => {
              const pending = pendingTaskByScript[script.id];
              return (
                <Card key={script.id} className="border border-border/60 hover:border-border transition-colors">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base font-semibold">{script.name}</CardTitle>
                      <Badge variant={riskVariant(script.risk_level)} className="capitalize">
                        {script.risk_level} risk
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <pre className="overflow-x-auto rounded-lg bg-muted/80 border border-border/40 p-4 text-xs font-mono text-foreground leading-relaxed">
                      {script.content}
                    </pre>

                    {pending ? (
                      <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 text-xs text-muted-foreground flex flex-col gap-1">
                        <span>
                          Task ID: <strong className="font-mono text-primary">{pending.taskId}</strong> — Status:{" "}
                          <strong className="capitalize text-foreground">{pending.status}</strong>.
                        </span>
                        <span>Approve this execution request from the Tasks queue in AI Chat to proceed.</span>
                      </div>
                    ) : (
                      <div className="flex justify-end mt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1.5 text-xs font-bold"
                          disabled={!targetServerId || executeScript.isPending}
                          onClick={() => handleExecute(script.id)}
                        >
                          <Play className="h-3.5 w-3.5" />
                          Request Execution
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
