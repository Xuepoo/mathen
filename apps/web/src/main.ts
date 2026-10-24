import "./style.css";
import type { ForceGraph3DInstance } from "3d-force-graph";
import { createLabelPool } from "./graph-labels";
import { lazyModule } from "./lazy-module";
import {
  frameNodes,
  seedCoordinates,
  worldUnitsPerPixel,
} from "./graph-viewport";
import { applyView, expandOneHop, applyPin, type Pin } from "./graph-view";
import { movablePanel } from "./movable-panel";
import { configureNavigation } from "./navigation-controls";
import { centeredCamera } from "./graph-camera";
import {
  domainFor,
  domains,
  filterGraph,
  loadAllSystems,
  type GraphPayload,
  type SystemSummary,
} from "./graph-data";
import {
  endpointId,
  filterModelGraph,
  loadModelGraph,
  modelSimulationData,
  neighborhood,
  searchNodes,
  simulationEdgeId,
  type ExplorerPayload,
  type ModelGraphPayload,
  type SimulationLink,
  type SimulationNode,
} from "./model-data";
import { renderDetail, type SystemDetail } from "./system-detail";

type TurnstileWidget = {
  render: (
    container: HTMLElement,
    options: {
      sitekey: string;
      action: string;
      callback: (token: string) => void;
      "error-callback": () => void;
      "expired-callback": () => void;
    },
  ) => string;
  reset: (widgetId?: string) => void;
};

