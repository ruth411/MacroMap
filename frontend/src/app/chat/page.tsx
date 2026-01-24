"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import Link from "next/link";
import { sendChatMessage, clearConversation, checkChatHealth, type ChatHealthResponse } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  questionType?: string | null;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmHealth, setLlmHealth] = useState<ChatHealthResponse | null>(null);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check LLM health on mount
  useEffect(() => {
    checkChatHealth()
      .then(setLlmHealth)
      .catch(() => setLlmHealth(null));
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage({
        message: input,
        session_id: sessionId,
        use_templates: true,
      });

      const assistantMessage: Message = {
        role: "assistant",
        content: response.response,
        questionType: response.question_type,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to get response";
      setError(errorMessage);
      // Add error message to chat
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
    try {
      await clearConversation(sessionId);
      setMessages([]);
      setError(null);
    } catch (err) {
      console.error("Failed to clear conversation:", err);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
            MacroMap
          </Link>
          <div className="flex items-center gap-4">
            {llmHealth && (
              <span className={`text-xs px-2 py-1 rounded ${llmHealth.healthy ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {llmHealth.healthy ? `${llmHealth.provider}: ${llmHealth.model}` : 'LLM Offline'}
              </span>
            )}
            <span className="text-sm text-zinc-500">Financial Analyst Copilot</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6 max-w-5xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-140px)]">
          {/* Main Chat Area */}
          <div className="lg:col-span-2 flex flex-col">
            <Card className="flex-1 flex flex-col">
              <CardHeader className="border-b flex flex-row items-center justify-between">
                <CardTitle className="text-lg">Financial Analysis Chat</CardTitle>
                {messages.length > 0 && (
                  <Button variant="outline" size="sm" onClick={handleClearChat}>
                    Clear Chat
                  </Button>
                )}
              </CardHeader>
              <CardContent className="flex-1 p-0">
                <ScrollArea className="h-[calc(100vh-340px)] p-4">
                  {messages.length === 0 ? (
                    <div className="text-center text-zinc-500 py-12">
                      <p className="text-lg mb-4">Welcome to MacroMap</p>
                      <p className="mb-4">Ask questions about financial concepts, ratios, valuation, and more.</p>
                      <div className="text-sm space-y-2">
                        <p className="font-medium">Try asking:</p>
                        <p>&quot;What is the P/E ratio and how do I interpret it?&quot;</p>
                        <p>&quot;Explain the difference between EBITDA and Net Income&quot;</p>
                        <p>&quot;How does the Federal Reserve affect stock prices?&quot;</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {messages.map((message, i) => (
                        <div
                          key={i}
                          className={`flex ${
                            message.role === "user" ? "justify-end" : "justify-start"
                          }`}
                        >
                          <div
                            className={`max-w-[85%] rounded-lg px-4 py-3 ${
                              message.role === "user"
                                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                                : "bg-zinc-100 dark:bg-zinc-800"
                            }`}
                          >
                            <div className="whitespace-pre-wrap">{message.content}</div>
                            {message.questionType && message.role === "assistant" && (
                              <div className="mt-2 text-xs opacity-60">
                                Category: {message.questionType}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                      {loading && (
                        <div className="flex justify-start">
                          <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg px-4 py-3">
                            <span className="animate-pulse">Analyzing your question...</span>
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
              <div className="p-4 border-t">
                {error && (
                  <div className="mb-2 text-sm text-red-600 dark:text-red-400">
                    {error}
                  </div>
                )}
                <form onSubmit={handleSubmit} className="flex gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask a financial question..."
                    disabled={loading}
                    className="flex-1"
                  />
                  <Button type="submit" disabled={loading || !input.trim()}>
                    {loading ? "..." : "Send"}
                  </Button>
                </form>
              </div>
            </Card>
          </div>

          {/* Info Panel */}
          <div className="hidden lg:block">
            <Card className="h-full">
              <CardHeader className="border-b">
                <CardTitle className="text-lg">About MacroMap</CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                <div>
                  <h3 className="font-medium text-sm mb-1">Expertise Areas</h3>
                  <ul className="text-sm text-zinc-600 dark:text-zinc-400 space-y-1">
                    <li>• Financial Statement Analysis</li>
                    <li>• Valuation Methods (DCF, Comps)</li>
                    <li>• Financial Ratios & Metrics</li>
                    <li>• Capital Markets</li>
                    <li>• Macroeconomics</li>
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
