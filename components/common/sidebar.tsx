"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/button";
import {
  LogOut,
  FileText,
  History,
  Settings,
  UserIcon,
  ChevronRight,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  currentPage: "analysis" | "history" | "settings" | "profile";
  onPageChange: (page: "analysis" | "history" | "settings" | "profile") => void;
}

export function Sidebar({ currentPage, onPageChange }: SidebarProps) {
  const { user, logout, documents } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!sidebarRef.current || !triggerRef.current) return;

      const sidebarRect = sidebarRef.current.getBoundingClientRect();
      const triggerRect = triggerRef.current.getBoundingClientRect();

      // Check if mouse is near the left edge (trigger zone)
      const isNearTrigger = e.clientX < 50;

      // Check if mouse is over sidebar
      const isOverSidebar =
        e.clientX >= sidebarRect.left &&
        e.clientX <= sidebarRect.right &&
        e.clientY >= sidebarRect.top &&
        e.clientY <= sidebarRect.bottom;

      if (isNearTrigger || isOverSidebar) {
        setIsOpen(true);
      } else if (!isOverSidebar && !isNearTrigger) {
        setIsOpen(false);
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const menuItems = [
    { id: "analysis", label: "Document Analysis", icon: FileText },
    {
      id: "history",
      label: "Past Uploads",
      icon: History,
      badge: documents.length,
    },
    { id: "settings", label: "Settings", icon: Settings },
    { id: "profile", label: "Profile", icon: UserIcon },
  ];

  return (
    <>
      {/* Hamburger Menu Button - Always visible */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed top-4 left-4 z-50 p-3 rounded-lg shadow-lg transition-all duration-300",
          "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700",
          "text-white hover:shadow-xl hover:scale-105 active:scale-95",
          isOpen && "left-[17rem]"
        )}
        aria-label="Toggle menu"
      >
        {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Trigger zone indicator */}
      <div
        ref={triggerRef}
        className="fixed left-0 top-0 w-1 h-screen pointer-events-none"
      />

      {/* Sidebar */}
      <div
        ref={sidebarRef}
        className={cn(
          "fixed left-0 top-0 h-screen w-64 shadow-2xl transition-transform duration-300 ease-out z-40 flex flex-col",
          "bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900",
          "border-r border-slate-700/50",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                Sentinel AI
              </h2>
              <p className="text-xs text-slate-400">Document Intelligence</p>
            </div>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onPageChange(
                    item.id as "analysis" | "history" | "settings" | "profile"
                  );
                  setIsOpen(false); // Close on mobile after selection
                }}
                className={cn(
                  "w-full flex items-center justify-between px-4 py-3.5 rounded-xl transition-all duration-200 group",
                  isActive
                    ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/30"
                    : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      "h-5 w-5",
                      !isActive && "group-hover:scale-110 transition-transform"
                    )}
                  />
                  <span className="font-medium">{item.label}</span>
                </div>
                {item.badge && (
                  <span className="bg-indigo-500 text-white text-xs font-bold px-2 py-1 rounded-full shadow-sm">
                    {item.badge}
                  </span>
                )}
                {isActive && <ChevronRight className="h-4 w-4 animate-pulse" />}
              </button>
            );
          })}
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-slate-700/50 space-y-3">
          {user && (
            <div className="px-4 py-3 bg-slate-800/50 rounded-xl border border-slate-700/50 backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-lg">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {user.name}
                  </p>
                  <p className="text-xs text-slate-400 capitalize">
                    {user.rbacLevel} access
                  </p>
                </div>
              </div>
            </div>
          )}
          <Button
            onClick={() => void logout()}
            variant="destructive"
            className="w-full justify-start hover:scale-[1.02] active:scale-95 transition-transform shadow-lg"
            size="sm"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
          <div className="text-center pt-2">
            <p className="text-xs text-slate-500">v1.0.0 • Edge Inference</p>
          </div>
        </div>
      </div>

      {/* Overlay when sidebar is open */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 transition-opacity duration-300"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
