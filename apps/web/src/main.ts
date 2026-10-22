import "./style.css";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";

type SystemSummary = {
  id: string;
  name: string;
  version_context: string | null;
  summary: string;
  scope: string[];
  related_systems: string[];
};

type GraphPayload = {
  nodes: Array<{ id: string; name: string; type: "system" }>;
  edges: Array<{
    source: string;
    target: string;
    type: string;
    claim_type?: string;
    claim_status?: string;
    evidence_ids?: string[];
    notes?: string;
  }>;
};

type Feature = {
  id: string;
  name: string;
  category: string;
  claim_type: string;
  description: string;
  benefits: string[];
  costs: string[];
};

type SystemDetail = SystemSummary & {
  features: Feature[];
  mathematical_views: Array<{
    model: string;
    question: string;
    assumptions: string[];
    claim_type: string;
  }>;
  evidence: Array<{ title: string; uri: string; kind: string }>;
};

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Application root is missing");

app.innerHTML = `
  <header class="site-header">
    <div>
      <p class="eyebrow">Architecture knowledge graph</p>
      <h1>Mathen</h1>
      <p class="subtitle">Translate software systems into reusable structures, mathematical views, and evidence-backed trade-offs.</p>
    </div>
    <a class="github-link" href="https://github.com/Xuepoo/mathen" target="_blank" rel="noreferrer">GitHub ↗</a>
  </header>
  <section class="graph-workspace" aria-labelledby="graph-title">
    <div class="graph-heading">
      <div><p class="eyebrow">Relational map</p><h2 id="graph-title">Architecture graph</h2><p class="graph-intro">Explore systems as connected architecture cards. Drag nodes, pan the canvas, or scroll to zoom.</p></div>
      <div class="graph-actions">
        <label for="relation-filter">Show relations</label>
        <select id="relation-filter" class="relation-filter"><option value="all">All relation types</option></select>
        <button id="graph-reset" class="graph-button" type="button">Reset view</button>
      </div>
    </div>
    <div class="graph-layout">
      <div id="graph-canvas" class="graph-canvas" role="img" aria-label="Interactive architecture graph"></div>
      <aside id="graph-inspector" class="graph-inspector"><p class="eyebrow">Graph guide</p><h3>Select a node or edge</h3><p>Nodes represent reviewed systems. Edges retain their relation type and claim metadata.</p><div class="graph-legend"><span><i class="legend-dot"></i> System</span><span><i class="legend-line"></i> Relation</span></div></aside>
    </div>
  </section>
  <main class="layout">
    <section class="catalog-panel">
      <div class="panel-heading">
        <div><p class="eyebrow">Catalog</p><h2>Systems</h2></div>
        <span id="system-count" class="count-badge">—</span>
      </div>
      <label class="search-label" for="system-search">Search systems and architecture claims</label>
      <input id="system-search" class="search-input" type="search" placeholder="Try embedded, vectorized, KVM..." />
      <div id="system-list" class="system-list" aria-live="polite"></div>
    </section>
    <section id="detail-panel" class="detail-panel" aria-live="polite">
      <div class="empty-state"><p class="eyebrow">Start exploring</p><h2>Select a system</h2><p>Browse the catalog to inspect architecture features, mathematical views, trade-offs, and evidence.</p></div>
    </section>
  </main>
  <footer><span>Mathen is a research prototype.</span><span>D1-backed structured knowledge · Vector search ready</span></footer>
`;

const searchInputElement = document.querySelector<HTMLInputElement>("#system-search");
const systemListElement = document.querySelector<HTMLDivElement>("#system-list");
const systemCountElement = document.querySelector<HTMLSpanElement>("#system-count");
const detailPanelElement = document.querySelector<HTMLElement>("#detail-panel");
const graphCanvasElement = document.querySelector<HTMLDivElement>("#graph-canvas");
const graphInspectorElement = document.querySelector<HTMLElement>("#graph-inspector");
const relationFilterElement = document.querySelector<HTMLSelectElement>("#relation-filter");
const graphResetElement = document.querySelector<HTMLButtonElement>("#graph-reset");
if (
  !searchInputElement ||
  !systemListElement ||
  !systemCountElement ||
  !detailPanelElement ||
  !graphCanvasElement ||
  !graphInspectorElement ||
  !relationFilterElement ||
  !graphResetElement
) {
  throw new Error("Required UI elements are missing");
}
const searchInput = searchInputElement;
const systemList = systemListElement;
const systemCount = systemCountElement;
const detailPanel = detailPanelElement;
const graphCanvas = graphCanvasElement;
const graphInspector = graphInspectorElement;
const relationFilter = relationFilterElement;
const graphReset = graphResetElement;

