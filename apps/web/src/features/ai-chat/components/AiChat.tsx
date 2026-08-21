"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Terminal, ShieldAlert, BadgeCheck, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { API_BASE_URL, getAccessToken } from "@/lib/api-client";
import { PageHeader, MarkdownContent } from "@/components/common";
import { useAiChat } from "@/hooks";
import type { ChatMessage, ProposedAction } from "../types";
import { PROPOSALS_RISK_VARIANTS } from "../utils/constants";


import { SourceCitations } from "@/features/knowledge-base/components/SourceCitations";

export function AiChat() {

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [proposals, setProposals] = useState<Record<string, ProposedAction>>({});
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Hook-driven conversation & tasks mutations
  const { createConversation, approveTask, rejectTask } = useAiChat();

  // Confirmation dialog state for approve/reject of proposed operation tasks
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    taskId: string;
    action: "approve" | "reject";
  }>({ isOpen: false, taskId: "", action: "approve" });

  useEffect(() => {
    if (!conversationId) {
      createConversation.mutate(undefined, {
        onSuccess: (res) => {
          setConversationId(res.data.id);
        },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, proposals]);

  const handleApprove = (taskId: string) => {
    approveTask.mutate(taskId, {
      onSuccess: () => {
        setProposals((prev) => ({
          ...prev,
          [taskId]: { ...prev[taskId], status: "approved" },
        }));
      },
    });
  };

  const handleReject = (taskId: string) => {
    rejectTask.mutate(taskId, {
      onSuccess: () => {
        setProposals((prev) => ({
          ...prev,
          [taskId]: { ...prev[taskId], status: "rejected" },
        }));
      },
    });
  };

  const handleConfirmAction = () => {
    if (confirmDialog.action === "approve") {
      handleApprove(confirmDialog.taskId);
    } else {
      handleReject(confirmDialog.taskId);
    }
  };

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!conversationId || !input.trim() || streaming) return;

    const content = input;
    setInput("");
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content }]);
    setStreaming(true);

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "" }]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/ai/conversations/${conversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getAccessToken()}` },
        body: JSON.stringify({ content }),
      });
      const reader = response.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const raw = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          boundary = buffer.indexOf("\n\n");

          const eventMatch = raw.match(/^event: (.+)$/m);
          const dataMatch = raw.match(/^data: (.+)$/m);
          if (!eventMatch || !dataMatch) continue;
          const eventType = eventMatch[1];
          const data = JSON.parse(dataMatch[1]);

          if (eventType === "agent_step") {
            setMessages((prev) => [
              ...prev,
              { id: crypto.randomUUID(), role: "agent_step", content: `${data.stage}: ${data.detail}` },
            ]);
          } else if (eventType === "rag_sources") {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, sources: data.sources } : m))
            );
          } else if (eventType === "token") {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + data.delta } : m))
            );
          } else if (eventType === "task_created") {
            setProposals((prev) => ({
              ...prev,
              [data.task_id]: {
                taskId: data.task_id,
                summary: data.summary,
                riskLevel: data.risk_level,
                explanation: data.explanation,
                status: data.status,
              },
            }));
          } else if (eventType === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: data.message ?? "Something went wrong." } : m
              )
            );
          }

        }
      }
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col gap-4">
      <PageHeader
        title="AI Automation Copilot"
        description="Interact with the antigravity AI orchestrator to query inventory status, generate playbooks, and run execution tasks."
      />

      <div className="flex-1 overflow-y-auto rounded-xl border border-border/60 bg-card/40 backdrop-blur-md p-4 flex flex-col gap-4 shadow-inner">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto">
            <Terminal className="h-10 w-10 text-primary mb-3 animate-pulse" />
            <h3 className="text-base font-bold">Start a conversation</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Ask about system performance, request server logs, or ask the Copilot to run diagnosis scripts.
            </p>
          </div>
        )}

        <div className="flex flex-col gap-4">
          {messages.map((m) => {
            if (m.role === "agent_step") {
              return (
                <div key={m.id} className="text-xs text-muted-foreground/80 font-mono pl-4 border-l border-primary/20 py-1">
                  {m.content}
                </div>
              );
            }
            return (
              <div key={m.id} className={m.role === "user" ? "self-end max-w-[80%]" : "self-start max-w-[80%]"}>

                <div
                  className={`rounded-xl px-4 py-3 text-sm shadow-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground font-medium rounded-tr-none"
                      : "bg-muted/70 text-foreground border border-border/30 rounded-tl-none"
                  }`}
                >
                  {m.content ? (
                    m.role === "assistant" ? (
                      <MarkdownContent content={m.content} />
                    ) : (
                      m.content
                    )
                  ) : streaming ? (
                    <span className="animate-pulse">Typing...</span>
                  ) : (
                    ""
                  )}
                  {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                    <SourceCitations sources={m.sources} />
                  )}
                </div>
              </div>

            );
          })}

          {Object.values(proposals).map((proposal) => (
            <Card key={proposal.taskId} className="max-w-lg border-primary/20 shadow-md">
              <CardContent className="flex flex-col gap-3 pt-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldAlert className="h-4 w-4" />
                    Proposed Operation Task
                  </span>
                  <Badge
                    variant={(PROPOSALS_RISK_VARIANTS as any)[proposal.riskLevel] || "warning"}
                    className="capitalize text-[10px] font-bold"
                  >
                    {proposal.riskLevel} risk
                  </Badge>
                </div>
                <h4 className="text-sm font-semibold text-foreground">{proposal.summary}</h4>
                {proposal.explanation && <p className="text-xs text-muted-foreground">{proposal.explanation}</p>}

                {proposal.status === "pending_approval" ? (
                  <div className="flex gap-2 mt-2 pt-2 border-t border-border/40">
                    <Button
                      size="sm"
                      className="text-xs font-bold shadow-sm bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/95 hover:to-indigo-600/95"
                      disabled={approveTask.isPending}
                      onClick={() =>
                        setConfirmDialog({ isOpen: true, taskId: proposal.taskId, action: "approve" })
                      }
                    >
                      Approve &amp; Run
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs font-bold"
                      disabled={rejectTask.isPending}
                      onClick={() =>
                        setConfirmDialog({ isOpen: true, taskId: proposal.taskId, action: "reject" })
                      }
                    >
                      Reject
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-xs font-semibold mt-2 pt-2 border-t border-border/40">
                    {proposal.status === "approved" ? (
                      <>
                        <BadgeCheck className="h-4 w-4 text-emerald-500" />
                        <span className="text-emerald-600">Approved and executed.</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-4 w-4 text-destructive" />
                        <span className="text-destructive">Rejected by operator.</span>
                      </>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <form className="flex gap-2 items-center" onSubmit={sendMessage}>
        <Input
          placeholder="Ask about a server, e.g. Why is IIS service running slow on win-prod-02?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming || !conversationId}
          className="h-11 rounded-xl bg-card border-border/60 shadow-sm"
        />
        <Button
          type="submit"
          disabled={streaming || !conversationId}
          className="h-11 w-11 rounded-xl bg-primary hover:bg-primary/95 text-primary-foreground shadow-sm flex items-center justify-center shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </form>

      <ConfirmationDialog
        isOpen={confirmDialog.isOpen}
        onClose={() => setConfirmDialog((prev) => ({ ...prev, isOpen: false }))}
        onConfirm={handleConfirmAction}
        title={confirmDialog.action === "approve" ? "Approve & Run Task" : "Reject Task"}
        description={
          confirmDialog.action === "approve"
            ? "This will execute the proposed operation on the target server. This action cannot be undone."
            : "This will reject the proposed operation. The task will not be executed."
        }
        confirmText={confirmDialog.action === "approve" ? "Approve & Run" : "Reject Task"}
        variant={confirmDialog.action === "approve" ? "destructive" : "warning"}
        isLoading={approveTask.isPending || rejectTask.isPending}
      />
    </div>
  );
}
