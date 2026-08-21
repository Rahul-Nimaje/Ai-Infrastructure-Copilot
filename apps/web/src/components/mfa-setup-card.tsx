"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiFetch, ApiClientError } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";

/**
 * Roadmap Phase 1 exit criteria (docs/15-roadmap.md Section 3) require MFA
 * to be part of the authenticate flow, not just an API capability — this is
 * the minimal enrollment UI for that. No QR code rendering (would need an
 * extra dependency with no Phase 1 exit criterion behind it): the secret is
 * shown as manual-entry text, which every TOTP authenticator app supports.
 */
export function MfaSetupCard() {
  const user = useAuthStore((s) => s.user);
  const setSession = useAuthStore((s) => s.setSession);
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshToken = useAuthStore((s) => s.refreshToken);

  const [secret, setSecret] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const enable = useMutation({
    mutationFn: () => apiFetch<{ data: { secret: string; provisioning_uri: string } }>("/api/v1/auth/mfa/enable", { method: "POST", body: {} }),
    onSuccess: (res) => setSecret(res.data.secret),
  });

  const confirm = useMutation({
    mutationFn: () => apiFetch<{ data: { mfa_enabled: boolean } }>("/api/v1/auth/mfa/confirm", { method: "POST", body: { code } }),
    onSuccess: () => {
      if (user && accessToken && refreshToken) {
        setSession({ accessToken, refreshToken, user: { ...user, mfa_enabled: true } });
      }
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "Invalid code."),
  });

  if (!user || user.mfa_enabled || dismissed) return null;

  return (
    <Card className="mb-6 border-amber-300">
      <CardHeader>
        <CardTitle>Set up multi-factor authentication</CardTitle>
        <CardDescription>Required before this account is fully provisioned.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!secret ? (
          <Button size="sm" onClick={() => enable.mutate()} disabled={enable.isPending}>
            {enable.isPending ? "Generating..." : "Generate MFA secret"}
          </Button>
        ) : (
          <>
            <p className="text-sm">
              Add this key to your authenticator app (manual entry): <code className="rounded bg-muted px-1">{secret}</code>
            </p>
            <div className="flex gap-2">
              <Input placeholder="6-digit code" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} />
              <Button size="sm" onClick={() => confirm.mutate()} disabled={confirm.isPending}>
                Confirm
              </Button>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </>
        )}
        <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>
          Skip for now
        </Button>
      </CardContent>
    </Card>
  );
}
