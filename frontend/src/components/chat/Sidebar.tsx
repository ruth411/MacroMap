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
    <div className="flex flex-col h-full w-full bg-zinc-900 border-r-4 border-zinc-600 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b-2 border-zinc-600 bg-zinc-950 shrink-0">
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
      <div className="flex-1 overflow-y-auto bg-zinc-900">
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
                  className={`relative flex items-center gap-3 px-3 py-3 rounded-lg cursor-pointer transition-all border-2 ${
                    activeSessionId === session.id
                      ? "bg-zinc-700 border-blue-500 text-white shadow-lg"
                      : "bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-750 hover:border-zinc-600"
                  }`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <MessageSquare className={`h-4 w-4 shrink-0 ${
                    activeSessionId === session.id ? "text-blue-400" : "text-zinc-500"
                  }`} />
                  <div className="flex-1 min-w-0 pr-8">
                    <p className="text-sm font-medium truncate">{session.title}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">
                      {formatRelativeTime(session.updated_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-md bg-zinc-700 hover:bg-red-600 text-zinc-400 hover:text-white transition-all border border-zinc-600 hover:border-red-500"
                    title="Delete session"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
