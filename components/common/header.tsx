"use client"
import { useAuth } from "@/context/auth-context"
import { User } from "lucide-react"

export function Header() {
  const { user } = useAuth()

  return (
    <header className="border-b bg-card">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Document Analysis AI</h1>
        </div>

        {user && (
          <div className="flex items-center gap-2 text-sm">
            <User className="h-4 w-4" />
            <div>
              <p className="font-medium">{user.name}</p>
              <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
