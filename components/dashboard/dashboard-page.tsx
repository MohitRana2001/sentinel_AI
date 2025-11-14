"use client";

import { useAuth } from "@/context/auth-context";
import { AdminDashboard } from "./admin-dashboard";
import { ManagerDashboard } from "./manager-dashboard";
import { AnalystDashboard } from "./analyst-dashboard";

export function DashboardPage() {
  const { user } = useAuth();

  // Route based on user role
  if (user?.rbacLevel === "admin") {
    return <AdminDashboard />;
  }

  if (user?.rbacLevel === "manager") {
    return <ManagerDashboard />;
  }

  // Analyst dashboard - use new component with 3 upload options
  if (user?.rbacLevel === "analyst") {
    return <AnalystDashboard />;
  }

  // Fallback
  return null;
}

