"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";

interface GraphVisualizationProps {
  jobId: string;
  selectedDocumentIds?: number[];
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, any>;
}

interface GraphLink {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, any>;
}

export function GraphVisualization({ jobId, selectedDocumentIds }: GraphVisualizationProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<{
    nodes: GraphNode[];
    links: GraphLink[];
  } | null>(null);

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getJobGraph(jobId, selectedDocumentIds);
        setGraphData({
          nodes: data.nodes,
          links: data.relationships,
        });
        setError(null);
      } catch (err) {
        console.error("Failed to fetch graph data:", err);
        setError("Failed to load graph data");
      } finally {
        setLoading(false);
      }
    };

    fetchGraphData();
  }, [jobId, selectedDocumentIds]);

  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const width = 800;
    const height = 600;

    // Clear previous SVG
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);

    // Add zoom behavior
    const g = svg.append("g");

    svg.call(
      d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        })
    );

    // Create color scale for different node types
    const color = d3.scaleOrdinal(d3.schemeCategory10);

    // Create force simulation
    const simulation = d3
      .forceSimulation(graphData.nodes as any)
      .force(
        "link",
        d3
          .forceLink(graphData.links)
          .id((d: any) => d.id)
          .distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(50));

    // Create arrow markers for directed links
    svg
      .append("defs")
      .selectAll("marker")
      .data(["end"])
      .join("marker")
      .attr("id", String)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#999");

    // Create links
    const link = g
      .append("g")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(graphData.links)
      .join("line")
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#end)");

    // Create link labels
    const linkLabel = g
      .append("g")
      .selectAll("text")
      .data(graphData.links)
      .join("text")
      .attr("font-size", 10)
      .attr("fill", "#666")
      .attr("text-anchor", "middle")
      .text((d) => d.type);

    // Create nodes
    const node = g
      .append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .selectAll("circle")
      .data(graphData.nodes)
      .join("circle")
      .attr("r", 20)
      .attr("fill", (d) => color(d.type))
      .call(drag(simulation) as any);

    // Create node labels
    const nodeLabel = g
      .append("g")
      .selectAll("text")
      .data(graphData.nodes)
      .join("text")
      .attr("font-size", 12)
      .attr("font-weight", "bold")
      .attr("text-anchor", "middle")
      .attr("dy", 35)
      .text((d) => d.label);

    // Add tooltips
    node.append("title").text(
      (d) =>
        `${d.label}\nType: ${d.type}\n${
          d.properties
            ? Object.entries(d.properties)
                .map(([k, v]) => `${k}: ${v}`)
                .join("\n")
            : ""
        }`
    );

    // Update positions on each tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      linkLabel
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2);

      node.attr("cx", (d: any) => d.x).attr("cy", (d: any) => d.y);

      nodeLabel.attr("x", (d: any) => d.x).attr("y", (d: any) => d.y);
    });

    // Drag behavior
    function drag(simulation: d3.Simulation<any, undefined>) {
      function dragstarted(event: any) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }

      function dragged(event: any) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }

      function dragended(event: any) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }

      return d3
        .drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }
  }, [graphData]);

  if (loading) {
    return (
      <Card className="p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="ml-4 text-slate-600">Loading knowledge graph...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-8">
        <div className="text-center text-red-600">
          <p>{error}</p>
          <p className="text-sm text-slate-500 mt-2">
            No graph data available yet. Try uploading a document first.
          </p>
        </div>
      </Card>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <Card className="p-8">
        <div className="text-center text-slate-500">
          <p>No graph data available</p>
          <p className="text-sm mt-2">
            Knowledge graph will appear here after processing
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Knowledge Graph</h3>
        <p className="text-sm text-slate-600 mt-1">
          {graphData.nodes.length} entities • {graphData.links.length}{" "}
          relationships
        </p>
        <p className="text-xs text-slate-500 mt-2">
          💡 Drag nodes to reposition • Scroll to zoom
        </p>
      </div>
      <div className="border rounded-lg overflow-hidden bg-slate-50">
        <svg ref={svgRef} className="w-full h-full"></svg>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {Array.from(new Set(graphData.nodes.map((n) => n.type))).map((type) => (
          <div key={type} className="flex items-center gap-2 text-sm">
            <div
              className="w-4 h-4 rounded-full"
              style={{
                backgroundColor: d3.scaleOrdinal(d3.schemeCategory10)(type),
              }}
            ></div>
            <span className="capitalize">{type}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
