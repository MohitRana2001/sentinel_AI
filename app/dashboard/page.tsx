"use client";
import { useAuth } from "@/context/auth-context";
import { LoginPage } from "@/components/auth/login-page";
import { DashboardPage } from "@/components/dashboard/dashboard-page";
import { Header } from "@/components/common/header";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Dashboard() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/");
    }
  }, [isAuthenticated, router]);

  return (
    <>
      {isAuthenticated && <Header />}
      {isAuthenticated ? <DashboardPage /> : <LoginPage />}
    </>
  );
}
