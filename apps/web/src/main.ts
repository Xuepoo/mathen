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

type GraphNode = { id: string; name: string; type: "system" };

type GraphEdge = {
  source: string;
  target: string;
  type: string;
  claim_type?: string;
  claim_status?: string;
  evidence_ids?: string[];
  notes?: string;
};

type GraphPayload = { nodes: GraphNode[]; edges: GraphEdge[] };

type Feature = {
  id: string;
  name: string;
  category: string;
  claim_type: string;
  description: string;
  benefits: string[];
  costs: string[];
  evidence_ids: string[];
};

type SystemDetail = SystemSummary & {
  features: Feature[];
  mathematical_views: Array<{
    model: string;
    question: string;
    assumptions: string[];
    claim_type: string;
    evidence_ids: string[];
  }>;
  evidence: Array<{ id: string; title: string; uri: string; kind: string }>;
};

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Application root is missing");

app.innerHTML = `
  <header class="site-header shell">
    <a class="brand" href="/" aria-label="Mathen home">
      <span class="brand-mark">M</span>
      <span><strong>Mathen</strong><small>Architecture intelligence</small></span>
    </a>
    <nav class="site-nav" aria-label="Primary navigation">
      <a href="#explore">Explore</a>
      <a href="#catalog">Catalog</a>
      <a href="https://github.com/Xuepoo/mathen" target="_blank" rel="noreferrer">Source ↗</a>
    </nav>
  </header>
  <main>
    <section class="hero shell">
      <div class="hero-copy">
        <p class="eyebrow"><span class="live-dot"></span> Evidence-backed architecture graph</p>
        <h1>See how software<br /><em>takes shape.</em></h1>
        <p class="hero-lead">Explore the structures, boundaries, and trade-offs behind the systems we build. Every connection is grounded in a reviewed Architecture Card.</p>
        <div class="hero-actions"><a class="primary-button" href="#explore">Open the graph <span>↓</span></a><a class="text-link" href="#catalog">Browse systems →</a></div>
      </div>
      <div class="hero-orbit" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit-core">M</div><span class="orbit-node orbit-node-one">D</span><span class="orbit-node orbit-node-two">G</span><span class="orbit-node orbit-node-three">S</span></div>
    </section>
    <section class="stats-bar shell" aria-label="Knowledge base statistics">
      <div><strong id="system-count">—</strong><span>reviewed systems</span></div>
      <div><strong id="edge-count">—</strong><span>architecture relations</span></div>
      <div><strong id="feature-count">—</strong><span>reusable features</span></div>
      <div><strong id="evidence-count">—</strong><span>evidence sources</span></div>
    </section>
    <section id="explore" class="explore-section shell">
      <div class="section-heading"><div><p class="eyebrow">01 / Relational map</p><h2>Architecture graph</h2></div><p class="section-note">Trace patterns across reviewed systems.<br />Select a node to reveal its neighborhood.</p></div>
      <div class="graph-workspace">
        <div class="graph-toolbar">
          <label class="toolbar-search"><span>⌕</span><input id="graph-search" type="search" placeholder="Find a system…" /></label>
          <div class="toolbar-controls"><label for="relation-filter">Relations</label><select id="relation-filter"><option value="all">All types</option></select><label for="layout-select">Layout</label><select id="layout-select"><option value="cose">Network</option><option value="concentric">Concentric</option><option value="circle">Circle</option><option value="grid">Grid</option></select><button id="graph-focus" class="toolbar-button" type="button" disabled>Focus selected</button><button id="graph-reset" class="toolbar-button icon-button" type="button" aria-label="Reset graph view">↺</button></div>
        </div>
        <div class="graph-body"><div id="graph-canvas" class="graph-canvas" role="img" aria-label="Interactive architecture graph"></div><aside id="graph-inspector" class="graph-inspector"><div class="inspector-empty"><span class="inspector-icon">⌁</span><p class="eyebrow">Graph inspector</p><h3>Choose a system or relation</h3><p>Click a node to see its connected architecture patterns. Click an edge to inspect the claim behind it.</p></div></aside></div>
        <div class="graph-footer"><span><i class="legend-dot"></i> System</span><span><i class="legend-line"></i> Evidence-backed relation</span><span id="graph-hint">Scroll to zoom · drag to pan</span></div>
      </div>
    </section>
    <section id="catalog" class="catalog-section shell">
      <div class="section-heading"><div><p class="eyebrow">02 / Reviewed catalog</p><h2>Systems worth studying</h2></div><p class="section-note">Search by system, workload, or architectural boundary.</p></div>
      <div class="catalog-layout"><aside class="catalog-sidebar"><label class="search-label" for="system-search">Search the knowledge base</label><label class="catalog-search"><span>⌕</span><input id="system-search" type="search" placeholder="embedded, isolation, storage…" /></label><div class="catalog-filter-label">Domains</div><div id="scope-filters" class="scope-filters"><button class="scope-chip active" data-scope="all" type="button">All systems</button></div></aside><div id="system-list" class="system-list" aria-live="polite"></div></div>
    </section>
    <section id="detail-panel" class="detail-section shell" aria-live="polite"><div class="empty-state"><p class="eyebrow">03 / Architecture card</p><h2>Select a system to inspect it.</h2><p>Features, mathematical views, trade-offs, and primary evidence will appear here.</p></div></section>
  </main>
  <footer class="site-footer shell"><span>Mathen · a research prototype for software architecture</span><span>D1-backed reviewed knowledge · <a href="https://github.com/Xuepoo/mathen" target="_blank" rel="noreferrer">Open source ↗</a></span></footer>
`;

