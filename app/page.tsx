"use client"
import { useAuth } from "@/context/auth-context"
import { LoginPage } from "@/components/auth/login-page"
import { DashboardPage } from "@/components/dashboard/dashboard-page"
import { Header } from "@/components/common/header"

export default function Home() {
  const { isAuthenticated } = useAuth()

  return (
    <>
      {isAuthenticated && <Header />}
      {isAuthenticated ? <DashboardPage /> : <LoginPage />}
    </>
  )
}
