"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import type { ChatMessage, ChatSource } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatTabProps {
  jobId: string;
  documents: { id: number; fileName: string }[];
  selectedDocumentIds: number[];
}

const formatTime = (isoString: string) =>
  new Date(isoString).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

export function ChatTab({
  jobId,
  documents,
  selectedDocumentIds,
}: ChatTabProps) {
  // Get selected document names
  const selectedDocs = documents.filter((d) =>
    selectedDocumentIds.includes(d.id)
  );
  const docNames =
    selectedDocs.length > 0
      ? selectedDocs.map((d) => d.fileName).join(", ")
      : "all documents";

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "intro",
      sender: "ai",
      content: `Hello! I'm your Sentinel AI assistant. I'm ready to answer questions about ${
        selectedDocs.length > 0
          ? `the selected document${
              selectedDocs.length > 1 ? "s" : ""
            }: **${docNames}**`
          : "your uploaded documents"
      }. Feel free to ask about summaries, translations, specific details, or relationships between documents.`,
      timestamp: new Date().toISOString(),
      mode: "gemini-2.0-flash",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) {
      return;
    }

    if (selectedDocumentIds.length === 0) {
      setError("Please select at least one document to chat with.");
      return;
    }

    const content = inputValue.trim();
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.chat(
        content,
        jobId,
        selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined
      );

      // Log response for debugging
      console.log("Chat response received:", {
        mode: response.mode,
        sourcesCount: response.sources?.length || 0,
        responseLength: response.response?.length || 0,
      });

      const aiMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: "ai",
        content: response.response,
        timestamp: new Date().toISOString(),
        mode: response.mode,
        sources: response.sources as ChatSource[],
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      console.error("Chat error:", err);

      const errorMessage =
        err instanceof Error ? err.message : "Unknown error occurred";
      const fallback: ChatMessage = {
        id: `error-${Date.now()}`,
        sender: "ai",
        content: `I encountered an error while processing your request: ${errorMessage}\n\nPlease check:\n- The backend server is running\n- GEMINI_API_KEY is configured\n- Your documents are properly processed`,
        timestamp: new Date().toISOString(),
        error: true,
      };
      setMessages((prev) => [...prev, fallback]);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const renderSources = (sources?: ChatSource[]) => {
    if (!sources || sources.length === 0) return null;

    return (
      <div className="mt-3 rounded-lg bg-white/80 border border-blue-200 p-3 text-xs text-slate-600 space-y-2">
        <p className="font-semibold text-blue-700 uppercase tracking-wide text-[11px] flex items-center gap-1">
          <svg
            className="w-3 h-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Source Excerpts ({sources.length})
        </p>
        <ul className="space-y-2.5">
          {sources.map((source, index) => (
            <li
              key={`${source.document_id}-${source.chunk_index}-${index}`}
              className="leading-relaxed pl-1"
            >
              <div className="flex items-start gap-2">
                <span className="font-medium text-blue-600 text-sm mt-0.5">
                  •
                </span>
                <div className="flex-1">
                  <span className="font-semibold text-slate-800 text-[11px]">
                    Doc {source.document_id}, Chunk {source.chunk_index + 1}
                  </span>
                  <p className="text-slate-600 mt-0.5 leading-relaxed">
                    {source.chunk_text.substring(0, 250)}
                    {source.chunk_text.length > 250 ? "…" : ""}
                  </p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {selectedDocs.length > 0 && (
        <Card className="p-3 mb-4 bg-blue-50 border-blue-200">
          <p className="text-sm text-blue-900">
            <strong>Chatting with:</strong> {docNames}
          </p>
        </Card>
      )}

      {selectedDocs.length === 0 && (
        <Card className="p-3 mb-4 bg-amber-50 border-amber-200">
          <p className="text-sm text-amber-900">
            <strong>No documents selected.</strong> Please select at least one
            document from above to start chatting.
          </p>
        </Card>
      )}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 bg-gradient-to-br from-blue-50/80 via-sky-50/60 to-blue-100/60 rounded-xl border border-blue-100 shadow-inner mb-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <Card
              className={`max-w-xs lg:max-w-xl px-4 py-3 shadow-md ${
                message.sender === "user"
                  ? "bg-blue-600 text-white"
                  : message.error
                  ? "bg-white border border-red-200 text-red-700"
                  : "bg-blue-100/90 border border-blue-200 text-slate-800"
              }`}
            >
              {message.sender === "user" ? (
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {message.content}
                </p>
              ) : (
                <div
                  className={`prose prose-sm max-w-none ${
                    message.sender === "ai" ? "prose-slate" : ""
                  }`}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code: ({
                        node,
                        inline,
                        className,
                        children,
                        ...props
                      }) => {
                        return inline ? (
                          <code
                            className="bg-slate-200 px-1 rounded text-slate-800"
                            {...props}
                          >
                            {children}
                          </code>
                        ) : (
                          <code
                            className="block bg-slate-900 text-white p-3 rounded overflow-x-auto text-xs"
                            {...props}
                          >
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              )}
              {message.sources && renderSources(message.sources)}
              <p
                className={`text-[11px] mt-2 uppercase tracking-wide ${
                  message.sender === "user"
                    ? "text-blue-50/70"
                    : "text-blue-700/80"
                }`}
              >
                {formatTime(message.timestamp)}
                {message.mode && !message.error && message.mode !== "system"
                  ? ` • ${message.mode}`
                  : ""}
              </p>
            </Card>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <Card className="bg-blue-100/70 border border-blue-200 px-4 py-2">
              <div className="flex items-center gap-2 text-blue-700">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" />
                <div
                  className="w-2 h-2 rounded-full bg-blue-500 animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
                <div
                  className="w-2 h-2 rounded-full bg-blue-500 animate-bounce"
                  style={{ animationDelay: "0.4s" }}
                />
                <span className="text-xs font-medium">Thinking…</span>
              </div>
            </Card>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="mb-3 text-xs text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      <div className="flex gap-2 items-center bg-blue-50/70 border border-blue-100 rounded-xl px-3 py-2 shadow-sm">
        <Input
          placeholder="Ask a question about the document…"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
          disabled={isLoading}
          className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-slate-700"
        />
        <Button
          onClick={handleSendMessage}
          disabled={isLoading || !inputValue.trim()}
          size="icon"
          className="bg-blue-600 hover:bg-blue-700 text-white shadow-md"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
