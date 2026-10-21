import "./style.css";

type SystemSummary = {
  id: string;
  name: string;
  version_context: string | null;
  summary: string;
  scope: string[];
  related_systems: string[];
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
if (!searchInputElement || !systemListElement || !systemCountElement || !detailPanelElement) {
  throw new Error("Required UI elements are missing");
}
const searchInput = searchInputElement;
const systemList = systemListElement;
const systemCount = systemCountElement;
const detailPanel = detailPanelElement;

let systems: SystemSummary[] = [];
await loadSystems();
searchInput.addEventListener("input", () => renderSystems(searchInput.value));

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

function renderSystems(query: string) {
  const normalized = query.trim().toLowerCase();
  const visible = systems.filter((system) => {
    const searchable = [system.name, system.summary, ...system.scope].join(" ").toLowerCase();
    return searchable.includes(normalized);
  });
  systemList.innerHTML = visible.length ? visible.map(systemCard).join("") : `<p class="muted-message">No matching systems.</p>`;
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
  return value.replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] ?? character);
}