const systemList = required<HTMLDivElement>("system-list");
const systemCount = required<HTMLElement>("system-count");
const edgeCount = required<HTMLElement>("edge-count");
const featureCount = required<HTMLElement>("feature-count");
const evidenceCount = required<HTMLElement>("evidence-count");
const detailPanel = required<HTMLElement>("detail-panel");
const graphCanvas = required<HTMLDivElement>("graph-canvas");
const graphInspector = required<HTMLElement>("graph-inspector");
const graphSearch = required<HTMLInputElement>("graph-search");
const systemSearch = required<HTMLInputElement>("system-search");
const relationFilter = required<HTMLSelectElement>("relation-filter");
const layoutSelect = required<HTMLSelectElement>("layout-select");
const graphFocus = required<HTMLButtonElement>("graph-focus");
const graphReset = required<HTMLButtonElement>("graph-reset");
const scopeFilters = required<HTMLDivElement>("scope-filters");

let systems: SystemSummary[] = [];
let graphData: GraphPayload = { nodes: [], edges: [] };
let graph: Core | undefined;
let selectedNodeId: string | undefined;
let activeScope = "all";
let detailRequest = 0;

await loadSystems();
await loadFeatureStats();
await loadGraph();
systemSearch.addEventListener("input", () => renderSystems(systemSearch.value));
graphSearch.addEventListener("input", () => searchGraph(graphSearch.value));
relationFilter.addEventListener("change", () => applyGraphVisibility());
layoutSelect.addEventListener("change", () => runLayout(layoutSelect.value));
graphFocus.addEventListener("click", () => focusSelectedNode());
graphReset.addEventListener("click", () => resetGraph());

async function loadSystems() {
  try {
    const response = await fetch("/api/systems");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const payload = (await response.json()) as { data: SystemSummary[] };
    systems = payload.data;
    systemCount.textContent = String(systems.length);
    buildScopeFilters();
    renderSystems("");
  } catch (error) {
    systemList.innerHTML = `<p class="error-message">Unable to load reviewed systems.</p>`;
    console.error(error);
  }
}

