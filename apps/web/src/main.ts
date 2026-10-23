import "./style.css";
import ForceGraph3D, { type ForceGraph3DInstance } from "3d-force-graph";
import SpriteText from "three-spritetext";
import {
  domainFor,
  domains,
  endpointId,
  filterGraph,
  loadAllSystems,
  neighborhood,
  searchSystems,
  simulationData,
  type GraphPayload,
  type SimulationLink,
  type SimulationNode,
  type SystemSummary,
} from "./graph-data";
import { renderDetail, type SystemDetail } from "./system-detail";

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Application root is missing");
app.innerHTML = `
  <main class="explorer" aria-label="Software architecture explorer">
    <div id="graph" aria-label="Interactive force graph. Use Browse systems for a keyboard accessible list."></div>
    <header class="topbar glass">
      <a class="brand" href="/" aria-label="Mathen home"><span class="brand-mark" aria-hidden="true">m<span>·</span></span><span>mathen<small>Architecture atlas</small></span></a>
      <div class="search-wrap">
        <label class="sr-only" for="search">Search systems, descriptions, or card scope</label>
        <span class="search-icon" aria-hidden="true">⌕</span><input id="search" type="search" placeholder="Find a system…" autocomplete="off" aria-controls="search-results"><kbd>/</kbd>
        <div id="search-results" class="search-results glass" hidden></div>
      </div>
      <button id="catalog-open" class="quiet-button">Browse systems <span aria-hidden="true">↗</span></button>
    </header>

    <section class="graph-tools glass" aria-label="Graph controls">
      <div class="dimension-switch" aria-label="Graph dimensions"><button id="mode-2" aria-pressed="true">2D</button><button id="mode-3" aria-pressed="false">3D</button></div>
      <span class="tool-divider"></span>
      <button id="fit" title="Fit all visible systems">Fit</button>
      <button id="focus" disabled title="Focus selected system and its neighbors">Focus</button>
      <button id="pause" aria-pressed="false">Pause forces</button>
      <button id="reheat" title="Restart the force simulation">Reheat</button>
      <button id="reset" title="Clear filters and restore the overview">Reset</button>
    </section>

    <aside class="filters glass" aria-label="Navigation filters">
      <label for="domain">Navigation group</label><select id="domain"><option value="all">All domains</option>${domains.map((domain) => `<option value="${domain.id}">${domain.name}</option>`).join("")}</select>
      <label for="relation">Relation type</label><select id="relation"><option value="all">All relations</option></select>
      <button id="help-open" class="text-button">How to explore <span aria-hidden="true">?</span></button>
    </aside>

    <div id="state" class="state-panel glass" role="status"><span class="state-orbit" aria-hidden="true"></span><h1>Connecting the atlas</h1><p>Loading reviewed systems and their relationships…</p></div>
    <div id="metadata-notice" class="metadata-notice glass" role="status" hidden></div>
    <aside id="inspector" class="inspector glass" aria-label="Selection" hidden></aside>
    <footer class="map-footer">
      <div class="map-caption"><p class="eyebrow">An atlas of software systems</p><h1>Follow the structure.</h1><p id="gesture-hint">Drag a node to reshape its neighborhood. Scroll to explore.</p></div>
      <div class="map-key glass"><div id="counts" class="map-counts" aria-live="polite">Loading graph…</div><div class="edge-key"><span><i class="typed-line"></i>Typed relation</span><span><i class="legacy-line"></i>Legacy related</span></div><button id="legend-open" class="text-button">Node colors · navigation groups</button><span id="simulation-status" class="simulation-status" aria-live="polite">Preparing layout</span></div>
    </footer>
  </main>
  <dialog id="catalog-dialog" class="drawer" aria-labelledby="catalog-title"><div class="dialog-header"><div><p class="eyebrow">Keyboard explorer</p><h2 id="catalog-title">Browse systems</h2></div><button data-close aria-label="Close system catalog">✕</button></div><div class="catalog-search"><label for="catalog-search">Search the complete atlas</label><input id="catalog-search" type="search" placeholder="Name, description, or card scope…"></div><p id="catalog-count" class="muted"></p><div id="catalog-list" class="catalog-list"></div></dialog>
  <dialog id="detail-dialog" class="drawer detail-drawer" aria-labelledby="detail-title"><div class="dialog-header"><div><p class="eyebrow">Reviewed architecture card</p><h2 id="detail-title">System details</h2></div><button data-close aria-label="Close architecture card">✕</button></div><div id="detail-content"></div></dialog>
  <dialog id="help-dialog" class="help-dialog" aria-labelledby="help-title"><div class="dialog-header"><h2 id="help-title">Explore the atlas</h2><button data-close aria-label="Close exploration guide">✕</button></div><p>Drag any node: spring forces pull connected systems along with it. Scroll or pinch to zoom. Drag the background to pan in 2D or orbit in 3D.</p><p>Select a system to highlight its neighbors, then open its architecture card for features, mathematical views, trade-offs, and source evidence. Select a line to inspect the relation and its claim metadata.</p><p>Pause forces holds the layout while keeping navigation and selection available. Reheat lets the layout settle again. Focus frames the selected neighborhood; Reset restores all systems.</p><h3>Navigation groups</h3><p>Node colors and the domain filter are broad browsing categories. They are independent of evidence-backed card scope and do not imply a relationship.</p><div class="domain-legend">${domains.map((domain) => `<span><i style="--domain-color:${domain.color}"></i>${domain.name}</span>`).join("")}</div><h3>Read the edges</h3><p>Colored arrows are typed relations. Gray lines are legacy “related” links with no implied direction or causal claim. Filters only show relationships supplied by the atlas.</p><p>Use <kbd>/</kbd> to search, <kbd>Enter</kbd> to select the first result, and <kbd>Escape</kbd> to close a dialog. Browse systems offers every visible system and its relations as ordinary keyboard-accessible buttons.</p></dialog>
`;

