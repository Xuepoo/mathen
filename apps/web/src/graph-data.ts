export type SystemSummary = {
  id: string;
  name: string;
  version_context: string | null;
  summary: string;
  scope: string[];
  related_systems: string[];
  scope_context?: Record<string, unknown>;
};

export type GraphNode = { id: string; name: string; type: "system" };
export type GraphEdge = {
  source: string;
  target: string;
  type: string;
  claim_type?: string;
  claim_status?: string;
  lifecycle?: Record<string, unknown>;
  evidence_ids?: string[];
  notes?: string;
};
export type GraphPayload = { nodes: GraphNode[]; edges: GraphEdge[] };
/** Navigation categories only: these are not card scope or evidence-backed relations. */
export const domains = [
  {
    id: "web",
    name: "Web / UI",
    color: "#66dbc5",
    systems:
      "angular capacitor chromium django electron expo express fastapi firefox flutter gtk ionic javafx laravel nestjs nextjs qt rails react react-native spring-boot storybook svelte tauri vue wails wxwidgets",
  },
  {
    id: "languages",
    name: "Languages / runtimes",
    color: "#bdacff",
    systems:
      "ast-grep boost cpython deno gcc glibc go libuv llvm lua luajit musl node protobuf ruby rust rustc tree-sitter v8 wasm wasmtime zig",
  },
  {
    id: "data",
    name: "Data",
    color: "#e9ba76",
    systems:
      "airflow cassandra celery clickhouse cockroachdb dagster dbt duckdb elasticsearch etcd flink foundationdb hadoop influxdb kafka leveldb minio mongodb mosquitto mysql-server nats postgresql pulsar rabbitmq redis rocksdb seaweedfs spark sqlite supabase temporal tidb tikv zookeeper",
  },
  {
    id: "infrastructure",
    name: "Infrastructure",
    color: "#7fb7f4",
    systems:
      "apisix argo-cd authentik caddy cilium clickhouse-operator consul containerd crossplane docker dovecot envoy firecracker freebsd grpc gvisor haproxy helm istio kata-containers keycloak kong kubernetes linux minix nginx oauth2-proxy openbao openbsd openssl opentelemetry plan9 postfix prometheus qemu quiche runc stalwart systemd terraform traefik vault velero wayland wireguard xv6-public",
  },
  {
    id: "tools",
    name: "Tools",
    color: "#f49eaf",
    systems:
      "alacritty bazel busybox coreutils curl esbuild fd ghostty git i3 hyprland jq just kitty lsp niri neovim playwright ripgrep rollup sway vite vscode webpack wezterm yq",
  },
  {
    id: "graphics",
    name: "Graphics / ML",
    color: "#a7d480",
    systems:
      "blender ffmpeg gstreamer imagemagick jax mlflow opencv opengl pytorch scikit-learn sdl tensorflow threejs transformers vulkan webgl",
  },
  { id: "others", name: "Others", color: "#b1bbc9", systems: "" },
] as const;

export function domainFor(id: string) {
  return (
    domains.find((domain) => domain.systems.split(" ").includes(id)) ?? domains[domains.length - 1]
  );
}

export function filterGraph(graph: GraphPayload, domain = "all", relation = "all"): GraphPayload {
  const nodes = graph.nodes.filter((node) => domain === "all" || domainFor(node.id).id === domain);
  const ids = new Set(nodes.map((node) => node.id));
  return {
    nodes,
    edges: graph.edges.filter(
      (edge) =>
        ids.has(edge.source) &&
        ids.has(edge.target) &&
        (relation === "all" || edge.type === relation),
    ),
  };
}
export type SimulationNode = GraphNode & {
  x?: number;
  y?: number;
  z?: number;
  fx?: number;
  fy?: number;
  fz?: number;
  degree: number;
};
export type SimulationLink = Omit<GraphEdge, "source" | "target"> & {
  id: string;
  source: string | SimulationNode;
  target: string | SimulationNode;
};

export function endpointId(endpoint: string | SimulationNode): string {
  return typeof endpoint === "string" ? endpoint : endpoint.id;
}

export function neighborhood(graph: GraphPayload, id: string, relation = "all") {
  const ids = new Set([id]);
  for (const edge of graph.edges) {
    if (relation !== "all" && edge.type !== relation) continue;
    if (edge.source === id) ids.add(edge.target);
    if (edge.target === id) ids.add(edge.source);
  }
  return ids;
}

/** Force libraries mutate nodes and replace link endpoints; never lend them API objects. */
export function simulationData(graph: GraphPayload, relation = "all") {
  const known = new Set(graph.nodes.map((node) => node.id));
  const degree = new Map<string, number>();
  const links: SimulationLink[] = graph.edges.flatMap((edge, index) => {
    if (!known.has(edge.source) || !known.has(edge.target)) return [];
    if (relation !== "all" && edge.type !== relation) return [];
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
    return [
      {
        ...edge,
        evidence_ids: edge.evidence_ids?.slice(),
        id: `edge-${index}`,
      },
    ];
  });
  return {
    nodes: graph.nodes.map((node) => ({
      ...node,
      degree: degree.get(node.id) ?? 0,
    })) as SimulationNode[],
    links,
  };
}

export function searchSystems(nodes: GraphNode[], systems: SystemSummary[], query: string) {
  const metadata = new Map(systems.map((system) => [system.id, system]));
  const normalized = query.trim().toLowerCase();
  return nodes.filter((node) => {
    const system = metadata.get(node.id);
    return [node.id, node.name, system?.summary ?? "", ...(system?.scope ?? [])]
      .join(" ")
      .toLowerCase()
      .includes(normalized);
  });
}

/** Fetch every page before publishing metadata, including nodes beyond the API default. */
export async function loadAllSystems(
  request: (input: string) => Promise<Response> = fetch,
): Promise<SystemSummary[]> {
  const systems = new Map<string, SystemSummary>();
  for (let offset = 0; ; offset += 100) {
    const response = await request(`/api/systems?limit=100&offset=${offset}`);
    if (!response.ok) throw new Error(`Systems API returned ${response.status}`);
    const { data } = (await response.json()) as { data: SystemSummary[] };
    if (!Array.isArray(data)) throw new Error("Invalid systems response");
    const previousSize = systems.size;
    for (const system of data) systems.set(system.id, system);
    if (data.length < 100) return [...systems.values()];
    if (systems.size === previousSize) throw new Error("Systems API did not advance pagination");
  }
}
