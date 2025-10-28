"use client"

import type React from "react"
import { useState } from "react"
import { useAuth } from "@/context/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setIsLoading(true)

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    if (!login(email, password)) {
      setError("Invalid email or password")
      setIsLoading(false)
      return
    }

    setIsLoading(false)
  }

  const handleDemoLogin = (demoEmail: string) => {
    setEmail(demoEmail)
    setPassword("password")
    setError("")
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-2">
          <CardTitle className="text-2xl font-bold">Document Analysis AI</CardTitle>
          <CardDescription>Sign in to your account to get started</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="admin@test.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>

            {error && <div className="text-sm text-red-600 font-medium">{error}</div>}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Sign In"}
            </Button>
          </form>

          <div className="mt-6 space-y-2">
            <p className="text-xs text-muted-foreground text-center font-semibold">Demo Accounts</p>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleDemoLogin("admin@test.com")}
                disabled={isLoading}
              >
                Admin
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleDemoLogin("analyst@test.com")}
                disabled={isLoading}
              >
                Analyst
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleDemoLogin("manager@test.com")}
                disabled={isLoading}
              >
                Manager
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleDemoLogin("super_admin@test.com")}
                disabled={isLoading}
              >
                Super Admin
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
