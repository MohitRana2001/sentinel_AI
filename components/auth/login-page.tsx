"use client"
import type React from "react"
import { useState } from "react"
import { useAuth } from "@/context/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function LoginPage() {
  const { login } = useAuth()
  const [error, setError] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)

  const [loginForm, setLoginForm] = useState({
    email: "",
    password: "",
  })

  const resetFeedback = () => {
    setError("")
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    resetFeedback()
    setIsLoading(true)

    try {
      await login(loginForm.email, loginForm.password)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-3">
          <CardTitle className="text-2xl font-bold">
            Sign in to Sentinel AI
          </CardTitle>
          <CardDescription>
            Access intelligence dashboards and document workflows
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label htmlFor="login-email" className="text-sm font-medium">
                Email
              </label>
              <Input
                id="login-email"
                type="email"
                value={loginForm.email}
                onChange={(event) => setLoginForm((prev) => ({ ...prev, email: event.target.value }))}
                placeholder="you@example.com"
                autoComplete="email"
                required
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="login-password" className="text-sm font-medium">
                Password
              </label>
              <Input
                id="login-password"
                type="password"
                value={loginForm.password}
                onChange={(event) => setLoginForm((prev) => ({ ...prev, password: event.target.value }))}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                disabled={isLoading}
              />
            </div>

            {error && <div className="text-sm text-red-600 font-medium">{error}</div>}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Sign In"}
            </Button>

            <div className="text-center text-sm text-muted-foreground pt-4">
              Contact your administrator to create an account
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