async function loadGraph() {
  try {
    const response = await fetch("/api/graph");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const payload = (await response.json()) as GraphPayload | { data: GraphPayload };
    graphData = "data" in payload ? payload.data : payload;
    edgeCount.textContent = String(graphData.edges.length);
    renderGraph();
  } catch (error) {
    graphCanvas.innerHTML = `<p class="graph-error">Unable to load the architecture graph.</p>`;
    console.error(error);
  }
}

async function loadFeatureStats() {
  try {
    const response = await fetch("/api/features?limit=200");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const payload = (await response.json()) as {
      data: Array<{ evidence_ids?: string[] }>;
    };
    const evidenceIds = new Set(payload.data.flatMap((feature) => feature.evidence_ids ?? []));
    featureCount.textContent = String(payload.data.length);
    evidenceCount.textContent = String(evidenceIds.size);
  } catch (error) {
    featureCount.textContent = "—";
    evidenceCount.textContent = "—";
    console.error(error);
  }
}

function renderGraph() {
  const relationTypes = [...new Set(graphData.edges.map((edge) => edge.type))].sort();
  relationFilter.innerHTML = `<option value="all">All types</option>${relationTypes.map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`).join("")}`;
  const elements: ElementDefinition[] = [
    ...graphData.nodes.map((node) => ({
      group: "nodes" as const,
      data: {
        id: node.id,
        label: node.name,
        scope: systems.find((system) => system.id === node.id)?.scope[0] ?? "system",
      },
    })),
    ...graphData.edges.map((edge, index) => ({
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
  graph?.destroy();
  graph = cytoscape({
    container: graphCanvas,
    elements,
    minZoom: 0.25,
    maxZoom: 4,
    wheelSensitivity: 0.22,
    style: [
      {
        selector: "node",
        style: {
          "background-color": "#d5f35f",
          "border-color": "#f2ffb2",
          "border-width": 2,
          color: "#f5f7ed",
          label: "data(label)",
          "font-size": 11,
          "font-weight": 600,
          "text-wrap": "wrap",
          "text-max-width": "130px",
          "text-valign": "bottom",
          "text-margin-y": 10,
          "overlay-opacity": 0,
          width: 28,
          height: 28,
        },
      },
      {
        selector: "node:selected",
        style: {
          "background-color": "#ffb86b",
          "border-color": "#fff1d5",
          "border-width": 4,
          width: 36,
          height: 36,
        },
      },
      { selector: "node.dimmed", style: { opacity: 0.18 } },
      {
        selector: "edge",
        style: {
          width: 2,
          "line-color": "#5e7081",
          "target-arrow-color": "#a6bac8",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "data(type)",
          color: "#b5c4cc",
          "font-size": 9,
          "text-background-color": "#121b24",
          "text-background-opacity": 0.9,
          "text-background-padding": "4px",
          "text-rotation": "autorotate",
          "overlay-opacity": 0,
        },
      },
      {
        selector: "edge:selected",
        style: {
          width: 4,
          "line-color": "#ffb86b",
          "target-arrow-color": "#ffb86b",
          color: "#fff1d5",
        },
      },
      { selector: "edge.dimmed", style: { opacity: 0.08 } },
    ],
    layout: layoutOptions("cose"),
  });
  graph.on("tap", "node", (event) => selectGraphNode(event.target.id()));
  graph.on("tap", "edge", (event) => showGraphEdge(event.target.data()));
  graph.on("tap", (event) => {
    if (event.target === graph) showGraphGuide();
  });
  applyGraphVisibility();
  updateGraphHint();
}

function selectGraphNode(id: string) {
  if (!graph) return;
  selectedNodeId = id;
  graphFocus.disabled = false;
  const node = graphData.nodes.find((item) => item.id === id);
  graph.elements().removeClass("dimmed");
  graph
    .nodes()
    .not(`#${escapeSelector(id)}`)
    .addClass("dimmed");
  graph.edges().forEach((edge) => {
    if (edge.source().id() !== id && edge.target().id() !== id) edge.addClass("dimmed");
  });
  showGraphNode(id, node);
  void loadDetail(id);
}