let systems: SystemSummary[] = [];
let graph: Core | undefined;
await loadSystems();
await loadGraph();
searchInput.addEventListener("input", () => renderSystems(searchInput.value));
relationFilter.addEventListener("change", () => filterGraph(relationFilter.value));
graphReset.addEventListener("click", () => graph?.fit(undefined, 42));

async function loadSystems() {
  try {
    const response = await fetch("/api/systems");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const payload = (await response.json()) as { data: SystemSummary[] };
    systems = payload.data;
    systemCount.textContent = String(systems.length);
    renderSystems("");
  } catch (error) {
    systemList.innerHTML = `<p class="error-message">Unable to load the local API. Start it with <code>bun run dev</code>.</p>`;
    console.error(error);
  }
}

async function loadGraph() {
  try {
    const response = await fetch("/api/graph");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const payload = (await response.json()) as GraphPayload | { data: GraphPayload };
    const data = "data" in payload ? payload.data : payload;
    renderGraph(data);
  } catch (error) {
    graphCanvas.innerHTML = `<p class="graph-error">Unable to load the architecture graph.</p>`;
    console.error(error);
  }
}

function renderGraph(data: GraphPayload) {
  const relationTypes = [...new Set(data.edges.map((edge) => edge.type))].sort();
  relationFilter.innerHTML = `<option value="all">All relation types</option>${relationTypes.map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`).join("")}`;
  const elements: ElementDefinition[] = [
    ...data.nodes.map((node) => ({
      group: "nodes" as const,
      data: { id: node.id, label: node.name, type: node.type },
    })),
    ...data.edges.map((edge, index) => ({
      group: "edges" as const,
      data: {
        id: `edge-${index}-${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        claimType: edge.claim_type,
        claimStatus: edge.claim_status,
        evidenceIds: edge.evidence_ids,
        notes: edge.notes,
      },
    })),
  ];
  graph = cytoscape({
    container: graphCanvas,
    elements,
    minZoom: 0.35,
    maxZoom: 3,
    wheelSensitivity: 0.25,
    style: [
      {
        selector: "node",
        style: {
          "background-color": "#38bdf8",
          "border-color": "#b9ecff",
          "border-width": 2,
          color: "#e8ecf4",
          label: "data(label)",
          "font-size": 11,
          "text-wrap": "wrap",
          "text-max-width": "120px",
          "text-valign": "bottom",
          "text-margin-y": 9,
          "overlay-opacity": 0,
        },
      },
      {
        selector: "node:selected",
        style: {
          "background-color": "#fbbf24",
          "border-color": "#fff7cc",
          "border-width": 3,
        },
      },
      {
        selector: "edge",
        style: {
          width: 2,
          "line-color": "#49647f",
          "target-arrow-color": "#7dd3fc",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "data(type)",
          color: "#93a4ba",
          "font-size": 9,
          "text-background-color": "#0d1117",
          "text-background-opacity": 0.85,
          "text-background-padding": "3px",
          "text-rotation": "autorotate",
          "overlay-opacity": 0,
        },
      },
      {
        selector: "edge:selected",
        style: {
          width: 4,
          "line-color": "#fbbf24",
          "target-arrow-color": "#fbbf24",
          color: "#fff7cc",
        },
      },
    ],
    layout: {
      name: "cose",
      animate: false,
      padding: 42,
      idealEdgeLength: 150,
      nodeRepulsion: 7000,
      edgeElasticity: 100,
    },
  });
  graph.on("tap", "node", (event) => {
    const nodeId = event.target.id();
    showGraphNode(
      nodeId,
      data.nodes.find((node) => node.id === nodeId),
    );
    void loadDetail(nodeId);
  });
  graph.on("tap", "edge", (event) => showGraphEdge(event.target.data()));
  graph.on("tap", (event) => {
    if (event.target === graph) showGraphGuide();
  });
}

function filterGraph(type: string) {
  if (!graph) return;
  graph.edges().forEach((edge) => {
    edge.style("display", type === "all" || edge.data("type") === type ? "element" : "none");
  });
}

function showGraphNode(id: string, node?: GraphPayload["nodes"][number]) {
  graphInspector.innerHTML = `<p class="eyebrow">Selected system</p><h3>${escapeHtml(node?.name ?? id)}</h3><p>${escapeHtml(systems.find((system) => system.id === id)?.summary ?? "Open the architecture card below for features, views, and evidence.")}</p><button class="inspector-link" data-system-id="${escapeHtml(id)}" type="button">Open architecture card ↓</button>`;
  graphInspector.querySelector("button")?.addEventListener("click", () => void loadDetail(id));
}

