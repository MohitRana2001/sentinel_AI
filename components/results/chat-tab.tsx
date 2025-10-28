"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import type { ChatMessage } from "@/types"
import { Send } from "lucide-react"

interface ChatTabProps {
  fileName: string
}

export function ChatTab({ fileName }: ChatTabProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      sender: "ai",
      content: `I've analyzed "${fileName}" for you. Feel free to ask me any questions about the document's content, summary, or any specific details you'd like to know more about.`,
      timestamp: new Date().toISOString(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: "user",
      content: inputValue,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setIsLoading(true)

    // Simulate AI response delay
    await new Promise((resolve) => setTimeout(resolve, 1000))

    const aiResponses = [
      "Based on the document, I can confirm that this information is relevant to your query.",
      "That's an excellent question. The document discusses this topic in detail.",
      "I found relevant information about that in the document. Would you like me to elaborate?",
      "This is covered in the analysis. The key points are clearly outlined.",
      "Great question! The document provides comprehensive information on this subject.",
    ]

    const aiMessage: ChatMessage = {
      id: `msg-${Date.now() + 1}`,
      sender: "ai",
      content: aiResponses[Math.floor(Math.random() * aiResponses.length)],
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, aiMessage])
    setIsLoading(false)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 bg-muted/30 rounded-lg mb-4">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
            <Card
              className={`max-w-xs lg:max-w-md px-4 py-2 ${
                message.sender === "user" ? "bg-primary text-primary-foreground" : "bg-card border-muted"
              }`}
            >
              <p className="text-sm">{message.content}</p>
              <p
                className={`text-xs mt-1 ${
                  message.sender === "user" ? "text-primary-foreground/70" : "text-muted-foreground"
                }`}
              >
                {new Date(message.timestamp).toLocaleTimeString()}
              </p>
            </Card>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <Card className="bg-card border-muted px-4 py-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" />
                <div
                  className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
                <div
                  className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce"
                  style={{ animationDelay: "0.4s" }}
                />
              </div>
            </Card>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex gap-2">
        <Input
          placeholder="Ask a question about the document..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
          disabled={isLoading}
        />
        <Button onClick={handleSendMessage} disabled={isLoading || !inputValue.trim()} size="icon">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
