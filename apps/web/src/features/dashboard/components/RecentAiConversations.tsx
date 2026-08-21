import Link from "next/link";
import type { AiConversation } from "@ai-infra-copilot/shared-types";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function RecentAiConversations({
  conversations,
  isLoading,
  isError,
}: {
  conversations: AiConversation[];
  isLoading: boolean;
  isError: boolean;
}) {
  const recent = conversations.slice(0, 4);
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Recent AI Conversations</CardTitle>
        <Link href="/ai-chat" className="text-xs font-semibold text-primary">
          Open chat →
        </Link>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {isError && <p className="text-sm text-muted-foreground">Conversations aren&apos;t available.</p>}
        {!isLoading && !isError && recent.length === 0 && (
          <p className="text-sm text-muted-foreground">No conversations yet.</p>
        )}
        {recent.map((conversation) => (
          <div
            key={conversation.id}
            className="flex items-start gap-2.5 border-t border-border pt-2 first:border-t-0 first:pt-0"
          >
            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-semibold">{conversation.title ?? "Untitled conversation"}</div>
              <div className="text-[11px] text-muted-foreground">{conversation.status}</div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