function required<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing UI element: ${id}`);
  return element as T;
}

const host = required<HTMLDivElement>("graph");
const search = required<HTMLInputElement>("search");
const results = required<HTMLDivElement>("search-results");
const domainSelect = required<HTMLSelectElement>("domain");
const relationSelect = required<HTMLSelectElement>("relation");
const inspector = required<HTMLElement>("inspector");
const state = required<HTMLDivElement>("state");
const catalog = required<HTMLDialogElement>("catalog-dialog");
const detailDialog = required<HTMLDialogElement>("detail-dialog");
const helpDialog = required<HTMLDialogElement>("help-dialog");
const catalogSearch = required<HTMLInputElement>("catalog-search");
const detailContent = required<HTMLDivElement>("detail-content");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let canonical: GraphPayload = { nodes: [], edges: [] };
let systems: SystemSummary[] = [];
let visible: GraphPayload = canonical;
let graph: ForceGraph3DInstance<SimulationNode, SimulationLink> | undefined;
let selectedId: string | undefined;
let selectedEdge: SimulationLink | undefined;
let hoveredId: string | undefined;
let highlighted = new Set<string>();
let searchMatches: Set<string> | undefined;
let paused = reducedMotion.matches;
let dimensions: 2 | 3 = 2;
let autoFit = true;
let detailRequest = 0;
let metadataLoaded = false;
const labels = new Map<
  string,
  SpriteText & {
    visible: boolean;
    position: { set: (x: number, y: number, z: number) => void };
    material: { depthWrite: boolean };
  }
>();
const details = new Map<string, SystemDetail>();
const relationColors = ["#69d7c3", "#bca5f4", "#e7bb7d", "#7ab9ee", "#e699ad"];
const relationColor = (type: string) =>
  type === "related"
    ? "#657181"
    : relationColors[
        [...type].reduce((sum, character) => sum + character.charCodeAt(0), 0) %
          relationColors.length
      ];
const duration = () => (reducedMotion.matches ? 0 : 500);

function escapeHtml(value: string) {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character] ??
      character,
  );
}

function showDialog(dialog: HTMLDialogElement) {
  if (!dialog.open) dialog.showModal();
}
document.querySelectorAll<HTMLButtonElement>("[data-close]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog")?.close());
});
for (const dialog of [catalog, detailDialog, helpDialog]) {
  let opener: HTMLElement | null = null;
  dialog.addEventListener("beforetoggle", (event) => {
    if ((event as ToggleEvent).newState === "open")
      opener = document.activeElement as HTMLElement | null;
  });
  dialog.addEventListener("close", () => {
    if (dialog === detailDialog) detailRequest++;
    if (opener?.isConnected) opener.focus();
  });
}

function configureCamera() {
  if (!graph) return;
  const controls = graph.controls() as {
    enableRotate: boolean;
    enablePan: boolean;
    screenSpacePanning: boolean;
  };
  controls.enableRotate = dimensions === 3;
  controls.enablePan = true;
  controls.screenSpacePanning = true;
  required("gesture-hint").textContent =
    dimensions === 2
      ? "Drag a node to reshape its neighborhood. Scroll to explore."
      : "Drag a node to reshape its neighborhood. Drag space to orbit.";
}

function createGraph() {
  graph = new ForceGraph3D(host, {
    controlType: "orbit",
    rendererConfig: { antialias: true, alpha: true },
  }) as unknown as ForceGraph3DInstance<SimulationNode, SimulationLink>;
  graph
    .width(host.clientWidth)
    .height(host.clientHeight)
    .backgroundColor("#10192300")
    .showNavInfo(false)
    .numDimensions(2)
    .nodeRelSize(4)
    .nodeResolution(16)
    .nodeVal((node: SimulationNode) => 1.4 + Math.sqrt(node.degree) * 0.65)
    .nodeColor(nodeColor)
    .nodeOpacity(0.95)
    .nodeLabel((node) => {
      const label = document.createElement("span");
      label.textContent = node.name;
      return label;
    })
    .nodeThreeObjectExtend(true)
    .nodeThreeObject((node: SimulationNode) => {
      const label = new SpriteText(node.name, 4, "#e9f0ef") as SpriteText & {
        visible: boolean;
        position: { set: (x: number, y: number, z: number) => void };
        material: { depthWrite: boolean };
      };
      label.backgroundColor = "#111c29dd";
      label.padding = [2, 1];
      label.borderRadius = 2;
      label.position.set(0, 10, 0);
      label.material.depthWrite = false;
      label.visible = labelVisible(node);
      labels.set(node.id, label);
      return label;
    })
    .linkColor(linkColor)
    .linkOpacity(0.55)
    .linkWidth((link) =>
      selectedEdge?.id === link.id ? 2.5 : link.type === "related" ? 0.45 : 1.1,
    )
    .linkDirectionalArrowLength((link) => (link.type === "related" ? 0 : 3.5))
    .linkDirectionalArrowRelPos(0.8)
    .linkHoverPrecision(3)
    .linkLabel((link) => {
      const label = document.createElement("span");
      label.textContent = `${nodeName(endpointId(link.source))} → ${nodeName(endpointId(link.target))} · ${link.type.replaceAll("_", " ")}`;
      return label;
    })
    .d3AlphaDecay(0.035)
    .d3VelocityDecay(0.38)
    .d3AlphaMin(0.005)
    .warmupTicks(reducedMotion.matches ? 100 : 35)
    .cooldownTicks(paused ? 0 : 180)
    .cooldownTime(8000)
    .onNodeClick((node) => selectNode(node.id))
    .onNodeHover((node) => {
      hoveredId = node?.id;
      host.style.cursor = node ? "pointer" : "";
      updateStyles();
    })
    .onLinkClick((link) => selectEdge(link))
    .onBackgroundClick(() => clearSelection())
    .onNodeDrag(() => {
      autoFit = false;
      if (!paused) graph?.d3ReheatSimulation();
    })
    .onNodeDragEnd((node) => {
      node.fx = undefined;
      node.fy = undefined;
      node.fz = undefined;
      if (!paused) reheat();
    })
    .onEngineStop(() => {
      required("simulation-status").textContent = paused
        ? "Forces paused · navigation active"
        : "Layout settled · drag to reshape";
      if (autoFit) {
        fit();
        autoFit = false;
      }
    });
  graph.d3Force("charge")?.strength(-140).distanceMax(650);
  graph
    .d3Force("link")
    ?.distance((link: SimulationLink) => (link.type === "related" ? 85 : 65))
    .strength((link: SimulationLink) => (link.type === "related" ? 0.12 : 0.35));
  graph.d3Force("center")?.strength(0.08);
  configureCamera();
  new ResizeObserver(() => {
    graph?.width(host.clientWidth).height(host.clientHeight);
  }).observe(host);
  // Manual navigation should never be interrupted by a later automatic fit.
  host.addEventListener("pointerdown", () => {
    autoFit = false;
  });
  host.addEventListener(
    "wheel",
    () => {
      autoFit = false;
    },
    { passive: true },
  );
  updatePauseButton();
}

function nodeName(id: string) {
  return canonical.nodes.find((node) => node.id === id)?.name ?? id;
}
function nodeColor(node: SimulationNode) {
  const active =
    (!highlighted.size || highlighted.has(node.id)) &&
    (!searchMatches || searchMatches.has(node.id));
  return active ? domainFor(node.id).color : "#34404c";
}
function linkColor(link: SimulationLink) {
  if (selectedEdge?.id === link.id) return "#ffffff";
  if (
    highlighted.size &&
    (!highlighted.has(endpointId(link.source)) || !highlighted.has(endpointId(link.target)))
  )
    return "#29323d";
  return relationColor(link.type);
}
function labelVisible(node: SimulationNode) {
  return (
    node.id === hoveredId ||
    node.id === selectedId ||
    highlighted.has(node.id) ||
    Boolean(searchMatches?.has(node.id)) ||
    (!highlighted.size && !searchMatches && node.degree >= 7)
  );
}
function updateStyles() {
  if (!graph) return;
  graph
    .nodeColor(nodeColor)
    .linkColor(linkColor)
    .linkWidth((link) =>
      selectedEdge?.id === link.id ? 2.5 : link.type === "related" ? 0.45 : 1.1,
    );
  for (const node of graph.graphData().nodes) {
    const label = labels.get(node.id);
    if (label) {
      label.visible = labelVisible(node);
      label.color = node.id === selectedId ? "#9ff5dc" : "#e9f0ef";
    }
  }
}

function updateGraph() {
  visible = filterGraph(canonical, domainSelect.value, relationSelect.value);
  if (selectedId && !visible.nodes.some((node) => node.id === selectedId)) clearSelection();
  selectedEdge = undefined;
  const next = simulationData(visible);
  const old = new Map(graph?.graphData().nodes.map((node) => [node.id, node]));
  for (const node of next.nodes)
    Object.assign(
      node,
      old.get(node.id)
        ? {
            x: old.get(node.id)?.x,
            y: old.get(node.id)?.y,
            z: dimensions === 2 ? 0 : old.get(node.id)?.z,
          }
        : {},
    );
  labels.clear();
  graph?.graphData(next);
  highlighted = selectedId ? neighborhood(visible, selectedId) : new Set();
  if (selectedId) renderNodeInspector(selectedId);
  else inspector.hidden = true;
  required("counts").textContent =
    `${visible.nodes.length} systems / ${visible.edges.length} relations`;
  if (visible.nodes.length) state.hidden = true;
  else {
    state.hidden = false;
    state.innerHTML = `<h2>No systems in this group</h2><p>Choose another navigation group or reset the atlas.</p><button id="empty-reset">Reset atlas</button>`;
    required("empty-reset").onclick = reset;
  }
  updateSearch();
  renderCatalog();
  updateStyles();
  if (!paused) reheat();
  else graph?.cooldownTicks(0);
}

function fit() {
  graph?.zoomToFit(duration(), window.innerWidth < 640 ? 65 : 110);
}
function focus() {
  if (selectedId)
    graph?.zoomToFit(duration(), window.innerWidth < 640 ? 75 : 140, (node) =>
      highlighted.has(node.id),
    );
}
function updatePauseButton() {
  const button = required<HTMLButtonElement>("pause");
  button.setAttribute("aria-pressed", String(paused));
  button.textContent = paused ? "Resume forces" : "Pause forces";
}
function reheat() {
  paused = false;
  updatePauseButton();
  graph?.cooldownTicks(reducedMotion.matches ? 70 : 180).d3ReheatSimulation();
  required("simulation-status").textContent = "Forces settling…";
}
function clearSelection() {
  selectedId = undefined;
  selectedEdge = undefined;
  highlighted.clear();
  inspector.hidden = true;
  required<HTMLButtonElement>("focus").disabled = true;
  updateStyles();
}
function selectNode(id: string) {
  selectedId = id;
  selectedEdge = undefined;
  highlighted = neighborhood(visible, id);
  required<HTMLButtonElement>("focus").disabled = !visible.nodes.some((node) => node.id === id);
  results.hidden = true;
  renderNodeInspector(id);
  updateStyles();
}
function renderNodeInspector(id: string) {
  const system = details.get(id) ?? systems.find((item) => item.id === id);
  const edges = visible.edges.filter((edge) => edge.source === id || edge.target === id);
  inspector.hidden = false;
  inspector.innerHTML = `<button class="inspector-close" aria-label="Clear selection">✕</button><p class="eyebrow">${escapeHtml(domainFor(id).name)} · navigation group</p><h2>${escapeHtml(nodeName(id))}</h2><p class="selection-summary">${escapeHtml(system?.summary ?? "Open the architecture card for reviewed scope, features, and evidence.")}</p><div class="tag-row">${system ? system.scope.map((scope) => `<span>${escapeHtml(scope)}</span>`).join("") : "<span>Card scope loading on demand</span>"}</div><div class="inspector-bottom"><span>${edges.length} visible relation${edges.length === 1 ? "" : "s"}</span><button id="open-card" class="primary-button">Open card ↗</button></div>`;
  inspector.querySelector(".inspector-close")?.addEventListener("click", clearSelection);
  required("open-card").onclick = () => void openDetail(id);
}
function selectEdge(edge: SimulationLink) {
  selectedEdge = edge;
  selectedId = undefined;
  highlighted = new Set([endpointId(edge.source), endpointId(edge.target)]);
  required<HTMLButtonElement>("focus").disabled = true;
  inspector.hidden = false;
  inspector.innerHTML = `<button class="inspector-close" aria-label="Clear selection">✕</button><p class="eyebrow">${edge.type === "related" ? "Legacy association" : "Typed relation"}</p><h2>${escapeHtml(edge.type.replaceAll("_", " "))}</h2><p>${escapeHtml(nodeName(endpointId(edge.source)))} ${edge.type === "related" ? "—" : "→"} ${escapeHtml(nodeName(endpointId(edge.target)))}</p><div class="tag-row">${[
    edge.claim_type,
    edge.claim_status,
  ]
    .filter(Boolean)
    .map((item) => `<span>${escapeHtml(item!)}</span>`)
    .join(
      "",
    )}</div>${edge.notes ? `<p class="selection-summary">${escapeHtml(edge.notes)}</p>` : ""}<p class="muted">${edge.evidence_ids?.length ? `Evidence: ${edge.evidence_ids.map(escapeHtml).join(", ")}` : "No relation evidence supplied."}</p><button id="source-card" class="primary-button">Open source card & evidence ↗</button>`;
  inspector.querySelector(".inspector-close")?.addEventListener("click", clearSelection);
  required("source-card").onclick = () => void openDetail(endpointId(edge.source));
  updateStyles();
}

function updateSearch() {
  const matches = searchSystems(visible.nodes, systems, search.value);
  searchMatches = search.value.trim() ? new Set(matches.map((node) => node.id)) : undefined;
  results.hidden = !search.value.trim() || document.activeElement !== search;
  results.innerHTML = matches.length
    ? `${matches
        .slice(0, 8)
        .map(
          (node) =>
            `<button data-result="${escapeHtml(node.id)}"><strong>${escapeHtml(node.name)}</strong><small>${escapeHtml(domainFor(node.id).name)}</small></button>`,
        )
        .join("")}<button id="all-results">Browse all ${matches.length} results ↗</button>`
    : `<p>No matching systems in this navigation group.</p>`;
  results.querySelectorAll<HTMLButtonElement>("[data-result]").forEach(
    (button) =>
      (button.onclick = () => {
        selectNode(button.dataset.result!);
        focus();
      }),
  );
  const all = document.getElementById("all-results");
  if (all)
    all.onclick = () => {
      catalogSearch.value = search.value;
      renderCatalog();
      showDialog(catalog);
      results.hidden = true;
    };
  updateStyles();
}
function renderCatalog() {
  const nodes = canonical.nodes.length
    ? visible.nodes
    : systems.map((system) => ({ id: system.id, name: system.name, type: "system" as const }));
  const matches = searchSystems(nodes, systems, catalogSearch.value);
  required("catalog-count").textContent =
    `${matches.length} systems · ${domainSelect.selectedOptions[0].textContent}`;
  const metadata = new Map(systems.map((system) => [system.id, system]));
  required("catalog-list").innerHTML = matches.length
    ? matches
        .map(
          (node) =>
            `<article class="catalog-item"><span class="eyebrow">${escapeHtml(domainFor(node.id).name)}</span><h3>${escapeHtml(node.name)}</h3><p>${escapeHtml(metadata.get(node.id)?.summary ?? "Reviewed card details available on demand.")}</p><div><button data-card="${escapeHtml(node.id)}">Read card ↗</button><button data-locate="${escapeHtml(node.id)}">Locate on graph</button></div></article>`,
        )
        .join("")
    : `<p class="muted">No systems match this search. Change the query or navigation group.</p>`;
  required("catalog-list")
    .querySelectorAll<HTMLButtonElement>("[data-card]")
    .forEach((button) => (button.onclick = () => void openDetail(button.dataset.card!)));
  required("catalog-list")
    .querySelectorAll<HTMLButtonElement>("[data-locate]")
    .forEach(
      (button) =>
        (button.onclick = () => {
          catalog.close();
          selectNode(button.dataset.locate!);
          focus();
          required("open-card").focus();
        }),
    );
}

async function openDetail(id: string) {
  const request = ++detailRequest;
  required("detail-title").textContent = nodeName(id);
  detailContent.innerHTML = `<p role="status" class="loading-message">Loading architecture card…</p>`;
  showDialog(detailDialog);
  try {
    let system = details.get(id);
    if (!system) {
      const response = await fetch(`/api/systems/${encodeURIComponent(id)}`);
      if (!response.ok) throw new Error(`Card API returned ${response.status}`);
      system = ((await response.json()) as { data: SystemDetail }).data;
      details.set(id, system);
    }
    if (request !== detailRequest) return;
    detailContent.innerHTML = renderDetail(system, canonical);
    detailContent
      .querySelectorAll<HTMLButtonElement>("[data-related]")
      .forEach((button) => (button.onclick = () => void openDetail(button.dataset.related!)));
    if (selectedId === id) renderNodeInspector(id);
  } catch {
    if (request !== detailRequest) return;
    detailContent.innerHTML = `<p role="alert">Unable to load this architecture card.</p><button id="retry-detail" class="primary-button">Retry card</button>`;
    required("retry-detail").onclick = () => void openDetail(id);
  }
}

function reset() {
  domainSelect.value = "all";
  relationSelect.value = "all";
  search.value = "";
  catalogSearch.value = "";
  clearSelection();
  updateGraph();
  autoFit = true;
  fit();
}

function validateMetadata() {
  if (!metadataLoaded || !canonical.nodes.length) return;
  const ids = new Set(systems.map((system) => system.id));
  const missing = canonical.nodes.filter((node) => !ids.has(node.id));
  if (missing.length)
    metadataError(
      `${missing.length} system summaries unavailable. All graph nodes remain searchable by name; cards load on demand.`,
    );
}
function metadataError(message: string) {
  const notice = required("metadata-notice");
  notice.hidden = false;
  notice.innerHTML = `<span>${escapeHtml(message)}</span><button id="retry-metadata">Retry summaries</button>`;
  required("retry-metadata").onclick = () => void loadMetadata();
}
async function loadMetadata() {
  required("metadata-notice").hidden = true;
  try {
    systems = await loadAllSystems();
    metadataLoaded = true;
    validateMetadata();
    updateSearch();
    renderCatalog();
    if (selectedId) renderNodeInspector(selectedId);
  } catch {
    metadataError(
      "System summaries unavailable. Search by name or open a card for its actual scope.",
    );
  }
}
async function loadGraph() {
  state.hidden = false;
  state.innerHTML = `<span class="state-orbit" aria-hidden="true"></span><h1>Connecting the atlas</h1><p>Loading systems and relationships…</p>`;
  try {
    const response = await fetch("/api/graph");
    if (!response.ok) throw new Error(`Graph API returned ${response.status}`);
    const payload = (await response.json()) as GraphPayload | { data: GraphPayload };
    canonical = "data" in payload ? payload.data : payload;
    if (!Array.isArray(canonical.nodes) || !Array.isArray(canonical.edges))
      throw new Error("Invalid graph payload");
    if (!graph) createGraph();
    relationSelect.innerHTML = `<option value="all">All relations</option>${[
      ...new Set(canonical.edges.map((edge) => edge.type)),
    ]
      .sort()
      .map(
        (type) =>
          `<option value="${escapeHtml(type)}">${type === "related" ? "Legacy related" : escapeHtml(type.replaceAll("_", " "))}</option>`,
      )
      .join("")}`;
    autoFit = true;
    updateGraph();
    validateMetadata();
  } catch {
    graph?._destructor();
    graph = undefined;
    host.replaceChildren();
    state.hidden = false;
    state.innerHTML = `<p class="eyebrow">Atlas unavailable</p><h1>We couldn’t open the graph.</h1><p>Retry the connection or browse architecture cards.</p><div class="state-actions"><button id="retry-graph" class="primary-button">Retry graph</button><button id="fallback-catalog">Browse systems</button></div>`;
    required("retry-graph").onclick = () => void loadGraph();
    required("fallback-catalog").onclick = () => {
      renderCatalog();
      showDialog(catalog);
    };
  }
}

search.addEventListener("input", updateSearch);
search.addEventListener("focus", updateSearch);
search.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    results.hidden = true;
    search.blur();
  }
  if (event.key === "ArrowDown") {
    event.preventDefault();
    results.querySelector<HTMLButtonElement>("button")?.focus();
  }
  if (event.key === "Enter") {
    const first = searchSystems(visible.nodes, systems, search.value)[0];
    if (first) {
      selectNode(first.id);
      focus();
      search.blur();
    }
  }
});
document.addEventListener("pointerdown", (event) => {
  if (!(event.target as Element).closest(".search-wrap")) results.hidden = true;
});
document.addEventListener("keydown", (event) => {
  if (
    event.key === "/" &&
    !document.querySelector("dialog[open]") &&
    !(
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      event.target instanceof HTMLSelectElement
    )
  ) {
    event.preventDefault();
    search.focus();
  }
});
catalogSearch.addEventListener("input", renderCatalog);
required("catalog-open").onclick = () => {
  renderCatalog();
  showDialog(catalog);
};
required("help-open").onclick = required("legend-open").onclick = () => showDialog(helpDialog);
domainSelect.onchange = () => {
  updateGraph();
  autoFit = true;
  fit();
};
relationSelect.onchange = () => updateGraph();
required("fit").onclick = fit;
required("focus").onclick = focus;
required("reset").onclick = reset;
required("reheat").onclick = reheat;
required("pause").onclick = () => {
  paused = !paused;
  updatePauseButton();
  if (paused) {
    graph?.cooldownTicks(0);
    required("simulation-status").textContent = "Forces paused · navigation active";
  } else reheat();
};
for (const mode of [2, 3] as const)
  required(`mode-${mode}`).onclick = () => {
    dimensions = mode;
    required("mode-2").setAttribute("aria-pressed", String(mode === 2));
    required("mode-3").setAttribute("aria-pressed", String(mode === 3));
    graph?.numDimensions(mode);
    configureCamera();
    if (mode === 2) graph?.cameraPosition({ x: 0, y: 0, z: 700 }, { x: 0, y: 0, z: 0 }, duration());
    if (!paused) reheat();
    else graph?.cooldownTicks(0);
    autoFit = true;
    fit();
  };
reducedMotion.addEventListener("change", () => {
  if (reducedMotion.matches) {
    paused = true;
    graph?.cooldownTicks(0);
    updatePauseButton();
  }
});
void loadGraph();
void loadMetadata();
