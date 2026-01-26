"use client";

import { SessionSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Trash2, MessageSquare, History } from "lucide-react";

interface SidebarProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  isLoading: boolean;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  isLoading,
}: SidebarProps) {
  return (
    <div className="flex flex-col h-full bg-zinc-900 border-r-2 border-zinc-700">
      {/* Header */}
      <div className="p-4 border-b-2 border-zinc-700 bg-zinc-950">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wide mb-3 flex items-center gap-2">
          <History className="h-4 w-4" />
          Chat History
        </h2>
        <Button
          onClick={onNewSession}
          className="w-full justify-center gap-2 bg-zinc-100 text-zinc-900 hover:bg-white"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Sessions List */}
      <ScrollArea className="flex-1 bg-zinc-900">
        <div className="p-3">
          {isLoading ? (
            <div className="p-4 text-center text-zinc-500 text-sm">
              Loading sessions...
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-zinc-500 text-sm">
              No conversations yet
            </div>
          ) : (
            <div className="space-y-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group relative flex items-start gap-3 px-3 py-3 rounded-lg cursor-pointer transition-all border ${
                    activeSessionId === session.id
                      ? "bg-zinc-800 border-zinc-600 text-white shadow-md"
                      : "bg-zinc-850 border-zinc-800 text-zinc-400 hover:bg-zinc-800 hover:border-zinc-700 hover:text-zinc-200"
                  }`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <MessageSquare className={`h-4 w-4 mt-0.5 shrink-0 ${
                    activeSessionId === session.id ? "text-blue-400" : "text-zinc-500"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate leading-tight">{session.title}</p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {formatRelativeTime(session.updated_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-zinc-700 text-zinc-500 hover:text-red-400 transition-all absolute right-2 top-2"
                    title="Delete session"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
