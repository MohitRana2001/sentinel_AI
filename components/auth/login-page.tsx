"use client"
import type React from "react"
import { useMemo, useState } from "react"
import { useAuth } from "@/context/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

type Mode = "login" | "signup"
type RbacLevel = "station" | "district" | "state"

const RBAC_LABELS: Record<RbacLevel, string> = {
  station: "Station",
  district: "District",
  state: "State",
}

export function LoginPage() {
  const { login, signup } = useAuth()
  const [mode, setMode] = useState<Mode>("login")
  const [error, setError] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)

  const [loginForm, setLoginForm] = useState({
    email: "",
    password: "",
  })

  const [signupForm, setSignupForm] = useState({
    email: "",
    username: "",
    password: "",
    confirmPassword: "",
    rbacLevel: "station" as RbacLevel,
    stationId: "",
    districtId: "",
    stateId: "",
  })

  const resetFeedback = () => {
    setError("")
  }

  const requiredHierarchyFields = useMemo(() => {
    switch (signupForm.rbacLevel) {
      case "station":
        return ["stateId", "districtId", "stationId"] as const
      case "district":
        return ["stateId", "districtId"] as const
      case "state":
        return ["stateId"] as const
      default:
        return []
    }
  }, [signupForm.rbacLevel])

  const handleToggle = (nextMode: Mode) => {
    if (mode === nextMode) return
    setMode(nextMode)
    resetFeedback()
    setIsLoading(false)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    resetFeedback()
    setIsLoading(true)

    try {
      if (mode === "login") {
        await login(loginForm.email, loginForm.password)
      } else {
        if (signupForm.password !== signupForm.confirmPassword) {
          throw new Error("Passwords do not match")
        }

        // Validate hierarchy fields based on RBAC level
        for (const field of requiredHierarchyFields) {
          if (!signupForm[field]) {
            throw new Error(`Please provide ${field.replace("Id", " ID")}`)
          }
        }

        await signup({
          email: signupForm.email,
          username: signupForm.username,
          password: signupForm.password,
          rbacLevel: signupForm.rbacLevel,
          stationId: signupForm.stationId || undefined,
          districtId: signupForm.districtId || undefined,
          stateId: signupForm.stateId || undefined,
        })
      }
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
            {mode === "login" ? "Sign in to Sentinel AI" : "Create your Sentinel AI account"}
          </CardTitle>
          <CardDescription>
            {mode === "login"
              ? "Access edge intelligence dashboards and document workflows"
              : "Provision a new account with the right RBAC scope for your deployment"}
          </CardDescription>

          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{mode === "login" ? "Need an account?" : "Already onboarded?"}</span>
            <button
              type="button"
              onClick={() => handleToggle(mode === "login" ? "signup" : "login")}
              className="font-semibold text-blue-600 hover:text-blue-700 transition-colors"
            >
              {mode === "login" ? "Create one" : "Sign in instead"}
            </button>
          </div>
        </CardHeader>

        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            {mode === "login" ? (
              <>
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
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <label htmlFor="signup-email" className="text-sm font-medium">
                    Work email
                  </label>
                  <Input
                    id="signup-email"
                    type="email"
                    value={signupForm.email}
                    onChange={(event) => setSignupForm((prev) => ({ ...prev, email: event.target.value }))}
                    placeholder="user@police.gov"
                    autoComplete="email"
                    required
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="signup-username" className="text-sm font-medium">
                    Operator name
                  </label>
                  <Input
                    id="signup-username"
                    value={signupForm.username}
                    onChange={(event) => setSignupForm((prev) => ({ ...prev, username: event.target.value }))}
                    placeholder="station_ops"
                    autoComplete="username"
                    required
                    disabled={isLoading}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label htmlFor="signup-password" className="text-sm font-medium">
                      Password
                    </label>
                    <Input
                      id="signup-password"
                      type="password"
                      value={signupForm.password}
                      onChange={(event) => setSignupForm((prev) => ({ ...prev, password: event.target.value }))}
                      placeholder="StrongPass!234"
                      autoComplete="new-password"
                      required
                      disabled={isLoading}
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="signup-confirm-password" className="text-sm font-medium">
                      Confirm password
                    </label>
                    <Input
                      id="signup-confirm-password"
                      type="password"
                      value={signupForm.confirmPassword}
                      onChange={(event) =>
                        setSignupForm((prev) => ({ ...prev, confirmPassword: event.target.value }))
                      }
                      placeholder="StrongPass!234"
                      autoComplete="new-password"
                      required
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="signup-rbac-level" className="text-sm font-medium">
                    Access level
                  </label>
                  <select
                    id="signup-rbac-level"
                    value={signupForm.rbacLevel}
                    onChange={(event) =>
                      setSignupForm((prev) => ({
                        ...prev,
                        rbacLevel: event.target.value as RbacLevel,
                      }))
                    }
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={isLoading}
                  >
                    {Object.entries(RBAC_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label} level
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Select the highest level of jurisdiction this account should access.
                  </p>
                </div>

                <div className="space-y-3">
                  <HierarchyField
                    id="state-id"
                    label="State identifier"
                    value={signupForm.stateId}
                    onChange={(value) => setSignupForm((prev) => ({ ...prev, stateId: value }))}
                    disabled={isLoading}
                    required={requiredHierarchyFields.includes("stateId")}
                  />

                  {signupForm.rbacLevel !== "state" && (
                    <HierarchyField
                      id="district-id"
                      label="District identifier"
                      value={signupForm.districtId}
                      onChange={(value) => setSignupForm((prev) => ({ ...prev, districtId: value }))}
                      disabled={isLoading}
                      required={requiredHierarchyFields.includes("districtId")}
                    />
                  )}

                  {signupForm.rbacLevel === "station" && (
                    <HierarchyField
                      id="station-id"
                      label="Station identifier"
                      value={signupForm.stationId}
                      onChange={(value) => setSignupForm((prev) => ({ ...prev, stationId: value }))}
                      disabled={isLoading}
                      required={requiredHierarchyFields.includes("stationId")}
                    />
                  )}
                </div>
              </>
            )}

            {error && <div className="text-sm text-red-600 font-medium">{error}</div>}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Processing..." : mode === "login" ? "Sign In" : "Create account"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

interface HierarchyFieldProps {
  id: string
  label: string
  value: string
  disabled?: boolean
  required?: boolean
  onChange: (value: string) => void
}

function HierarchyField({ id, label, value, disabled, required, onChange }: HierarchyFieldProps) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
        {required ? <span className="ml-1 text-red-600">*</span> : <span className="ml-1 text-slate-400">(optional)</span>}
      </label>
      <Input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={`e.g. ${label.replace(" identifier", "_001").toUpperCase()}`}
        disabled={disabled}
        required={required}
      />
    </div>
  )
}
