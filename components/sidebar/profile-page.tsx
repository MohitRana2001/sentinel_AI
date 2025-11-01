"use client";

import { useAuth } from "@/context/auth-context";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { User, Mail, Shield, Calendar } from "lucide-react";

export function ProfilePage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Profile</h1>
          <p className="text-muted-foreground">
            View and manage your profile information
          </p>
        </div>

        {/* Profile Card */}
        <Card className="p-8 mb-6">
          <div className="flex items-center gap-6 mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center">
              <User className="h-10 w-10 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold">{user.name}</h2>
              <p className="text-muted-foreground capitalize">
                {user.rbacLevel} access
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Email */}
            <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg">
              <Mail className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-muted-foreground">Email Address</p>
                <p className="font-medium">{user.email}</p>
              </div>
            </div>

            {/* Access Level */}
            <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg">
              <Shield className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-muted-foreground">Access Level</p>
                <p className="font-medium capitalize">{user.rbacLevel}</p>
              </div>
            </div>

            {/* Manager Info for Analysts */}
            {user.rbacLevel === "analyst" && user.managerId && (
              <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg">
                <Shield className="h-5 w-5 text-indigo-600" />
                <div>
                  <p className="text-sm text-muted-foreground">Manager ID</p>
                  <p className="font-medium">{user.managerId}</p>
                </div>
              </div>
            )}

            {/* User ID */}
            <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg">
              <Calendar className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm text-muted-foreground">User ID</p>
                <p className="font-medium text-xs font-mono">{user.id}</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Edit Profile Button */}
        <div className="flex gap-3">
          <Button className="flex-1">Edit Profile</Button>
          <Button variant="outline" className="flex-1 bg-transparent">
            Change Password
          </Button>
        </div>
      </div>
    </div>
  );
}