declare global {
  interface Window {
    turnstile?: TurnstileWidget;
  }
}

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Application root is missing");
app.innerHTML = `
  <main class="explorer" aria-label="Software architecture explorer">
    <div id="graph" role="region" aria-label="Interactive force graph. Use Browse systems for a keyboard accessible list."></div>
    <div id="graph-names" aria-hidden="true"></div>
    <header class="topbar glass">
      <a class="brand" href="/"><span class="brand-mark" aria-hidden="true">m<span>·</span></span><span>mathen<small>Architecture atlas</small></span></a>
      <div class="search-wrap">
        <label class="sr-only" for="search">Search systems, descriptions, or card scope</label>
        <span class="search-icon" aria-hidden="true">⌕</span><input id="search" type="search" placeholder="Find a system…" autocomplete="off" aria-controls="search-results"><kbd>/</kbd>
        <div id="search-results" class="search-results glass" hidden></div>
      </div>
      <button id="catalog-open" class="quiet-button">Browse systems <span aria-hidden="true">↗</span></button>
      <a class="github-link" href="https://github.com/Xuepoo/mathen" target="_blank" rel="noopener noreferrer" aria-label="Mathen on GitHub" title="Mathen on GitHub">
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.25c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.74.08-.74 1.2.08 1.84 1.23 1.84 1.23 1.07 1.83 2.8 1.3 3.48 1 .11-.78.42-1.3.76-1.6-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.38 1.23-3.22-.12-.3-.53-1.52.12-3.17 0 0 1-.32 3.3 1.23a11.4 11.4 0 0 1 6 0c2.3-1.55 3.3-1.23 3.3-1.23.65 1.65.24 2.87.12 3.17.76.84 1.23 1.91 1.23 3.22 0 4.62-2.8 5.64-5.48 5.94.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58A12 12 0 0 0 12 .5Z"/></svg>
      </a>
    </header>

    <section class="graph-tools glass" aria-label="Graph controls">
      <div class="dimension-switch graph-mode-switch" role="group" aria-label="Graph mode"><button id="graph-systems" aria-pressed="true">Systems</button><button id="graph-models" aria-pressed="false">Math models</button></div>
      <div class="dimension-switch" role="group" aria-label="Graph dimensions"><button id="mode-2" aria-pressed="true">2D</button><button id="mode-3" aria-pressed="false">3D</button></div>
      <span class="tool-divider"></span>
      <button id="fit" title="Fit all visible nodes">Fit</button>
      <button id="names" aria-pressed="true" title="Toggle all names or highlighted names">Names: all</button>
      <button id="focus" disabled title="Focus selected node and its neighbors">Focus</button>
      <button id="pause" aria-pressed="false">Pause forces</button>
      <button id="reheat" title="Restart the force simulation">Reheat</button>
      <button id="reset" title="Clear filters and restore the overview">Reset</button>
      <button id="restore-hidden" hidden>Restore hidden</button>
    </section>

    <aside class="filters glass" aria-label="Navigation filters">
      <label for="domain">Navigation group</label><select id="domain"><option value="all">All domains</option>${domains.map((domain) => `<option value="${domain.id}">${domain.name}</option>`).join("")}</select>
      <label for="relation">Relation type</label><select id="relation"><option value="all">All relations</option></select>
      <button id="help-open" class="text-button">Research position · explore <span aria-hidden="true">?</span></button>
    </aside>

    <div id="state" class="state-panel glass" role="status"><span class="state-orbit" aria-hidden="true"></span><h1>Connecting the atlas</h1><p>Loading reviewed systems and their relationships…</p></div>
    <div id="metadata-notice" class="metadata-notice glass" role="status" hidden></div>
    <dialog id="access-dialog" class="access-dialog" aria-labelledby="access-title">
      <div class="dialog-header"><div><p class="eyebrow">Public access check</p><h2 id="access-title">Verify to explore Mathen</h2></div></div>
      <p>Complete the Cloudflare check to protect the shared architecture database from automated query floods.</p>
      <div id="turnstile-widget" class="turnstile-widget"></div>
      <p id="access-status" class="muted" role="status">Preparing verification…</p>
    </dialog>
    <aside id="inspector" class="inspector glass" aria-label="Selection" hidden></aside>
    <div id="node-menu" class="node-menu glass" role="menu" aria-label="Node actions" hidden></div>
    <footer class="map-footer">
      <div class="map-caption"><p id="gesture-hint">Drag nodes · scroll to zoom · drag space to pan</p></div>
      <div class="map-key glass"><div id="counts" class="map-counts" aria-live="polite">Loading graph…</div><div class="edge-key"><span><i class="typed-line"></i>Typed relation</span><span><i class="legacy-line"></i>Legacy related</span></div><button id="legend-open" class="text-button">Node colors · navigation groups</button><span id="simulation-status" class="simulation-status" aria-live="polite">Preparing layout</span></div>
    </footer>
  </main>
  <dialog id="catalog-dialog" class="drawer" aria-labelledby="catalog-title"><div class="dialog-header"><div><p class="eyebrow">Keyboard explorer</p><h2 id="catalog-title">Browse systems</h2></div><button data-close aria-label="Close system catalog">✕</button></div><div class="catalog-search"><label for="catalog-search">Search the complete atlas</label><input id="catalog-search" type="search" placeholder="Name, description, or card scope…"></div><p id="catalog-count" class="muted"></p><div id="catalog-list" class="catalog-list"></div></dialog>
  <dialog id="detail-dialog" class="drawer detail-drawer" aria-labelledby="detail-title"><div class="dialog-header"><div><p class="eyebrow">Reviewed architecture card</p><h2 id="detail-title">System details</h2></div><button data-close aria-label="Close architecture card">✕</button></div><div id="detail-content"></div></dialog>
  <dialog id="help-dialog" class="help-dialog" aria-labelledby="help-title"><div class="dialog-header"><div><p class="eyebrow">Evidence to experiment</p><h2 id="help-title">Research position</h2></div><button data-close aria-label="Close research position">✕</button></div><p>Mathen studies whether a reviewed bridge between evidence, architectural microstructure, and checkable contracts can make cross-domain comparison more useful and falsifiable. The loop is <strong>evidence → deterministic observation → reviewed microstructure → contract → bounded composition → macro candidate → experiment → new evidence</strong>, with human review and question reformulation throughout.</p><h3>Different tools, different claims</h3><p>Humans reframe questions and review trade-offs. Deterministic analysis records reproducible repository signals. LLMs explain evidence and draft candidate abstractions. Graph analysis can expose typed neighborhoods and paths; vector retrieval can recover terminology variants. Neither retrieval signal is proof, compatibility, causality, or historical influence. Contracts check supplied model data, while experiments measure behavior within a stated workload, version, environment, and deployment scope.</p><p><code>vector similarity ≠ graph position ≠ LLM interpretation ≠ contract classification ≠ runtime compatibility</code></p><h3>Comparisons are bounded analogies</h3><p>Chemistry and biology may share a qualitative network motif, but not parameters, substrates, laws, units, or causal semantics: a representation can transfer a question about connectivity without transferring the mechanism that produces behavior. Materials science helps explain why software <em>microstructure</em> names bounded units, interfaces, conditions, and properties; it does not import crystal structure or thermodynamic laws. Taxonomy organizes vocabulary for retrieval and review; it does not discover natural kinds or establish dependency, compatibility, lineage, or historical influence.</p><h3>Discovery is a candidate, not a conclusion</h3><p>Discovery means surfacing a path, mapping, counterexample, or question not recorded in the current dataset. A vector neighbor, graph path, larger graph, or fluent LLM proposal is not architectural novelty. Stronger novelty or usefulness claims need a defined reference set, source review, explicit scope, and an experiment. Current cards, contracts, drafts, and read-only API/MCP boundaries do not provide automatic proofs, calibrated originality scores, universal quality scores, or validation of the full loop. Graph projection and novelty benchmarks remain planned work; see the <a href="https://github.com/Xuepoo/mathen/issues/47" target="_blank" rel="noopener noreferrer">MTH-0117 plan</a> and <a href="https://github.com/Xuepoo/mathen/issues/48" target="_blank" rel="noopener noreferrer">MTH-0118 plan</a>.</p><h3>Explore the atlas</h3><p>Drag any node: spring forces pull connected systems along with it. Scroll or pinch to zoom. Drag the background to pan in 2D or orbit in 3D.</p><p>Select a system to highlight its neighbors, then open its architecture card for features, mathematical views, trade-offs, and source evidence. Select a line to inspect the relation and its claim metadata.</p><p>Node colors and the domain filter are broad browsing categories. They are independent of evidence-backed card scope and do not imply a relationship.</p><div class="domain-legend">${domains.map((domain) => `<span><i style="--domain-color:${domain.color}"></i>${domain.name}</span>`).join("")}</div><h3>Read the edges</h3><p>Colored arrows are typed relations. Gray lines are legacy “related” links with no implied direction or causal claim. Filters only show relationships supplied by the atlas.</p><p>Use <kbd>/</kbd> to search, <kbd>Enter</kbd> to select the first result, and <kbd>Escape</kbd> to close a dialog. Deployment origins are configurable and scope access or reproduction; they do not establish semantic validity.</p></dialog>
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
const panel = movablePanel(inspector);
const nodeMenu = required<HTMLDivElement>("node-menu");
let menuOpener: HTMLElement | null = null;
const pins = new Map<string, Pin>();
const hiddenNodes = new Set<string>();
const expandedNodes = new Set<string>();
const state = required<HTMLDivElement>("state");
const catalog = required<HTMLDialogElement>("catalog-dialog");
const detailDialog = required<HTMLDialogElement>("detail-dialog");
const accessDialog = required<HTMLDialogElement>("access-dialog");
const accessStatus = required<HTMLParagraphElement>("access-status");
const helpDialog = required<HTMLDialogElement>("help-dialog");
helpDialog.insertAdjacentHTML(
  "beforeend",
  `<h3>Why these shapes?</h3><p>Stars show a hub with many direct neighbors; in Math models a hub often represents a model family shared by several systems. Chains follow successive supplied links. Disconnected islands have no connecting links in the current data or filter. None of these shapes adds a new relationship.</p><p>2D and 3D are force-layout projections, not semantic distance maps. Position, closeness, direction, and depth do not measure similarity, chronology, or influence. A 3D chain can look shorter or overlap when viewed end-on: orbit to inspect it, or use 2D for a flat overview.</p><p>Names are shown beside every node by default and keep their screen size when zooming. Use Names to show only hovered, selected, or highlighted names in crowded views. Fit frames the current graph; filters and dimension changes frame their new layout until you pan, zoom, or drag.</p>`,
);
const catalogSearch = required<HTMLInputElement>("catalog-search");
const detailContent = required<HTMLDivElement>("detail-content");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let canonical: GraphPayload = { nodes: [], edges: [] };
let modelCanonical: ModelGraphPayload | undefined;
let graphMode: "systems" | "models" = "systems";
let graphRequest = 0;
let systems: SystemSummary[] = [];
let visible: ExplorerPayload = canonical;
let graph: ForceGraph3DInstance<SimulationNode, SimulationLink> | undefined;
const loadForceGraphModule = lazyModule(() => import("3d-force-graph"));
let selectedId: string | undefined;
let selectedEdge: SimulationLink | undefined;
let styledEdgeId: string | undefined;
let hoveredId: string | undefined;
let highlighted = new Set<string>();
let searchMatches: Set<string> | undefined;
let paused = reducedMotion.matches;
let dimensions: 2 | 3 = 2;
let autoFit = true;
let initialFitPending = false;
let allNames = true;
let detailRequest = 0;
let metadataLoaded = false;
let accessReady = false;
let accessRequest: Promise<void> | undefined;
type LabelAnchor = {
  scale: { setScalar: (scale: number) => void };
  updateMatrixWorld: (force: boolean) => void;
};
const labelAnchors = new Map<string, LabelAnchor>();
type LinkAnchor = {
  scale: { x: number; y: number };
  geometry: { parameters: { radiusTop: number } };
  updateMatrixWorld: (force: boolean) => void;
};
const linkAnchors = new Map<string, LinkAnchor>();
const labelElements = new Map<string, HTMLSpanElement>();
const labelWidths = new Map<string, number>();
const namesLayer = required<HTMLDivElement>("graph-names");
let labelUpdateScheduled = false;
const labels = createLabelPool<SimulationNode, HTMLSpanElement>({
  schedule: (run) => {
    requestAnimationFrame(run);
  },
  create: (node) => {
    const label = document.createElement("span");
    label.className = "graph-name";
    label.textContent = node.name;
    label.dataset.nodeId = node.id;
    label.hidden = true;
    namesLayer.append(label);
    labelElements.set(node.id, label);
    return label;
  },
  update: (label, node) => {
    label.classList.toggle(
      "active",
      node.id === selectedId || node.id === hoveredId,
    );
  },
  dispose: (label) => {
    labelElements.delete(label.dataset.nodeId!);
    labelWidths.delete(label.dataset.nodeId!);
    label.remove();
  },
});
const details = new Map<string, SystemDetail>();
const relationColors = ["#69d7c3", "#bca5f4", "#e7bb7d", "#7ab9ee", "#e699ad"];
const relationColor = (type: string) =>
  type === "modeled-by"
    ? "#69d7c3"
    : type === "related"
      ? "#8c9cab"
      : relationColors[
          [...type].reduce(
            (sum, character) => sum + character.charCodeAt(0),
            0,
          ) % relationColors.length
        ];
const duration = () => (reducedMotion.matches ? 0 : 500);

function escapeHtml(value: string) {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ] ?? character,
  );
}

function showDialog(dialog: HTMLDialogElement) {
  closeNodeMenu();
  if (!dialog.open) dialog.showModal();
}

function loadTurnstileScript() {
  return new Promise<void>((resolve, reject) => {
    if (window.turnstile) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(
      "script[data-mathen-turnstile]",
    );
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener(
        "error",
        () => reject(new Error("Turnstile failed to load")),
        {
          once: true,
        },
      );
      return;
    }
    const script = document.createElement("script");
    script.src =
      "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    script.async = true;
    script.defer = true;
    script.dataset.mathenTurnstile = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Turnstile failed to load"));
    document.head.append(script);
  });
}

async function startAccess() {
  if (accessReady || accessRequest) return accessRequest;
  accessRequest = (async () => {
    const response = await fetch("/api/access/config", {
      credentials: "include",
    });
    if (!response.ok)
      throw new Error(`Access config returned ${response.status}`);
    const body = (await response.json()) as {
      data?: {
        enabled?: boolean;
        authenticated?: boolean;
        site_key?: string | null;
      };
    };
    const config = body.data;
    if (!config?.enabled || config.authenticated) {
      accessReady = true;
      void loadGraph();
      void loadMetadata();
      return;
    }
    if (!config.site_key) throw new Error("Turnstile site key is unavailable");
    showDialog(accessDialog);
    accessStatus.textContent = "Complete the Cloudflare check to continue.";
    await loadTurnstileScript();
    if (!window.turnstile) throw new Error("Turnstile is unavailable");
    const widgetId = window.turnstile.render(required("turnstile-widget"), {
      sitekey: config.site_key,
      action: "mathen-access",
      callback: (token) => {
        void fetch("/api/access/turnstile", {
          method: "POST",
          credentials: "include",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ token }),
        })
          .then(async (verification) => {
            if (!verification.ok)
              throw new Error("Turnstile verification failed");
            accessReady = true;
            accessDialog.close();
            void loadGraph();
            void loadMetadata();
          })
          .catch(() => {
            accessStatus.textContent = "Verification failed. Please try again.";
            window.turnstile?.reset(widgetId);
          });
      },
      "error-callback": () => {
        accessStatus.textContent =
          "Turnstile could not verify this browser. Retry the check.";
      },
      "expired-callback": () => {
        accessStatus.textContent =
          "The verification expired. Please complete it again.";
      },
    });
  })().catch(() => {
    accessStatus.textContent =
      "Access verification is unavailable. Please retry later.";
    accessStatus.insertAdjacentHTML(
      "afterend",
      '<button id="retry-access" class="primary-button">Retry verification</button>',
    );
    required("retry-access").onclick = () => {
      document.getElementById("retry-access")?.remove();
      accessRequest = undefined;
      void startAccess();
    };
  });
  return accessRequest;
}

accessDialog.addEventListener("cancel", (event) => event.preventDefault());
document
  .querySelectorAll<HTMLButtonElement>("[data-close]")
  .forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog")?.close());
  });
for (const dialog of [catalog, detailDialog, helpDialog]) {
  let opener: HTMLElement | null = null;
  let backdropDown = false;
  const outside = (event: PointerEvent | MouseEvent) => {
    const rect = dialog.getBoundingClientRect();
    return (
      event.target === dialog &&
      (event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom)
    );
  };
  dialog.addEventListener("pointerdown", (event) => {
    backdropDown = outside(event);
  });
  dialog.addEventListener("click", (event) => {
    if (backdropDown && outside(event)) dialog.close();
    backdropDown = false;
  });
  dialog.addEventListener("beforetoggle", (event) => {
    if ((event as ToggleEvent).newState === "open")
      opener = document.activeElement as HTMLElement | null;
  });
  dialog.addEventListener("close", () => {
    if (dialog === detailDialog) detailRequest++;
    const restore = opener?.isConnected
      ? opener
      : opener?.id
        ? document.getElementById(opener.id)
        : null;
    restore?.focus();
  });
}

function configureCamera() {
  if (!graph) return;
  configureNavigation(
    graph.controls() as Parameters<typeof configureNavigation>[0],
    dimensions,
  );
  required("gesture-hint").textContent =
    dimensions === 2
      ? "Drag space to pan. Drag a node to reshape its neighborhood. Scroll to zoom."
      : "Drag a node to reshape its neighborhood. Drag space to orbit.";
}

async function createGraph() {
  styledEdgeId = undefined;
  const { default: ForceGraph3D } = await loadForceGraphModule();
  graph = new ForceGraph3D(host, {
    controlType: "orbit",
    rendererConfig: { antialias: true, alpha: true },
  }) as unknown as ForceGraph3DInstance<SimulationNode, SimulationLink>;
  // The renderer updates camera matrices after controls but before this callback.
  // A separate RAF races that update and sizes the next frame from stale depth.
  graph.scene().onBeforeRender = renderScreenGeometry;
  graph
    .width(host.clientWidth)
    .height(host.clientHeight)
    .backgroundColor("#10192300")
    .showNavInfo(false)
    .numDimensions(dimensions)
    .nodeRelSize(4)
    .nodeResolution(16)
    .nodeVal(
      (node: SimulationNode) =>
        (node.type === "model" ? 4 : 1.4) + Math.sqrt(node.degree) * 0.65,
    )
    .nodeColor(nodeColor)
    .nodeOpacity(0.95)
    .nodeLabel((node) => {
      const label = document.createElement("span");
      label.textContent = node.name;
      return label;
    })
    .nodePositionUpdate((object, _coordinates, node) => {
      if (labelAnchors.get(node.id) !== object) {
        labelAnchors.set(node.id, object as LabelAnchor);
        if (!labelUpdateScheduled) {
          labelUpdateScheduled = true;
          queueMicrotask(() => {
            labelUpdateScheduled = false;
            updateLabels();
          });
        }
      }
      // Returning false preserves the engine's normal positioning and dragging.
      return false;
    })
    .linkColor(linkColor)
    .linkOpacity(0.85)
    .linkPositionUpdate((object, _coordinates, link) => {
      linkAnchors.set(link.id, object as unknown as LinkAnchor);
      return false;
    })
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
    .onNodeRightClick((node, event) => {
      event.preventDefault();
      selectNode(node.id);
      openNodeMenu(node.id, event.clientX, event.clientY);
    })
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
      if (pins.has(node.id))
        pins.set(node.id, {
          x: node.x!,
          y: node.y!,
          z: dimensions === 2 ? pins.get(node.id)!.z : node.z!,
        });
      applyPin(node, pins.get(node.id), dimensions);
      if (!paused) reheat();
    })
    .onEngineTick(() => {
      flatten2D();
      if (initialFitPending) {
        initialFitPending = false;
        fit(0);
      }
    })
    .onEngineStop(() => {
      flatten2D();
      initialFitPending = false;
      required("simulation-status").textContent = paused
        ? "Forces paused · navigation active"
        : "Layout settled · drag to reshape";
      if (autoFit) {
        fit(0);
        autoFit = false;
      }
    });
  graph.d3Force("charge")?.strength(-140).distanceMax(650);
  graph
    .d3Force("link")
    ?.distance((link: SimulationLink) =>
      link.type === "modeled-by" ? 220 : 150,
    )
    .strength((link: SimulationLink) =>
      link.type === "related" ? 0.12 : 0.35,
    );
  graph.d3Force("center")?.strength(0.08);
  configureCamera();
  new ResizeObserver(() => {
    graph?.width(host.clientWidth).height(host.clientHeight);
    if (autoFit) initialFitPending = true;
  }).observe(host);
  // Manual navigation should never be interrupted by a later automatic fit.
  host.addEventListener("pointerdown", () => {
    closeNodeMenu(false);
    autoFit = false;
    initialFitPending = false;
  });
  host.addEventListener(
    "wheel",
    () => {
      closeNodeMenu(false);
      autoFit = false;
      initialFitPending = false;
    },
    { passive: true },
  );
  updatePauseButton();
}

function nodeName(id: string) {
  return (
    modelCanonical?.nodes.find((node) => node.id === id)?.name ??
    canonical.nodes.find((node) => node.id === id)?.name ??
    id
  );
}
function graphSource(): ExplorerPayload {
  return graphMode === "models"
    ? (modelCanonical ?? { nodes: [], edges: [] })
    : canonical;
}
function closeNodeMenu(restore = true) {
  if (nodeMenu.hidden) return;
  nodeMenu.hidden = true;
  if (restore && menuOpener?.isConnected) menuOpener.focus();
}
function openNodeMenu(id: string, x?: number, y?: number) {
  const node = graph?.graphData().nodes.find((item) => item.id === id);
  if (!node || !graph) return;
  autoFit = false;
  initialFitPending = false;
  menuOpener = document.getElementById("node-actions") ?? host;
  const point = graph.graph2ScreenCoords(node.x!, node.y!, node.z!);
  nodeMenu.innerHTML = `<strong>${escapeHtml(node.name)}</strong><button role="menuitem" data-action="pin">${pins.has(id) ? "Unpin" : "Pin"}</button><button role="menuitem" data-action="expand">Expand 1 hop</button><button role="menuitem" data-action="hide">Hide from view</button><button role="menuitem" data-action="details">${node.type === "model" ? "View model metadata" : "View details"}</button><p>Expand adds actual neighbors outside the domain; relation filters and hidden nodes still apply.</p>`;
  nodeMenu.hidden = false;
  nodeMenu.style.left = `${Math.max(8, Math.min(x ?? point.x + 14, window.innerWidth - nodeMenu.offsetWidth - 8))}px`;
  nodeMenu.style.top = `${Math.max(8, Math.min(y ?? point.y, window.innerHeight - nodeMenu.offsetHeight - 8))}px`;
  nodeMenu
    .querySelectorAll<HTMLButtonElement>("[data-action]")
    .forEach((button) => {
      button.onclick = () => {
        closeNodeMenu();
        switch (button.dataset.action) {
          case "pin":
            if (pins.has(id)) pins.delete(id);
            else pins.set(id, { x: node.x!, y: node.y!, z: node.z! });
            applyPin(node, pins.get(id), dimensions);
            required("simulation-status").textContent =
              `${node.name} ${pins.has(id) ? "pinned" : "unpinned"}`;
            break;
          case "expand":
            expandOneHop(
              graphSource(),
              id,
              expandedNodes,
              graphMode === "models" ? "all" : relationSelect.value,
            );
            updateGraph();
            required("simulation-status").textContent =
              "Expanded actual neighbors · domain exceptions active";
            break;
          case "hide":
            hiddenNodes.add(id);
            updateGraph();
            required("restore-hidden").focus();
            break;
          case "details":
            if (node.type === "model") {
              selectNode(id);
              required("node-actions").focus();
            } else void openDetail(id);
            break;
        }
      };
    });
  nodeMenu.querySelector<HTMLButtonElement>("button")?.focus();
}
nodeMenu.addEventListener("keydown", (event) => {
  const items = [...nodeMenu.querySelectorAll<HTMLButtonElement>("button")];
  const index = items.indexOf(document.activeElement as HTMLButtonElement);
  if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
    event.preventDefault();
    items[
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? items.length - 1
          : (index + (event.key === "ArrowDown" ? 1 : -1) + items.length) %
            items.length
    ]?.focus();
  }
  if (event.key === "Tab") closeNodeMenu(false);
});
window.addEventListener("resize", () => closeNodeMenu(false));
function nodeColor(node: SimulationNode) {
  const active =
    (!highlighted.size || highlighted.has(node.id)) &&
    (!searchMatches || searchMatches.has(node.id));
  return active
    ? node.type === "model"
      ? "#d5afff"
      : domainFor(node.id).color
    : "#34404c";
}
function linkColor(link: SimulationLink) {
  if (selectedEdge?.id === link.id) return "#ffffff";
  if (
    highlighted.size &&
    (!highlighted.has(endpointId(link.source)) ||
      !highlighted.has(endpointId(link.target)))
  )
    return "#29323d";
  return relationColor(link.type);
}
function labelVisible(node: SimulationNode) {
  return (
    allNames ||
    node.id === hoveredId ||
    node.id === selectedId ||
    highlighted.has(node.id) ||
    Boolean(searchMatches?.has(node.id))
  );
}
function updateStyles() {
  if (!graph) return;
  graph.nodeColor(nodeColor).linkColor(linkColor);
  // The engine rebuilds every link mesh when linkWidth is set, even on hover.
  if (styledEdgeId !== selectedEdge?.id) {
    styledEdgeId = selectedEdge?.id;
    graph.linkWidth((link) =>
      selectedEdge?.id === link.id ? 2.5 : link.type === "related" ? 0.45 : 1.1,
    );
  }
  updateLabels();
}
function updateLabels() {
  const nodes = (graph?.graphData().nodes ?? []).filter(
    (node) => labelAnchors.has(node.id) && labelVisible(node),
  );
  // Hovered/selected nodes should not wait behind a large highlighted neighborhood.
  labels.sync([
    ...nodes.filter((node) => node.id === selectedId || node.id === hoveredId),
    ...nodes.filter((node) => node.id !== selectedId && node.id !== hoveredId),
  ]);
}

function updateGraph() {
  closeNodeMenu(false);
  autoFit = true;
  initialFitPending = true;
  visible =
    graphMode === "models"
      ? filterModelGraph(
          modelCanonical ?? { nodes: [], edges: [] },
          domainSelect.value,
        )
      : filterGraph(canonical, domainSelect.value, relationSelect.value);
  visible = applyView(
    graphSource(),
    visible,
    expandedNodes,
    hiddenNodes,
    graphMode === "models" ? "all" : relationSelect.value,
  );
  if (selectedId && !visible.nodes.some((node) => node.id === selectedId))
    clearSelection();
  selectedEdge = undefined;
  const next = modelSimulationData(visible);
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
  seedCoordinates(next.nodes, dimensions);
  for (const node of next.nodes) applyPin(node, pins.get(node.id), dimensions);
  labels.clear();
  labelAnchors.clear();
  linkAnchors.clear();
  graph?.graphData(next);
  highlighted = selectedId ? neighborhood(visible, selectedId) : new Set();
  if (selectedId) renderNodeInspector(selectedId);
  else inspector.hidden = true;
  required("counts").textContent =
    graphMode === "models"
      ? `${visible.nodes.filter((node) => node.type === "system").length} systems / ${visible.nodes.filter((node) => node.type === "model").length} models / ${visible.edges.length} model links`
      : `${visible.nodes.length} systems / ${visible.edges.length} relations`;
  if (expandedNodes.size)
    required("counts").textContent += " · expanded beyond group";
  if (visible.nodes.length) state.hidden = true;
  else {
    state.hidden = false;
    state.innerHTML = `<h2>No ${graphMode === "models" ? "model neighborhoods" : "systems"} in this group</h2><p>Choose another navigation group or reset the atlas.</p><button id="empty-reset">Reset atlas</button>`;
    required("empty-reset").onclick = reset;
  }
  updateSearch();
  required("restore-hidden").hidden = !hiddenNodes.size;
  required("restore-hidden").textContent =
    `Restore hidden (${hiddenNodes.size})`;
  renderCatalog();
  updateStyles();
  if (!paused) reheat();
  else graph?.cooldownTicks(0);
}

function safeViewport() {
  const width = host.clientWidth;
  const height = host.clientHeight;
  const tools = required("fit")
    .closest(".graph-tools")!
    .getBoundingClientRect();
  const filters = domainSelect.closest(".filters")!.getBoundingClientRect();
  const footer = required("counts")
    .closest(".map-key")!
    .getBoundingClientRect();
  const mobile = width <= 700;
  return {
    width,
    height,
    left: mobile ? 25 : filters.right + 24,
    right: width - (mobile ? 90 : 140),
    top: Math.max(tools.bottom, mobile ? filters.bottom : 0) + 30,
    bottom: footer.top - 28,
  };
}
function flatten2D() {
  // The engine deletes z when changing dimensions, including while forces are paused.
  if (dimensions === 2)
    for (const node of graph?.graphData().nodes ?? []) node.z = 0;
}
function fit(ms = duration(), only?: Set<string>) {
  if (!graph) return;
  const nodes = graph
    .graphData()
    .nodes.filter(
      (node) =>
        (!only || only.has(node.id)) &&
        [node.x, node.y, node.z].every(Number.isFinite),
    ) as (SimulationNode & { x: number; y: number; z: number })[];
  if (!nodes.length) return;
  const camera = graph.camera() as unknown as { fov: number };
  const frame = frameNodes(nodes, safeViewport(), camera.fov);
  graph.cameraPosition(frame.position, frame.target, ms);
}
function focus() {
  autoFit = false;
  initialFitPending = false;
  if (selectedId) fit(duration(), highlighted);
}

// CSS pixels (not drawing-buffer pixels) keep names and hit geometry readable at any DPR.
// O(V + E) per frame, O(V + E) anchors and pooled labels. No force restart on camera moves.
function renderScreenGeometry() {
  if (graph) {
    const camera = graph.camera() as unknown as {
      fov: number;
      matrixWorldInverse: { elements: number[] };
    };
    const m = camera.matrixWorldInverse.elements;
    const width = host.clientWidth;
    const height = host.clientHeight;
    for (const node of graph.graphData().nodes) {
      const { x = 0, y = 0, z = 0 } = node;
      const depth = -(m[2] * x + m[6] * y + m[10] * z + m[14]);
      const radius = node.type === "model" ? 12 : 10;
      const baseRadius =
        4 *
        Math.cbrt(
          (node.type === "model" ? 4 : 1.4) + Math.sqrt(node.degree) * 0.65,
        );
      const anchor = labelAnchors.get(node.id);
      if (anchor) {
        anchor.scale.setScalar(
          (radius * worldUnitsPerPixel(depth, camera.fov, height)) / baseRadius,
        );
        // Scene matrices were already updated before onBeforeRender. Refresh the
        // scaled mesh now so rendering and the subsequent raycast use this size.
        anchor.updateMatrixWorld(true);
      }
      const label = labelElements.get(node.id);
      if (!label) continue;
      const point = graph.graph2ScreenCoords(x, y, z);
      label.hidden =
        depth <= 0 ||
        point.x < -radius ||
        point.x > width + radius ||
        point.y < -radius ||
        point.y > height + radius;
      if (!label.hidden) {
        if (!labelWidths.has(node.id))
          labelWidths.set(node.id, label.offsetWidth);
        const labelWidth = labelWidths.get(node.id)!;
        // Keep labels adjacent, flipping at the right edge without moving the node.
        const right = point.x + radius + 5;
        const left =
          right + labelWidth < width - 8
            ? right
            : point.x - radius - 5 - labelWidth;
        label.style.transform = `translate(${Math.max(8, left)}px, ${Math.max(4, Math.min(height - 24, point.y - 10))}px)`;
      }
    }
    for (const link of graph.graphData().links) {
      const anchor = linkAnchors.get(link.id);
      if (!anchor?.geometry.parameters.radiusTop) continue;
      const source = link.source as SimulationNode;
      const target = link.target as SimulationNode;
      const x = ((source.x ?? 0) + (target.x ?? 0)) / 2;
      const y = ((source.y ?? 0) + (target.y ?? 0)) / 2;
      const z = ((source.z ?? 0) + (target.z ?? 0)) / 2;
      const depth = -(m[2] * x + m[6] * y + m[10] * z + m[14]);
      const pixels =
        selectedEdge?.id === link.id ? 3 : link.type === "related" ? 1.2 : 2;
      anchor.scale.x = anchor.scale.y =
        (pixels * worldUnitsPerPixel(depth, camera.fov, height)) /
        (2 * anchor.geometry.parameters.radiusTop);
      anchor.updateMatrixWorld(true);
    }
  }
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
  closeNodeMenu(false);
  selectedId = undefined;
  selectedEdge = undefined;
  highlighted.clear();
  inspector.hidden = true;
  required<HTMLButtonElement>("focus").disabled = true;
  updateStyles();
}
function selectNode(id: string) {
  closeNodeMenu(false);
  selectedId = id;
  selectedEdge = undefined;
  highlighted = neighborhood(visible, id);
  required<HTMLButtonElement>("focus").disabled = !visible.nodes.some(
    (node) => node.id === id,
  );
  results.hidden = true;
  renderNodeInspector(id);
  updateStyles();
  const node = graph
    ?.graphData()
    .nodes.find((candidate) => candidate.id === id);
  if (graph && node && [node.x, node.y, node.z].every(Number.isFinite)) {
    autoFit = false;
    initialFitPending = false;
    const controls = graph.controls() as {
      target: { x: number; y: number; z: number };
    };
    const frame = centeredCamera(graph.camera().position, controls.target, {
      x: node.x!,
      y: node.y!,
      z: node.z!,
    });
    graph.cameraPosition(frame.position, frame.target, duration());
  }
}
function renderNodeInspector(id: string) {
  const node = visible.nodes.find((item) => item.id === id);
  if (node?.type === "model") {
    const edges = visible.edges.filter((edge) => edge.target === id);
    inspector.hidden = false;
    inspector.innerHTML = `<button class="inspector-close" aria-label="Clear selection">✕</button><p class="eyebrow model-family">Mathematical model family</p><h2>${escapeHtml(node.name)}</h2><p>${edges.length} visible systems share this candidate model family. Shared models do not imply influence or a system-to-system relation.</p>${modelConnections(id)}`;
    bindInspector();
    return;
  }
  const system = details.get(id) ?? systems.find((item) => item.id === id);
  const edges = visible.edges.filter(
    (edge) => edge.source === id || edge.target === id,
  );
  inspector.hidden = false;
  inspector.innerHTML = `<button class="inspector-close" aria-label="Clear selection">✕</button><p class="eyebrow">${escapeHtml(domainFor(id).name)} · navigation group</p><h2>${escapeHtml(nodeName(id))}</h2><p class="selection-summary">${escapeHtml(system?.summary ?? "Open the architecture card for reviewed scope, features, and evidence.")}</p><div class="tag-row">${system ? system.scope.map((scope) => `<span>${escapeHtml(scope)}</span>`).join("") : "<span>Card scope loading on demand</span>"}</div><div class="inspector-bottom"><span>${edges.length} visible relation${edges.length === 1 ? "" : "s"}</span><button id="open-card" class="primary-button">Open card ↗</button></div>`;
  if (graphMode === "models")
    inspector.insertAdjacentHTML("beforeend", modelConnections(id));
  bindInspector();
  required("open-card").onclick = () => void openDetail(id);
}

function modelConnections(id: string) {
  return `<div class="model-connections">${visible.edges
    .flatMap((edge) => {
      if (
        edge.type !== "modeled-by" ||
        (edge.source !== id && edge.target !== id)
      )
        return [];
      const other = edge.source === id ? edge.target : edge.source;
      return [
        `<div><button data-inspect-node="${escapeHtml(other)}">${escapeHtml(nodeName(other))}</button><button data-view-edge="${escapeHtml(simulationEdgeId(edge.source, edge.target))}">Inspect ${edge.metadata?.length ?? 0} view${edge.metadata?.length === 1 ? "" : "s"} ↗</button></div>`,
      ];
    })
    .join("")}</div>`;
}

function bindInspector() {
  inspector.insertAdjacentHTML(
    "afterbegin",
    `<div class="inspector-toolbar"><button data-move-panel class="panel-handle" aria-label="Move selection panel. Arrow keys move; Home resets position." title="Drag to move · arrows to move · Home to reset">⠿ Selection</button>${selectedId ? '<button id="node-actions" aria-haspopup="menu" aria-controls="node-menu">Actions</button>' : ""}</div>`,
  );
  const actions = document.getElementById("node-actions");
  if (actions)
    actions.onclick = () => {
      if (selectedId) openNodeMenu(selectedId);
    };
  panel.clamp();
  inspector
    .querySelector(".inspector-close")
    ?.addEventListener("click", clearSelection);
  inspector
    .querySelectorAll<HTMLButtonElement>("[data-inspect-node]")
    .forEach((button) => {
      button.onclick = () => selectNode(button.dataset.inspectNode!);
    });
  inspector
    .querySelectorAll<HTMLButtonElement>("[data-view-edge]")
    .forEach((button) => {
      button.onclick = () => {
        const edge = graph
          ?.graphData()
          .links.find((link) => link.id === button.dataset.viewEdge);
        if (edge) selectEdge(edge);
      };
    });
}
function selectEdge(edge: SimulationLink) {
  closeNodeMenu(false);
  selectedEdge = edge;
  selectedId = undefined;
  highlighted = new Set([endpointId(edge.source), endpointId(edge.target)]);
  required<HTMLButtonElement>("focus").disabled = true;
  inspector.hidden = false;
  if (edge.type === "modeled-by") {
    inspector.innerHTML = `<button class="inspector-close" aria-label="Clear selection">✕</button><p class="eyebrow model-family">Candidate mathematical views · ${escapeHtml(edge.claim_type ?? "")}</p><h2>${escapeHtml(nodeName(endpointId(edge.target)))}</h2><p>${escapeHtml(nodeName(endpointId(edge.source)))} → modeled by</p><div class="model-views">${(edge.metadata ?? []).map((view) => `<section><h3>${escapeHtml(view.model)}</h3><dl><dt>Question</dt><dd>${escapeHtml(view.question) || "Not supplied"}</dd><dt>Assumptions</dt><dd>${view.assumptions.length ? `<ul>${view.assumptions.map((assumption) => `<li>${escapeHtml(assumption)}</li>`).join("")}</ul>` : "None supplied"}</dd><dt>Claim</dt><dd>${escapeHtml(view.claim_type)}</dd><dt>Evidence IDs · source card</dt><dd>${view.evidence_ids.length ? view.evidence_ids.map(escapeHtml).join(", ") : "None supplied"}</dd></dl></section>`).join("") || "<p>No view metadata supplied.</p>"}</div><button id="source-card" class="primary-button">Open source card & evidence ↗</button>`;
    bindInspector();
    required("source-card").onclick = () =>
      void openDetail(endpointId(edge.source));
    updateStyles();
    return;
  }
  inspector.innerHTML = `<button class="inspector-close" aria-label="Clear selection">✕</button><p class="eyebrow">${edge.type === "related" ? "Legacy association" : "Typed relation"}</p><h2>${escapeHtml(edge.type.replaceAll("_", " "))}</h2><p>${escapeHtml(nodeName(endpointId(edge.source)))} ${edge.type === "related" ? "—" : "→"} ${escapeHtml(nodeName(endpointId(edge.target)))}</p><div class="tag-row">${[
    edge.claim_type,
    edge.claim_status,
  ]
    .filter(Boolean)
    .map((item) => `<span>${escapeHtml(item!)}</span>`)
    .join(
      "",
    )}</div>${edge.notes ? `<p class="selection-summary">${escapeHtml(edge.notes)}</p>` : ""}<p class="muted">${edge.evidence_ids?.length ? `Evidence: ${edge.evidence_ids.map(escapeHtml).join(", ")}` : "No relation evidence supplied."}</p><button id="source-card" class="primary-button">Open source card & evidence ↗</button>`;
  bindInspector();
  required("source-card").onclick = () =>
    void openDetail(endpointId(edge.source));
  updateStyles();
}

function updateSearch() {
  const matches = searchNodes(
    visible.nodes,
    systems,
    search.value,
    visible.edges,
  );
  searchMatches = search.value.trim()
    ? new Set(matches.map((node) => node.id))
    : undefined;
  results.hidden = !search.value.trim() || document.activeElement !== search;
  results.innerHTML = matches.length
    ? `${matches
        .slice(0, 8)
        .map(
          (node) =>
            `<button data-result="${escapeHtml(node.id)}"><strong>${escapeHtml(node.name)}</strong><small>${escapeHtml(node.type === "model" ? "Model family" : domainFor(node.id).name)}</small></button>`,
        )
        .join(
          "",
        )}<button id="all-results">Browse all ${matches.length} results ↗</button>`
    : `<p>No matching nodes in this navigation group.</p>`;
  results.querySelectorAll<HTMLButtonElement>("[data-result]").forEach(
    (button) =>
      (button.onclick = () => {
        selectNode(button.dataset.result!);
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
  const nodes = (
    graphMode === "models" ? modelCanonical : canonical.nodes.length
  )
    ? visible.nodes
    : systems.map((system) => ({
        id: system.id,
        name: system.name,
        type: "system" as const,
      }));
  const matches = searchNodes(nodes, systems, catalogSearch.value);
  required("catalog-count").textContent =
    `${matches.length} ${graphMode === "models" ? "systems and models" : "systems"} · ${domainSelect.selectedOptions[0].textContent}`;
  const metadata = new Map(systems.map((system) => [system.id, system]));
  required("catalog-list").innerHTML = matches.length
    ? matches
        .map(
          (node) =>
            `<article class="catalog-item"><span class="eyebrow">${escapeHtml(node.type === "model" ? "Mathematical model family" : domainFor(node.id).name)}</span><h3>${escapeHtml(node.name)}</h3><p>${escapeHtml(node.type === "model" ? "Select to explore systems and inspect their candidate views." : (metadata.get(node.id)?.summary ?? "Reviewed card details available on demand."))}</p><div>${node.type === "system" ? `<button data-card="${escapeHtml(node.id)}">Read card ↗</button>` : ""}<button data-locate="${escapeHtml(node.id)}">Locate on graph</button></div></article>`,
        )
        .join("")
    : `<p class="muted">No nodes match this search. Change the query or navigation group.</p>`;
  required("catalog-list")
    .querySelectorAll<HTMLButtonElement>("[data-card]")
    .forEach(
      (button) =>
        (button.onclick = () => void openDetail(button.dataset.card!)),
    );
  required("catalog-list")
    .querySelectorAll<HTMLButtonElement>("[data-locate]")
    .forEach(
      (button) =>
        (button.onclick = () => {
          catalog.close();
          selectNode(button.dataset.locate!);
          inspector.querySelector<HTMLButtonElement>("button")?.focus();
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
      .forEach(
        (button) =>
          (button.onclick = () => void openDetail(button.dataset.related!)),
      );
    if (selectedId === id) renderNodeInspector(id);
  } catch {
    if (request !== detailRequest) return;
    detailContent.innerHTML = `<p role="alert">Unable to load this architecture card.</p><button id="retry-detail" class="primary-button">Retry card</button>`;
    required("retry-detail").onclick = () => void openDetail(id);
  }
}

function reset() {
  pins.clear();
  hiddenNodes.clear();
  expandedNodes.clear();
  panel.reset();
  domainSelect.value = "all";
  relationSelect.value = "all";
  search.value = "";
  catalogSearch.value = "";
  clearSelection();
  updateGraph();
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
  const request = ++graphRequest;
  const mode = graphMode;
  state.hidden = false;
  state.innerHTML = `<span class="state-orbit" aria-hidden="true"></span><h1>Connecting the atlas</h1><p>Loading ${mode === "models" ? "mathematical model neighborhoods" : "systems and relationships"}…</p>`;
  const graphModule = graph ? undefined : loadForceGraphModule();
  // A superseded request may return before the parallel chunk settles.
  // Attach a rejection handler without changing the promise awaited below.
  void graphModule?.catch(() => undefined);
  try {
    if (mode === "models") {
      modelCanonical ??= await loadModelGraph();
    } else {
      const response = await fetch("/api/graph");
      if (!response.ok)
        throw new Error(`Graph API returned ${response.status}`);
      const payload = (await response.json()) as
        GraphPayload | { data: GraphPayload };
      canonical = "data" in payload ? payload.data : payload;
      if (!Array.isArray(canonical.nodes) || !Array.isArray(canonical.edges))
        throw new Error("Invalid graph payload");
    }
    if (!graph) await graphModule;
    if (request !== graphRequest) return;
    if (!graph) await createGraph();
    relationSelect.innerHTML = `<option value="all">All relations</option>${[
      ...new Set(
        (mode === "models" ? modelCanonical!.edges : canonical.edges).map(
          (edge) => edge.type,
        ),
      ),
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
    if (request !== graphRequest) return;
    labels.clear();
    labelAnchors.clear();
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

function switchGraphMode(mode: "systems" | "models") {
  if (mode === graphMode) return;
  graphMode = mode;
  expandedNodes.clear();
  clearSelection();
  hoveredId = undefined;
  visible = { nodes: [], edges: [] };
  labels.clear();
  labelAnchors.clear();
  graph?.graphData({ nodes: [], links: [] });
  relationSelect.value = "all";
  relationSelect.disabled = mode === "models";
  required("graph-systems").setAttribute(
    "aria-pressed",
    String(mode === "systems"),
  );
  required("graph-models").setAttribute(
    "aria-pressed",
    String(mode === "models"),
  );
  search.placeholder =
    mode === "models" ? "Find a system or model…" : "Find a system…";
  search.setAttribute(
    "aria-label",
    mode === "models"
      ? "Search systems and mathematical models"
      : "Search systems, descriptions, or card scope",
  );
  required("catalog-title").textContent =
    mode === "models" ? "Browse systems & models" : "Browse systems";
  required("catalog-open").innerHTML =
    `${mode === "models" ? "Browse nodes" : "Browse systems"} <span aria-hidden="true">↗</span>`;
  const key = document.querySelector(".edge-key");
  if (key)
    key.innerHTML =
      mode === "models"
        ? '<span><i class="model-dot"></i>Model family</span><span><i class="typed-line"></i>Modeled by</span>'
        : '<span><i class="typed-line"></i>Typed relation</span><span><i class="legacy-line"></i>Legacy related</span>';
  required("counts").textContent = "Loading graph…";
  updateSearch();
  void loadGraph();
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
    const first = searchNodes(
      visible.nodes,
      systems,
      search.value,
      visible.edges,
    )[0];
    if (first) {
      selectNode(first.id);
      search.blur();
    }
  }
});
document.addEventListener("pointerdown", (event) => {
  if (!(event.target as Element).closest(".search-wrap")) results.hidden = true;
  if (!(event.target as Element).closest("#node-menu, #node-actions"))
    closeNodeMenu(false);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !nodeMenu.hidden) {
    event.preventDefault();
    closeNodeMenu();
    return;
  }
  if (
    (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) &&
    selectedId &&
    !document.querySelector("dialog[open]")
  ) {
    event.preventDefault();
    openNodeMenu(selectedId);
    return;
  }
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
required("help-open").onclick = required("legend-open").onclick = () =>
  showDialog(helpDialog);
domainSelect.onchange = () => {
  expandedNodes.clear();
  updateGraph();
};
relationSelect.onchange = () => {
  expandedNodes.clear();
  updateGraph();
};
required("restore-hidden").onclick = () => {
  hiddenNodes.clear();
  updateGraph();
};
required("fit").onclick = () => {
  autoFit = false;
  initialFitPending = false;
  fit();
};
required("names").onclick = () => {
  allNames = !allNames;
  required("names").setAttribute("aria-pressed", String(allNames));
  required("names").textContent = allNames ? "Names: all" : "Names: focus";
  updateLabels();
};
required("focus").onclick = focus;
required("reset").onclick = reset;
required("reheat").onclick = reheat;
required("graph-systems").onclick = () => switchGraphMode("systems");
required("graph-models").onclick = () => switchGraphMode("models");
required("pause").onclick = () => {
  paused = !paused;
  updatePauseButton();
  if (paused) {
    graph?.cooldownTicks(0);
    required("simulation-status").textContent =
      "Forces paused · navigation active";
  } else reheat();
};
for (const mode of [2, 3] as const)
  required(`mode-${mode}`).onclick = () => {
    if (dimensions === mode) return;
    closeNodeMenu(false);
    dimensions = mode;
    required("mode-2").setAttribute("aria-pressed", String(mode === 2));
    required("mode-3").setAttribute("aria-pressed", String(mode === 3));
    seedCoordinates(graph?.graphData().nodes ?? [], mode);
    for (const node of graph?.graphData().nodes ?? [])
      applyPin(node, pins.get(node.id), mode);
    graph?.numDimensions(mode);
    configureCamera();
    if (mode === 2)
      graph?.cameraPosition({ x: 0, y: 0, z: 700 }, { x: 0, y: 0, z: 0 }, 0);
    if (!paused) reheat();
    else graph?.cooldownTicks(0);
    autoFit = true;
    initialFitPending = true;
  };
reducedMotion.addEventListener("change", () => {
  if (reducedMotion.matches) {
    paused = true;
    graph?.cooldownTicks(0);
    updatePauseButton();
  }
});
void startAccess();
