import { CredentialsManager } from "@/features/credentials/components/CredentialsManager";

export const metadata = {
  title: "Settings & Credentials | AI Infra Copilot",
  description: "Manage discovery credentials vault and system settings",
};

export default function SettingsPage() {
  return (
    <div className="container mx-auto p-6 space-y-6 max-w-7xl">
      <CredentialsManager />
    </div>
  );
}
