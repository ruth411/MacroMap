"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sidebar } from "@/components/chat/Sidebar";
import Link from "next/link";
import { Menu, X, LogOut, User } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  sendChatMessage,
  clearConversation,
  checkChatHealth,
  listSessions,
  createSession,
  getSession,
  deleteSession,
  type ChatHealthResponse,
  type SessionSummary,
} from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  questionType?: string | null;
}

export default function ChatPage() {
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth();

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmHealth, setLlmHealth] = useState<ChatHealthResponse | null>(null);

  // Session state (only for authenticated users)
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Guest session ID (temporary, for LLM context only)
  const [guestSessionId] = useState(() => `guest-${Date.now()}`);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check LLM health on mount
  useEffect(() => {
    checkChatHealth()
      .then(setLlmHealth)
      .catch(() => setLlmHealth(null));
  }, []);

  // Load sessions when authenticated
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      loadSessions();
    } else {
      setSessionsLoading(false);
    }
  }, [isAuthenticated, authLoading]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadSessions = async () => {
    if (!isAuthenticated) return;
    setSessionsLoading(true);
    try {
      const response = await listSessions();
      setSessions(response.sessions);
      if (response.sessions.length > 0 && !activeSessionId) {
        await handleSelectSession(response.sessions[0].id);
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    if (!isAuthenticated) return;
    setActiveSessionId(sessionId);
    setSidebarOpen(false);
    try {
      const sessionDetail = await getSession(sessionId);
      setMessages(
        sessionDetail.messages.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
          questionType: m.question_type,
        }))
      );
    } catch (err) {
      console.error("Failed to load session:", err);
      setMessages([]);
    }
  };

  const handleNewSession = async () => {
    if (!isAuthenticated) return;
    try {
      const session = await createSession();
      setSessions((prev) => [
        {
          id: session.id,
          title: session.title,
          created_at: session.created_at,
          updated_at: session.created_at,
          message_count: 0,
        },
        ...prev,
      ]);
      setActiveSessionId(session.id);
      setMessages([]);
      setSidebarOpen(false);
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!isAuthenticated) return;
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        if (remaining.length > 0) {
          await handleSelectSession(remaining[0].id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    let currentSessionId: string;

    if (isAuthenticated) {
      // Authenticated: create session if none active
      if (!activeSessionId) {
        try {
          const session = await createSession();
          setSessions((prev) => [
            {
              id: session.id,
              title: session.title,
              created_at: session.created_at,
              updated_at: session.created_at,
              message_count: 0,
            },
            ...prev,
          ]);
          currentSessionId = session.id;
          setActiveSessionId(session.id);
        } catch (err) {
          console.error("Failed to create session:", err);
          return;
        }
      } else {
        currentSessionId = activeSessionId;
      }
    } else {
      // Guest: use temporary session ID
      currentSessionId = guestSessionId;
    }

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage({
        message: input,
        session_id: currentSessionId,
        use_templates: true,
      });

      const assistantMessage: Message = {
        role: "assistant",
        content: response.response,
        questionType: response.question_type,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Refresh sessions for authenticated users
      if (isAuthenticated) {
        const sessionsResponse = await listSessions();
        setSessions(sessionsResponse.sessions);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to get response";
      setError(errorMessage);
      const errorAssistantMessage: Message = {
        role: "assistant",
        content: `Error: ${errorMessage}. Make sure the backend is running and the LLM provider is configured.`,
      };
      setMessages((prev) => [...prev, errorAssistantMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = async () => {
    const sessionId = isAuthenticated ? activeSessionId : guestSessionId;
    if (!sessionId) return;
    try {
      await clearConversation(sessionId);
      setMessages([]);
      setError(null);
    } catch (err) {
      console.error("Failed to clear conversation:", err);
    }
  };

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <p className="text-zinc-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="h-screen bg-zinc-50 dark:bg-zinc-950 flex overflow-hidden">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && isAuthenticated && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Only for authenticated users */}
      {isAuthenticated && (
        <div
          className={`fixed lg:relative inset-y-0 left-0 z-50 w-80 shrink-0 transform transition-transform lg:transform-none ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          }`}
        >
          <Sidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onNewSession={handleNewSession}
            onDeleteSession={handleDeleteSession}
            isLoading={sessionsLoading}
          />
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
          <div className="px-4 lg:px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isAuthenticated && (
                <button
                  className="lg:hidden p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg"
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                >
                  {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                </button>
              )}
              <Link href="/" className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
                MacroMap
              </Link>
            </div>
            <div className="flex items-center gap-3">
              {llmHealth && (
                <span
                  className={`hidden sm:inline text-sm px-3 py-1 rounded-full ${
                    llmHealth.healthy
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                  }`}
                >
                  {llmHealth.healthy ? `${llmHealth.provider}` : "Offline"}
                </span>
              )}
              {isAuthenticated ? (
                <div className="flex items-center gap-2">
                  <span className="hidden sm:inline text-sm text-zinc-600 dark:text-zinc-400">
                    {user?.email}
                  </span>
                  <Button variant="outline" size="sm" onClick={logout}>
                    <LogOut className="h-4 w-4 mr-1" />
                    Logout
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Link href="/login">
                    <Button variant="outline" size="sm">
                      Sign in
                    </Button>
                  </Link>
                  <Link href="/register">
                    <Button size="sm">Sign up</Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Guest banner */}
        {!isAuthenticated && (
          <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-4 py-2 text-center text-sm text-amber-800 dark:text-amber-200">
            You&apos;re using guest mode. Your chat won&apos;t be saved.{" "}
            <Link href="/register" className="underline font-medium">
              Sign up
            </Link>{" "}
            to save your conversations.
          </div>
        )}

        <div className="flex-1 flex overflow-hidden bg-zinc-100 dark:bg-zinc-950">
          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col min-w-0 p-4 lg:p-6">
            <Card className="flex-1 flex flex-col overflow-hidden border-2 border-zinc-200 dark:border-zinc-800 shadow-lg">
              <CardHeader className="border-b-2 border-zinc-200 dark:border-zinc-700 flex flex-row items-center justify-between py-4 px-5 bg-white dark:bg-zinc-900">
                <div>
                  <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">
                    {isAuthenticated ? "Current Conversation" : "Guest Chat"}
                  </p>
                  <CardTitle className="text-lg font-semibold">
                    {isAuthenticated
                      ? sessions.find((s) => s.id === activeSessionId)?.title || "New Chat"
                      : "Temporary Chat"}
                  </CardTitle>
                </div>
                {messages.length > 0 && (
                  <Button variant="outline" size="sm" onClick={handleClearChat}>
                    Clear Chat
                  </Button>
                )}
              </CardHeader>
              <CardContent className="flex-1 p-0 overflow-hidden">
                <ScrollArea className="h-full p-4 lg:p-6">
                  {messages.length === 0 ? (
                    <div className="text-center text-zinc-500 py-12">
                      <p className="text-xl mb-4 font-medium">Welcome to MacroMap</p>
                      <p className="mb-4">Ask questions about financial concepts, ratios, valuation, and more.</p>
                      <div className="text-sm space-y-2">
                        <p className="font-medium">Try asking:</p>
                        <p className="text-zinc-400">&quot;What is the P/E ratio and how do I interpret it?&quot;</p>
                        <p className="text-zinc-400">&quot;Explain the difference between EBITDA and Net Income&quot;</p>
                        <p className="text-zinc-400">&quot;How does the Federal Reserve affect stock prices?&quot;</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {messages.map((message, i) => (
                        <div
                          key={i}
                          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`max-w-[85%] rounded-xl px-4 py-3 ${
                              message.role === "user"
                                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                                : "bg-zinc-100 dark:bg-zinc-800"
                            }`}
                          >
                            <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                            {message.questionType && message.role === "assistant" && (
                              <div className="mt-2 text-xs opacity-60">Category: {message.questionType}</div>
                            )}
                          </div>
                        </div>
                      ))}
                      {loading && (
                        <div className="flex justify-start">
                          <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg px-4 py-3">
                            <span className="animate-pulse text-sm">Analyzing your question...</span>
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
              <div className="p-4 border-t">
                {error && <div className="mb-2 text-sm text-red-600 dark:text-red-400">{error}</div>}
                <form onSubmit={handleSubmit} className="flex gap-3">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask a financial question..."
                    disabled={loading}
                    className="flex-1 h-11"
                  />
                  <Button type="submit" disabled={loading || !input.trim()} className="h-11 px-6">
                    {loading ? "..." : "Send"}
                  </Button>
                </form>
              </div>
            </Card>
          </div>

          {/* Info Panel - Hidden on smaller screens */}
          <div className="hidden xl:block w-80 p-4 lg:p-6 pl-0">
            <Card className="h-full">
              <CardHeader className="border-b py-3 px-4">
                <CardTitle className="text-base">About MacroMap</CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                <div>
                  <h3 className="font-medium text-sm mb-1">Expertise Areas</h3>
                  <ul className="text-sm text-zinc-600 dark:text-zinc-400 space-y-1">
                    <li>Financial Statement Analysis</li>
                    <li>Valuation Methods (DCF, Comps)</li>
                    <li>Financial Ratios & Metrics</li>
                    <li>Capital Markets</li>
                    <li>Macroeconomics</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium text-sm mb-1">Status</h3>
                  {llmHealth ? (
                    <div className="text-sm">
                      <p className={llmHealth.healthy ? "text-green-600" : "text-red-600"}>
                        {llmHealth.healthy ? "Connected" : "Disconnected"}
                      </p>
                      {llmHealth.healthy && (
                        <>
                          <p className="text-zinc-500">Provider: {llmHealth.provider}</p>
                          <p className="text-zinc-500">Model: {llmHealth.model}</p>
                        </>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-500">Checking connection...</p>
                  )}
                </div>
                {!isAuthenticated && (
                  <div className="pt-4 border-t">
                    <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">
                      Sign up to save your chat history and access it from any device.
                    </p>
                    <Link href="/register">
                      <Button className="w-full" size="sm">
                        <User className="h-4 w-4 mr-2" />
                        Create Account
                      </Button>
                    </Link>
                  </div>
                )}
                <div className="text-xs text-zinc-400 pt-4 border-t">
                  <p>Note: This is for educational purposes only. Not financial advice.</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
