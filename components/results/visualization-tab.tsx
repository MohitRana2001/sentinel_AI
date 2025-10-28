"use client"
import { Card } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import type { ChartData } from "@/types"
import { ErrorBoundary } from "./error-boundary"

interface VisualizationTabProps {
  data: ChartData[]
}

export function VisualizationTab({ data }: VisualizationTabProps) {
  return (
    <ErrorBoundary
      fallback={
        <Card className="p-6 text-center">
          <p className="text-muted-foreground">Visualization will be shown here</p>
        </Card>
      }
    >
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Data Visualization</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="value" fill="#3b82f6" name="Value" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </ErrorBoundary>
  )
}
