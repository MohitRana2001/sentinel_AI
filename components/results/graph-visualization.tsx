"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GraphVisualizationProps {
  jobId: string;
  selectedDocumentIds?: number[];
}

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, any>;
  level?: number;
  group?: number;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  properties?: Record<string, any>;
  strength?: number;
}

export function GraphVisualization({
  jobId,
  selectedDocumentIds,
}: GraphVisualizationProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<{
    nodes: GraphNode[];
    links: GraphLink[];
  } | null>(null);

  // Zoom control ref
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown>>();

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getJobGraph(jobId, selectedDocumentIds);
      
        const uniqueTypes = new Set(data.nodes.map((n: any) => n.type));
        console.log("📊 Unique node types in graph:", Array.from(uniqueTypes));
        console.log("📝 Sample nodes:", data.nodes.slice(0, 5));
        
        const nodes = data.nodes.map((node: any) => ({
          ...node,
          group: getGroupByType(node.type),
          level: node.type === "Document" || node.type === "User" ? 1 : 2,
        }));

        const links = data.relationships.map((link: any) => ({
          ...link,
          strength: link.properties?.strength || 0.5,
        }));

        setGraphData({ nodes, links });
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

    const width = svgRef.current.clientWidth || 960;
    const height = 600;

    // Clear previous SVG
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    // Create a container group for zoom
    const container = svg.append("g");

    // Color mapping function - default colors that don't change
    function getNodeColor(node: GraphNode) {
    const colorMap: Record<string, string> = {
      // People
      Person: "#3b82f6",        // Blue
      User: "#2563eb",          // Darker Blue
      
      // Organizations
      Organization: "#8b5cf6",  // Purple
      Company: "#7c3aed",       // Darker Purple
      
      // Locations
      Location: "#10b981",      // Green
      Place: "#059669",         // Darker Green
      Address: "#14b8a6",       // Teal
      
      // Documents
      Document: "#f97316",      // Orange
      File: "#ea580c",          // Darker Orange
      
      // Vehicles
      Vehicle: "#ec4899",       // Pink
      Car: "#db2777",           // Darker Pink
      
      // Events
      Event: "#f59e0b",         // Amber
      Date: "#d97706",          // Darker Amber
      
      // Default
      Entity: "#6b7280",        // Gray
    };
    
    return colorMap[node.type] || "#6b7280"; // Default gray for unknown types
  }


    // Create zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on("zoom", (event) => {
        container.attr("transform", event.transform);
      });

    svg.call(zoom);
    zoomBehaviorRef.current = zoom;

    // Create force simulation
    const linkForce = d3
      .forceLink<GraphNode, GraphLink>(graphData.links)
      .id((d) => d.id)
      .distance(150)
      .strength((d) => d.strength || 0.5);

    const simulation = d3
      .forceSimulation<GraphNode>(graphData.nodes)
      .force("link", linkForce)
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(40));

    // Drag behavior
    const dragDrop = d3
      .drag<SVGCircleElement, GraphNode>()
      .on("start", function (event, node) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        node.fx = node.x;
        node.fy = node.y;
      })
      .on("drag", function (event, node) {
        node.fx = event.x;
        node.fy = event.y;
      })
      .on("end", function (event, node) {
        if (!event.active) simulation.alphaTarget(0);
        // node.fx = null;
        // node.fy = null;
      });

    // Create arrow markers for links
    container
      .append("defs")
      .selectAll("marker")
      .data(["arrow"])
      .enter()
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#999");

    // Create links with visible stroke
    const linkElements = container
      .append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(graphData.links)
      .enter()
      .append("line")
      .attr("stroke-width", 2)
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("marker-end", "url(#arrow)");

    // Create link labels (relationship types)
    const linkText = container
      .append("g")
      .attr("class", "link-texts")
      .selectAll("text")
      .data(graphData.links)
      .enter()
      .append("text")
      .attr("font-family", "Arial, Helvetica, sans-serif")
      .attr("fill", "#666")
      .attr("font-size", "10px")
      .attr("text-anchor", "middle")
      .attr("pointer-events", "none")
      .text((d) => d.type);

    // Create nodes
    const nodeElements = container
      .append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(graphData.nodes)
      .enter()
      .append("circle")
      .attr("r", 15)
      .attr("fill", (d) => getNodeColor(d))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .call(dragDrop);

    // Add tooltips to nodes
    nodeElements.append("title").text(
      (d) =>
        `${d.label}\nType: ${d.type}${
          d.properties
            ? "\n" +
              Object.entries(d.properties)
                .map(([k, v]) => `${k}: ${v}`)
                .join("\n")
            : ""
        }`
    );

    // Create node labels
    const textElements = container
      .append("g")
      .attr("class", "texts")
      .selectAll("text")
      .data(graphData.nodes)
      .enter()
      .append("text")
      .text((node) => node.label)
      .attr("font-size", 12)
      .attr("font-weight", "500")
      .attr("dx", 20)
      .attr("dy", 4)
      .attr("pointer-events", "none")
      .attr("fill", "#1e293b");

    // Update positions on each tick
    simulation.on("tick", () => {
      nodeElements
        .attr("cx", (node) => node.x || 0)
        .attr("cy", (node) => node.y || 0);

      textElements
        .attr("x", (node) => node.x || 0)
        .attr("y", (node) => node.y || 0);

      linkElements
        .attr("x1", (link: any) => link.source.x)
        .attr("y1", (link: any) => link.source.y)
        .attr("x2", (link: any) => link.target.x)
        .attr("y2", (link: any) => link.target.y);

      linkText
        .attr("x", (link: any) => (link.source.x + link.target.x) / 2)
        .attr("y", (link: any) => (link.source.y + link.target.y) / 2);
    });

    return () => {
      simulation.stop();
    };
  }, [graphData]);

  // Zoom control functions
  const handleZoomIn = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomBehaviorRef.current.scaleBy, 1.3);
    }
  };

  const handleZoomOut = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomBehaviorRef.current.scaleBy, 0.7);
    }
  };

  const handleResetZoom = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(
          zoomBehaviorRef.current.transform,
          d3.zoomIdentity
        );
    }
  };

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
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">Knowledge Graph</h3>
          <p className="text-sm text-slate-600 mt-1">
            {graphData.nodes.length} entities • {graphData.links.length}{" "}
            relationships
          </p>
          <p className="text-xs text-slate-500 mt-2">
            💡 Drag nodes to reposition • Scroll or use buttons to zoom • Nodes stay where you drop them
          </p>
        </div>
        
        {/* Zoom Controls */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={handleZoomIn}
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleZoomOut}
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleResetZoom}
            title="Reset Zoom"
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="border rounded-lg overflow-hidden bg-slate-50 relative">
        <svg ref={svgRef} className="w-full" style={{ height: "600px" }}></svg>
      </div>

      {/* Legend */}
      <div className="mt-4">
          <h4 className="text-sm font-semibold mb-2">Entity Types:</h4>
          <div className="flex flex-wrap gap-3">
            {Array.from(new Set(graphData.nodes.map((n) => n.type)))
              .sort()
              .map((type) => {
                const colorMap: Record<string, string> = {
                  Person: "#3b82f6",
                  User: "#2563eb",
                  Organization: "#8b5cf6",
                  Company: "#7c3aed",
                  Location: "#10b981",
                  Place: "#059669",
                  Address: "#14b8a6",
                  Document: "#f97316",
                  File: "#ea580c",
                  Vehicle: "#ec4899",
                  Car: "#db2777",
                  Event: "#f59e0b",
                  Date: "#d97706",
                  Entity: "#6b7280",
                };
                const nodeColor = colorMap[type] || "#6b7280";
        
                return (
                  <div key={type} className="flex items-center gap-2 text-sm">
                    <div
                      className="w-4 h-4 rounded-full border-2 border-white shadow-sm"
                      style={{
                        backgroundColor: nodeColor,
                      }}
                    ></div>
                    <span className="capitalize font-medium">{type}</span>
                  </div>
                );
              })}
          </div>
        </div>
    </Card>
  );
}

function getGroupByType(type: string): number {
  const groupMap: Record<string, number> = {
    User: 0,
    Document: 0,
    Person: 1,
    Organization: 2,
    Location: 3,
    Event: 4,
  };
  return groupMap[type] || 5;
}