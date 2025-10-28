"use client"

import React from "react"
import { Card } from "@/components/ui/card"
import { AlertCircle } from "lucide-react"

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error) {
    console.error("Error in component:", error)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <Card className="p-6 border-destructive/50 bg-destructive/5">
            <div className="flex gap-3">
              <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-destructive">Visualization Error</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Unable to render the visualization. Please try again later.
                </p>
              </div>
            </div>
          </Card>
        )
      )
    }

    return this.props.children
  }
}
