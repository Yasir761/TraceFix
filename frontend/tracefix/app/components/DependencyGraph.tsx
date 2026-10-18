
"use client";

import { useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  MarkerType,
  Position,
  Handle,
  Panel as FlowPanel,
  type Edge,
  type Node,
} from "@xyflow/react";
import { GitBranch, Maximize2, Network } from "lucide-react";

type RawEdge = {
  source?: string;
  source_id?: string;
  source_name?: string;
  target?: string;
  target_id?: string;
  target_name?: string;
  [key: string]: unknown;
};

type DependencyGraphProps = {
  edges?: RawEdge[];
  affectedServiceId?: string;
  suspectTargetId?: string;
  selectedNodeId?: string;
  onNodeSelect?: (nodeId?: string) => void;
};

type ServiceNodeData = {
  label: string;
  role: string;
  status: "affected" | "suspect" | "normal";
};

function ServiceNode({ data }: { data: ServiceNodeData }) {
  const styles = {
    affected: {
      border: "#fb7185",
      background: "#251923",
      text: "#fda4af",
      badge: "AFFECTED SERVICE",
      glow: "0 0 28px rgba(251,113,133,.13)",
    },
    suspect: {
      border: "#fbbf24",
      background: "#252116",
      text: "#fcd34d",
      badge: "SUSPECTED TRIGGER",
      glow: "0 0 28px rgba(251,191,36,.12)",
    },
    normal: {
      border: "#34465c",
      background: "#111a28",
      text: "#94a3b8",
      badge: "DEPENDENCY",
      glow: "0 8px 28px rgba(0,0,0,.2)",
    },
  }[data.status];

  return (
    <div
      style={{
        width: 205,
        overflow: "hidden",
        border: `1px solid ${styles.border}`,
        borderRadius: 14,
        background: styles.background,
        boxShadow: styles.glow,
        color: "#f8fafc",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{
          width: 8,
          height: 8,
          border: "2px solid #0b111b",
          background: styles.border,
        }}
      />

      <div style={{ padding: "15px 16px 14px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            marginBottom: 10,
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: 99,
              background: styles.border,
              boxShadow: `0 0 10px ${styles.border}70`,
            }}
          />
          <span
            style={{
              fontSize: 9,
              fontWeight: 800,
              letterSpacing: 1.1,
              color: styles.text,
            }}
          >
            {data.status === "normal" ? data.role.toUpperCase() : styles.badge}
          </span>
        </div>

        <div
          style={{
            fontSize: 14,
            fontWeight: 700,
            lineHeight: 1.45,
            overflowWrap: "anywhere",
          }}
        >
          {data.label}
        </div>

        <div
          style={{
            marginTop: 8,
            paddingTop: 9,
            borderTop: "1px solid rgba(148,163,184,.12)",
            fontSize: 10,
            color: "#94a3b8",
          }}
        >
          {data.status === "affected"
            ? "Associated with this incident"
            : data.status === "suspect"
              ? "Investigate supporting evidence"
              : "Connected service"}
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          width: 8,
          height: 8,
          border: "2px solid #0b111b",
          background: styles.border,
        }}
      />
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

export default function DependencyGraph({
  edges = [],
  affectedServiceId,
  suspectTargetId,
  selectedNodeId,
  onNodeSelect,
}: DependencyGraphProps) {
  const { nodes, flowEdges } = useMemo(() => {
    const names = new Map<string, string>();
    const adjacency = new Map<string, string[]>();
    const indegree = new Map<string, number>();
    const edgePairs: Array<{ source: string; target: string }> = [];

    for (const edge of edges) {
      const source =
        typeof edge.source === "string"
          ? edge.source
          : typeof edge.source_id === "string"
            ? edge.source_id
            : undefined;

      const target =
        typeof edge.target === "string"
          ? edge.target
          : typeof edge.target_id === "string"
            ? edge.target_id
            : undefined;

      if (!source || !target) continue;

      names.set(source, edge.source_name || names.get(source) || source);
      names.set(target, edge.target_name || names.get(target) || target);

      if (!adjacency.has(source)) adjacency.set(source, []);
      adjacency.get(source)!.push(target);

      if (!indegree.has(source)) indegree.set(source, 0);
      indegree.set(target, (indegree.get(target) || 0) + 1);

      edgePairs.push({ source, target });
    }

    // These IDs are provided by the investigation result, not invented.
    if (affectedServiceId) {
      names.set(
        affectedServiceId,
        names.get(affectedServiceId) || affectedServiceId
      );
    }

    if (suspectTargetId) {
      names.set(
        suspectTargetId,
        names.get(suspectTargetId) || suspectTargetId
      );
    }

    const ids = Array.from(names.keys());
    const depth = new Map<string, number>();
    const remainingIndegree = new Map(indegree);
    const queue: string[] = [];

    for (const id of ids) {
      if ((remainingIndegree.get(id) || 0) === 0) {
        depth.set(id, 0);
        queue.push(id);
      }
    }

    // Layer the graph from upstream services toward their dependencies.
    for (let i = 0; i < queue.length; i++) {
      const current = queue[i];

      for (const next of adjacency.get(current) || []) {
        depth.set(
          next,
          Math.max(depth.get(next) || 0, (depth.get(current) || 0) + 1)
        );

        remainingIndegree.set(
          next,
          (remainingIndegree.get(next) || 1) - 1
        );

        if (remainingIndegree.get(next) === 0) queue.push(next);
      }
    }

    // Preserve visibility for nodes involved in cycles.
    for (const id of ids) {
      if (!depth.has(id)) depth.set(id, 0);
    }

    const columns = new Map<number, string[]>();

    for (const id of ids) {
      const level = depth.get(id) || 0;
      if (!columns.has(level)) columns.set(level, []);
      columns.get(level)!.push(id);
    }

    const builtNodes: Node<ServiceNodeData>[] = [];

    for (const [level, columnIds] of Array.from(columns.entries()).sort(
      (a, b) => a[0] - b[0]
    )) {
      columnIds.forEach((id, index) => {
        const status: ServiceNodeData["status"] =
          id === affectedServiceId
            ? "affected"
            : id === suspectTargetId
              ? "suspect"
              : "normal";

        builtNodes.push({
          id,
          type: "service",
          position: { x: level * 290, y: index * 175 },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
          data: {
            label: names.get(id) || id,
            role: level === 0 ? "Entry point" : "Service",
            status,
          },
          selected: id === selectedNodeId,
        });
      });
    }

    const builtEdges: Edge[] = edgePairs.map((edge, index) => {
      const isSuspect = edge.target === suspectTargetId;
      const isAffected =
        edge.source === affectedServiceId ||
        edge.target === affectedServiceId;

      const stroke = isSuspect
        ? "#fbbf24"
        : isAffected
          ? "#fb7185"
          : "#52647c";

      return {
        id: `${edge.source}-${edge.target}-${index}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: isSuspect || isAffected,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
          width: 16,
          height: 16,
        },
        style: {
          stroke,
          strokeWidth: isSuspect || isAffected ? 2.2 : 1.5,
        },
      };
    });

    return { nodes: builtNodes, flowEdges: builtEdges };
  }, [edges, affectedServiceId, suspectTargetId, selectedNodeId]);

  if (nodes.length === 0) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-[#090c12] px-6 py-10 text-center">
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
          <Network size={24} className="text-slate-400" />
        </div>
        <p className="mt-4 text-sm font-semibold text-slate-200">
          No dependency topology available
        </p>
        <p className="mt-2 max-w-sm text-xs leading-5 text-slate-500">
          The investigation returned no usable service IDs or dependency edges.
          Check the topology response before drawing conclusions.
        </p>
      </div>
    );
  }

  return (
    <div
      className="tracefix-graph relative h-[430px] w-full overflow-hidden rounded-2xl border border-white/[0.09] md:h-[510px]"
      style={{
        background:
          "radial-gradient(ellipse at 50% 0%, rgba(34,211,238,.055), transparent 58%), #090e18",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.22, maxZoom: 1 }}
        minZoom={0.15}
        maxZoom={1.6}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        onNodeClick={(_, node) => onNodeSelect?.(node.id)}
        onPaneClick={() => onNodeSelect?.(undefined)}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#273449" gap={24} size={1} />
        <Controls position="bottom-left" showInteractive={false} />

        <MiniMap
          position="bottom-right"
          pannable
          zoomable
          nodeColor={(node) => {
            const data = node.data as ServiceNodeData;
            if (data.status === "affected") return "#fb7185";
            if (data.status === "suspect") return "#fbbf24";
            return "#52647c";
          }}
          maskColor="rgba(3, 7, 18, 0.78)"
          style={{
            background: "#101827",
            border: "1px solid #344155",
            borderRadius: 10,
          }}
        />

        <FlowPanel position="top-left">
          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#101827]/95 px-3 py-2 shadow-lg backdrop-blur">
            <GitBranch size={14} className="text-cyan-300" />
            <span className="text-[11px] font-semibold text-slate-200">
              Service topology
            </span>
            <span className="rounded-md bg-white/[0.06] px-2 py-1 text-[10px] text-slate-400">
              {nodes.length} nodes · {flowEdges.length} edges
            </span>
          </div>
        </FlowPanel>

        <FlowPanel position="top-right">
          <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#101827]/95 px-2.5 py-2 text-[10px] text-slate-400 shadow-lg backdrop-blur">
            <Maximize2 size={12} />
            Drag · Zoom · Pan
          </div>
        </FlowPanel>
      </ReactFlow>
    </div>
  );
}
