"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAppDispatch } from "@/hooks/store-hooks";
import { setSession } from "@/store/auth-slice";
import { useLoginMutation, useVerifyMfaMutation } from "@/features/auth/services/auth-api";
import { loginSchema, mfaSchema, LoginInput, MfaInput } from "@/features/auth/schemas/auth-schemas";

export function LoginForm() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [login, { isLoading: isLoginLoading }] = useLoginMutation();
  const [verifyMfa, { isLoading: isMfaLoading }] = useVerifyMfaMutation();

  const [mfaChallengeId, setMfaChallengeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    register: registerLogin,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const {
    register: registerMfa,
    handleSubmit: handleMfaSubmit,
    formState: { errors: mfaErrors },
  } = useForm<MfaInput>({
    resolver: zodResolver(mfaSchema),
    defaultValues: { mfaCode: "" },
  });

  async function onLoginSubmit(data: LoginInput) {
    setError(null);
    try {
      const res = await login(data).unwrap();
      if (res.data.mfa_required) {
        setMfaChallengeId(res.data.mfa_challenge_id);
      } else {
        dispatch(
          setSession({
            accessToken: res.data.access_token,
            refreshToken: res.data.refresh_token,
            user: res.data.user,
          })
        );
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err?.data?.error?.message ?? err?.data?.detail?.message ?? "Login failed.");
    }
  }

  async function onMfaSubmit(data: MfaInput) {
    if (!mfaChallengeId) return;
    setError(null);
    try {
      const res = await verifyMfa({
        mfa_challenge_id: mfaChallengeId,
        code: data.mfaCode,
      }).unwrap();
      dispatch(
        setSession({
          accessToken: res.data.access_token,
          refreshToken: res.data.refresh_token,
          user: res.data.user,
        })
      );
      router.push("/inventory");
    } catch (err: any) {
      setError(err?.data?.error?.message ?? err?.data?.detail?.message ?? "MFA verification failed.");
    }
  }

  const loading = isLoginLoading || isMfaLoading;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>AI Infrastructure Copilot</CardTitle>
          <CardDescription>
            {mfaChallengeId ? "Enter your authenticator code" : "Sign in to your organization"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!mfaChallengeId ? (
            <form onSubmit={handleLoginSubmit(onLoginSubmit)} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  {...registerLogin("email")}
                  aria-invalid={!!loginErrors.email}
                />
                {loginErrors.email && (
                  <p className="text-xs text-destructive">{loginErrors.email.message}</p>
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  {...registerLogin("password")}
                  aria-invalid={!!loginErrors.password}
                />
                {loginErrors.password && (
                  <p className="text-xs text-destructive">{loginErrors.password.message}</p>
                )}
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading}>
                {isLoginLoading ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleMfaSubmit(onMfaSubmit)} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="mfaCode">6-digit code</Label>
                <Input
                  id="mfaCode"
                  autoFocus
                  maxLength={6}
                  {...registerMfa("mfaCode")}
                  aria-invalid={!!mfaErrors.mfaCode}
                />
                {mfaErrors.mfaCode && (
                  <p className="text-xs text-destructive">{mfaErrors.mfaCode.message}</p>
                )}
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading}>
                {isMfaLoading ? "Verifying..." : "Verify"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