function showGraphNode(id: string, node?: GraphNode) {
  const system = systems.find((item) => item.id === id);
  const degree = graph?.getElementById(id).connectedEdges().length ?? 0;
  graphInspector.innerHTML = `<div class="inspector-label"><span class="inspector-node-dot"></span><p class="eyebrow">Selected system</p></div><h3>${escapeHtml(node?.name ?? id)}</h3><p>${escapeHtml(system?.summary ?? "Open the architecture card below for the complete evidence trail.")}</p><div class="inspector-metrics"><span><strong>${degree}</strong> relations</span><span><strong>${system?.scope.length ?? 0}</strong> domains</span></div><button class="inspector-link" data-system-id="${escapeHtml(id)}" type="button">Open architecture card <span>↓</span></button>`;
  graphInspector.querySelector("button")?.addEventListener("click", () => void loadDetail(id));
}

function showGraphEdge(edge: Record<string, unknown>) {
  graph?.elements().removeClass("dimmed");
  const metadata = [edge.claimType, edge.claimStatus].filter(
    (value): value is string => typeof value === "string",
  );
  const evidenceIds = Array.isArray(edge.evidenceIds)
    ? edge.evidenceIds.filter((value): value is string => typeof value === "string")
    : [];
  graphInspector.innerHTML = `<div class="inspector-label"><span class="inspector-edge-line"></span><p class="eyebrow">Selected relation</p></div><h3>${escapeHtml(String(edge.type ?? "relation"))}</h3><p class="relation-path">${escapeHtml(`${String(edge.source)} → ${String(edge.target)}`)}</p>${metadata.length ? `<div class="tag-row">${metadata.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>` : ""}${typeof edge.notes === "string" ? `<p class="graph-note">${escapeHtml(edge.notes)}</p>` : ""}${evidenceIds.length ? `<div class="evidence-pills"><span class="eyebrow">Evidence</span>${evidenceIds.map((id) => `<span class="evidence-pill">${escapeHtml(id)}</span>`).join("")}</div>` : `<p class="muted-message">Legacy relation without typed evidence metadata.</p>`}`;
}

function showGraphGuide() {
  selectedNodeId = undefined;
  graphFocus.disabled = true;
  graph?.elements().removeClass("dimmed");
  graphInspector.innerHTML = `<div class="inspector-empty"><span class="inspector-icon">⌁</span><p class="eyebrow">Graph inspector</p><h3>Choose a system or relation</h3><p>Click a node to see its connected architecture patterns. Click an edge to inspect the claim behind it.</p></div>`;
}

function applyGraphVisibility() {
  if (!graph) return;
  const type = relationFilter.value;
  graph.edges().forEach((edge) => {
    edge.style("display", type === "all" || edge.data("type") === type ? "element" : "none");
  });
  updateGraphHint();
}

function searchGraph(query: string) {
  if (!graph) return;
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    graph.elements().removeClass("dimmed");
    return;
  }
  const matches = graph
    .nodes()
    .filter((node) => String(node.data("label")).toLowerCase().includes(normalized));
  graph.nodes().forEach((node) => {
    node.toggleClass("dimmed", !matches.contains(node));
  });
  graph.edges().forEach((edge) => {
    edge.toggleClass(
      "dimmed",
      !matches.contains(edge.source()) && !matches.contains(edge.target()),
    );
  });
}

function runLayout(name: string) {
  graph?.layout(layoutOptions(name)).run();
}

function focusSelectedNode() {
  if (!graph || !selectedNodeId) return;
  const node = graph.getElementById(selectedNodeId);
  graph.animate({
    fit: { eles: node.closedNeighborhood(), padding: 70 },
    duration: 450,
  });
}