function showGraphEdge(edge: Record<string, unknown>) {
  const metadata = [edge.claimType, edge.claimStatus].filter(
    (value): value is string => typeof value === "string",
  );
  graphInspector.innerHTML = `<p class="eyebrow">Selected relation</p><h3>${escapeHtml(String(edge.type ?? "relation"))}</h3><p>${escapeHtml(`${String(edge.source)} → ${String(edge.target)}`)}</p>${metadata.length ? `<div class="tag-row">${metadata.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>` : ""}${typeof edge.notes === "string" ? `<p class="graph-note">${escapeHtml(edge.notes)}</p>` : ""}`;
}

function showGraphGuide() {
  graphInspector.innerHTML = `<p class="eyebrow">Graph guide</p><h3>Select a node or edge</h3><p>Nodes represent reviewed systems. Edges retain their relation type and claim metadata.</p><div class="graph-legend"><span><i class="legend-dot"></i> System</span><span><i class="legend-line"></i> Relation</span></div>`;
}

function renderSystems(query: string) {
  const normalized = query.trim().toLowerCase();
  const visible = systems.filter((system) => {
    const searchable = [system.name, system.summary, ...system.scope].join(" ").toLowerCase();
    return searchable.includes(normalized);
  });
  systemList.innerHTML = visible.length
    ? visible.map(systemCard).join("")
    : `<p class="muted-message">No matching systems.</p>`;
  systemList.querySelectorAll<HTMLButtonElement>("button[data-system-id]").forEach((button) => {
    button.addEventListener("click", () => loadDetail(button.dataset.systemId ?? ""));
  });
}

function systemCard(system: SystemSummary) {
  return `<button class="system-card" data-system-id="${escapeHtml(system.id)}"><span class="card-kicker">${escapeHtml(system.scope[0] ?? "system")}</span><strong>${escapeHtml(system.name)}</strong><span>${escapeHtml(system.summary)}</span></button>`;
}

async function loadDetail(id: string) {
  detailPanel.innerHTML = `<div class="loading-state">Loading architecture card…</div>`;
  const response = await fetch(`/api/systems/${encodeURIComponent(id)}`);
  if (!response.ok) {
    detailPanel.innerHTML = `<div class="error-message">Unable to load this system.</div>`;
    return;
  }
  const payload = (await response.json()) as { data: SystemDetail };
  detailPanel.innerHTML = renderDetail(payload.data);
}

function renderDetail(system: SystemDetail) {
  return `<article><p class="eyebrow">Architecture card</p><h2>${escapeHtml(system.name)}</h2><p class="lead">${escapeHtml(system.summary)}</p><div class="tag-row">${system.scope.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div><section class="detail-section"><h3>Reusable features</h3><div class="feature-grid">${system.features.map(renderFeature).join("")}</div></section><section class="detail-section"><h3>Mathematical views</h3>${system.mathematical_views.map((view) => `<div class="view-card"><div class="card-kicker">${escapeHtml(view.claim_type)}</div><h4>${escapeHtml(view.model)}</h4><p>${escapeHtml(view.question)}</p><details><summary>Assumptions</summary><ul>${view.assumptions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></details></div>`).join("")}</section><section class="detail-section"><h3>Evidence</h3><ul class="evidence-list">${system.evidence.map((item) => `<li><span>${escapeHtml(item.kind)}</span><a href="${escapeHtml(item.uri)}" target="_blank" rel="noreferrer">${escapeHtml(item.title)} ↗</a></li>`).join("")}</ul></section></article>`;
}

function renderFeature(feature: Feature) {
  return `<div class="feature-card"><div class="feature-meta"><span class="card-kicker">${escapeHtml(feature.category)}</span><span class="claim-type">${escapeHtml(feature.claim_type)}</span></div><h4>${escapeHtml(feature.name)}</h4><p>${escapeHtml(feature.description)}</p><details><summary>Benefits and costs</summary><p><strong>Benefits:</strong> ${escapeHtml(feature.benefits.join("; "))}</p><p><strong>Costs:</strong> ${escapeHtml(feature.costs.join("; "))}</p></details></div>`;
}

function escapeHtml(value: string) {
  return value.replace(
    /[&<>'"]/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] ??
      character,
  );
}
