"use client"

import { useState, useRef, useEffect } from "react"
import { useAuth } from "@/context/auth-context"
import { Button } from "@/components/ui/button"
import { LogOut, FileText, History, Settings, UserIcon, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarProps {
  currentPage: "analysis" | "history" | "settings" | "profile"
  onPageChange: (page: "analysis" | "history" | "settings" | "profile") => void
}

export function Sidebar({ currentPage, onPageChange }: SidebarProps) {
  const { user, logout, documents } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const sidebarRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!sidebarRef.current || !triggerRef.current) return

      const sidebarRect = sidebarRef.current.getBoundingClientRect()
      const triggerRect = triggerRef.current.getBoundingClientRect()

      // Check if mouse is near the left edge (trigger zone)
      const isNearTrigger = e.clientX < 50

      // Check if mouse is over sidebar
      const isOverSidebar =
        e.clientX >= sidebarRect.left &&
        e.clientX <= sidebarRect.right &&
        e.clientY >= sidebarRect.top &&
        e.clientY <= sidebarRect.bottom

      if (isNearTrigger || isOverSidebar) {
        setIsOpen(true)
      } else if (!isOverSidebar && !isNearTrigger) {
        setIsOpen(false)
      }
    }

    window.addEventListener("mousemove", handleMouseMove)
    return () => window.removeEventListener("mousemove", handleMouseMove)
  }, [])

  const menuItems = [
    { id: "analysis", label: "Document Analysis", icon: FileText },
    { id: "history", label: "Past Uploads", icon: History, badge: documents.length },
    { id: "settings", label: "Settings", icon: Settings },
    { id: "profile", label: "Profile", icon: UserIcon },
  ]

  return (
    <>
      {/* Trigger zone indicator */}
      <div ref={triggerRef} className="fixed left-0 top-0 w-1 h-screen pointer-events-none" />

      {/* Sidebar */}
      <div
        ref={sidebarRef}
        className={cn(
          "fixed left-0 top-0 h-screen w-64 bg-slate-900 text-white shadow-2xl transition-transform duration-300 ease-out z-40 flex flex-col",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            DocAnalyze
          </h2>
          <p className="text-xs text-slate-400 mt-1">AI-Powered Analysis</p>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id as "analysis" | "history" | "settings" | "profile")}
                className={cn(
                  "w-full flex items-center justify-between px-4 py-3 rounded-lg transition-colors duration-200",
                  currentPage === item.id
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white",
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-5 w-5" />
                  <span className="font-medium">{item.label}</span>
                </div>
                {item.badge && (
                  <span className="bg-blue-500 text-white text-xs font-bold px-2 py-1 rounded-full">{item.badge}</span>
                )}
                {currentPage === item.id && <ChevronRight className="h-4 w-4" />}
              </button>
            )
          })}
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-slate-700 space-y-3">
          {user && (
            <div className="px-4 py-3 bg-slate-800 rounded-lg">
              <p className="text-sm font-medium text-white">{user.name}</p>
              <p className="text-xs text-slate-400 capitalize">{user.role}</p>
            </div>
          )}
          <Button onClick={logout} variant="destructive" className="w-full justify-start" size="sm">
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>

      {/* Overlay when sidebar is open */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 transition-opacity duration-300"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