function resetGraph() {
  graphSearch.value = "";
  relationFilter.value = "all";
  selectedNodeId = undefined;
  graphFocus.disabled = true;
  graph?.elements().removeClass("dimmed");
  graph?.edges().forEach((edge) => {
    edge.style("display", "element");
  });
  runLayout(layoutSelect.value);
  showGraphGuide();
}

function layoutOptions(name: string) {
  const base = {
    name: name as "cose" | "circle" | "grid" | "concentric",
    animate: false,
    padding: 54,
  };
  return name === "cose"
    ? {
        ...base,
        idealEdgeLength: 160,
        nodeRepulsion: 8000,
        edgeElasticity: 100,
      }
    : base;
}

function updateGraphHint() {
  const visibleEdges = graphData.edges.filter(
    (edge) => relationFilter.value === "all" || edge.type === relationFilter.value,
  ).length;
  const message = graphData.edges.length
    ? `${visibleEdges} relation${visibleEdges === 1 ? "" : "s"} shown · scroll to zoom`
    : "No typed relations yet · browse the catalog below";
  const hint = document.querySelector<HTMLElement>("#graph-hint");
  if (hint) hint.textContent = message;
}

function buildScopeFilters() {
  const scopes = [...new Set(systems.flatMap((system) => system.scope))].sort();
  scopeFilters.innerHTML = `<button class="scope-chip active" data-scope="all" type="button">All systems</button>${scopes
    .slice(0, 8)
    .map(
      (scope) =>
        `<button class="scope-chip" data-scope="${escapeHtml(scope)}" type="button">${escapeHtml(scope)}</button>`,
    )
    .join("")}`;
  scopeFilters.querySelectorAll<HTMLButtonElement>("button").forEach((button) =>
    button.addEventListener("click", () => {
      activeScope = button.dataset.scope ?? "all";
      scopeFilters
        .querySelectorAll("button")
        .forEach((item) => item.classList.toggle("active", item === button));
      renderSystems(systemSearch.value);
    }),
  );
}

function renderSystems(query: string) {
  const normalized = query.trim().toLowerCase();
  const visible = systems.filter((system) => {
    const matchesScope = activeScope === "all" || system.scope.includes(activeScope);
    const searchable = [system.name, system.summary, ...system.scope].join(" ").toLowerCase();
    return matchesScope && searchable.includes(normalized);
  });
  systemList.innerHTML = visible.length
    ? visible.map(systemCard).join("")
    : `<p class="muted-message">No reviewed systems match this view.</p>`;
  systemList
    .querySelectorAll<HTMLButtonElement>("button[data-system-id]")
    .forEach((button) =>
      button.addEventListener("click", () => void loadDetail(button.dataset.systemId ?? "")),
    );
}

function systemCard(system: SystemSummary) {
  const relationCount = graphData.edges.filter(
    (edge) => edge.source === system.id || edge.target === system.id,
  ).length;
  return `<button class="system-card" data-system-id="${escapeHtml(system.id)}"><span class="system-card-top"><span class="card-kicker">${escapeHtml(system.scope[0] ?? "system")}</span><span class="system-degree">${relationCount} relation${relationCount === 1 ? "" : "s"}</span></span><strong>${escapeHtml(system.name)}</strong><span>${escapeHtml(system.summary)}</span><span class="card-arrow">↗</span></button>`;
}

async function loadDetail(id: string) {
  const requestId = ++detailRequest;
  detailPanel.innerHTML = `<div class="loading-state"><span class="spinner"></span> Loading architecture card…</div>`;
  try {
    const response = await fetch(`/api/systems/${encodeURIComponent(id)}`);
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const payload = (await response.json()) as { data: SystemDetail };
    if (requestId === detailRequest) detailPanel.innerHTML = renderDetail(payload.data);
  } catch (error) {
    if (requestId === detailRequest)
      detailPanel.innerHTML = `<div class="error-message">Unable to load this architecture card.</div>`;
    console.error(error);
  }
}

