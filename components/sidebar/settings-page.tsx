"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Bell, Lock, Eye, Database } from "lucide-react"

export function SettingsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Settings</h1>
          <p className="text-muted-foreground">Manage your preferences and account settings</p>
        </div>

        <div className="space-y-4">
          {/* Notifications */}
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Bell className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Notifications</h3>
                  <p className="text-sm text-muted-foreground mt-1">Manage email and push notifications</p>
                </div>
              </div>
              <Button variant="outline" size="sm">
                Configure
              </Button>
            </div>
          </Card>

          {/* Privacy & Security */}
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Lock className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Privacy & Security</h3>
                  <p className="text-sm text-muted-foreground mt-1">Control your data and security settings</p>
                </div>
              </div>
              <Button variant="outline" size="sm">
                Configure
              </Button>
            </div>
          </Card>

          {/* Display Preferences */}
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Eye className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Display Preferences</h3>
                  <p className="text-sm text-muted-foreground mt-1">Customize your interface appearance</p>
                </div>
              </div>
              <Button variant="outline" size="sm">
                Configure
              </Button>
            </div>
          </Card>

          {/* Data Management */}
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <Database className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Data Management</h3>
                  <p className="text-sm text-muted-foreground mt-1">Export or delete your data</p>
                </div>
              </div>
              <Button variant="outline" size="sm">
                Configure
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