function renderDetail(system: SystemDetail) {
  const evidenceById = new Map(system.evidence.map((item) => [item.id, item]));
  return `<article class="architecture-card"><div class="detail-header"><div><p class="eyebrow">03 / Architecture card</p><h2>${escapeHtml(system.name)}</h2><p class="lead">${escapeHtml(system.summary)}</p></div><span class="review-badge"><i></i> Reviewed</span></div><div class="tag-row">${system.scope.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div><div class="detail-metrics"><span><strong>${system.features.length}</strong> features</span><span><strong>${system.mathematical_views.length}</strong> mathematical views</span><span><strong>${system.evidence.length}</strong> evidence sources</span></div><section class="detail-block"><div class="block-heading"><p class="eyebrow">Transferable structure</p><h3>Reusable features</h3></div><div class="feature-grid">${system.features.map((feature) => renderFeature(feature, evidenceById)).join("")}</div></section><section class="detail-block"><div class="block-heading"><p class="eyebrow">Formal lenses</p><h3>Mathematical views</h3></div><div class="view-list">${system.mathematical_views.map((view) => `<div class="view-card"><div class="feature-meta"><span class="card-kicker">${escapeHtml(view.claim_type)}</span><span class="evidence-count">${view.evidence_ids.length} evidence</span></div><h4>${escapeHtml(view.model)}</h4><p>${escapeHtml(view.question)}</p><details><summary>Assumptions (${view.assumptions.length})</summary><ul>${view.assumptions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></details><div class="evidence-pills">${view.evidence_ids.map((id) => evidencePill(id, evidenceById)).join("")}</div></div>`).join("")}</div></section><section class="detail-block evidence-block"><div class="block-heading"><p class="eyebrow">Primary sources</p><h3>Evidence trail</h3></div><ul class="evidence-list">${system.evidence.map((item) => `<li><span class="evidence-kind">${escapeHtml(item.kind)}</span><div><a href="${escapeHtml(item.uri)}" target="_blank" rel="noreferrer">${escapeHtml(item.title)} ↗</a><small>${escapeHtml(item.id)}</small></div></li>`).join("")}</ul></section></article>`;
}

function renderFeature(
  feature: Feature,
  evidenceById: Map<string, SystemDetail["evidence"][number]>,
) {
  return `<div class="feature-card"><div class="feature-meta"><span class="card-kicker">${escapeHtml(feature.category)}</span><span class="claim-type">${escapeHtml(feature.claim_type)}</span></div><h4>${escapeHtml(feature.name)}</h4><p>${escapeHtml(feature.description)}</p><details><summary>Benefits and costs</summary><p><strong>Benefits:</strong> ${escapeHtml(feature.benefits.join("; "))}</p><p><strong>Costs:</strong> ${escapeHtml(feature.costs.join("; "))}</p></details><div class="evidence-pills">${feature.evidence_ids.map((id) => evidencePill(id, evidenceById)).join("")}</div></div>`;
}

function evidencePill(id: string, evidenceById: Map<string, SystemDetail["evidence"][number]>) {
  const evidence = evidenceById.get(id);
  return evidence
    ? `<a class="evidence-pill" href="${escapeHtml(evidence.uri)}" target="_blank" rel="noreferrer">${escapeHtml(id)} ↗</a>`
    : `<span class="evidence-pill">${escapeHtml(id)}</span>`;
}

function required<T extends Element>(id: string): T {
  const element = document.querySelector<T>(`#${id}`);
  if (!element) throw new Error(`Required UI element is missing: ${id}`);
  return element;
}

function escapeSelector(value: string) {
  return value.replace(/([!"#$%&'()*+,./:;<=>?@[\\\]^`{|}~])/g, "\\$1");
}

function escapeHtml(value: string) {
  return value.replace(
    /[&<>'"]/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] ??
      character,
  );
}
