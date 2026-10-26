import type { GraphPayload, SystemSummary } from "./graph-data";

export type SystemDetail = SystemSummary & {
  features: Array<{
    id: string;
    name: string;
    category: string;
    claim_type: string;
    description: string;
    benefits: string[];
    costs: string[];
    evidence_ids: string[];
  }>;
  mathematical_views: Array<{
    model: string;
    question: string;
    assumptions: string[];
    claim_type: string;
    evidence_ids: string[];
  }>;
  trade_offs?: Array<{ feature_id: string; benefits: string[]; costs: string[] }>;
  feature_relations?: Array<{
    source_feature_id: string;
    target_system_id: string;
    target_feature_id: string;
    type: string;
    claim_type?: string;
    claim_status?: string;
    lifecycle?: Record<string, unknown>;
    evidence_ids?: string[];
    notes?: string | null;
  }>;
  evidence: Array<{
    id: string;
    title: string;
    uri: string;
    kind: string;
    accessed?: string;
    notes?: string;
  }>;
};

function escapeHtml(value: string) {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character] ??
      character,
  );
}
function safeHref(value: string) {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password
      ? escapeHtml(url.href)
      : undefined;
  } catch {
    return undefined;
  }
}
function list(items: string[]) {
  return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function relationLabel(type: string) {
  return type === "related" ? "Legacy related" : type.replaceAll("_", " ");
}

export function renderDetail(system: SystemDetail, graph: GraphPayload) {
  const evidence = new Map(system.evidence.map((item) => [item.id, item]));
  const pills = (ids: string[]) =>
    `<div class="evidence-pills">${ids
      .map((id) => {
        const item = evidence.get(id);
        return item
          ? safeHref(item.uri)
            ? `<a href="${safeHref(item.uri)}" target="_blank" rel="noopener noreferrer">${escapeHtml(id)} ↗</a>`
            : `<span>${escapeHtml(id)} (non-web source)</span>`
          : `<span>${escapeHtml(id)}</span>`;
      })
      .join("")}</div>`;
  const relations = graph.edges.filter(
    (edge) => edge.source === system.id || edge.target === system.id,
  );
  const featureRelations = system.feature_relations ?? [];
  const featureNames = new Map(system.features.map((feature) => [feature.id, feature.name]));
  const nodeNames = new Map(graph.nodes.map((node) => [node.id, node.name]));
  return `<article class="architecture-card">
    <p class="detail-lead">${escapeHtml(system.summary)}</p>
    ${system.version_context ? `<p class="muted">${escapeHtml(system.version_context)}</p>` : ""}
    <h3>Card scope</h3><div class="tag-row">${system.scope.map((scope) => `<span>${escapeHtml(scope)}</span>`).join("")}</div>
    <div class="detail-metrics"><span><strong>${system.features.length}</strong> features</span><span><strong>${system.mathematical_views.length}</strong> views</span><span><strong>${system.evidence.length}</strong> sources</span></div>
    <section class="detail-section"><p class="eyebrow">Transferable structure</p><h3>Reusable features</h3>${system.features.map((feature) => `<article class="content-card"><div class="feature-meta"><span>${escapeHtml(feature.category)}</span><span>${escapeHtml(feature.claim_type)}</span></div><h4>${escapeHtml(feature.name)}</h4><p>${escapeHtml(feature.description)}</p><details><summary>Benefits and costs</summary><h5>Benefits</h5><ul>${list(feature.benefits)}</ul><h5>Costs</h5><ul>${list(feature.costs)}</ul></details>${pills(feature.evidence_ids)}</article>`).join("") || `<p>No reusable features recorded.</p>`}</section>
    <section class="detail-section"><p class="eyebrow">Candidate mathematical views</p><h3>Mathematical views</h3>${system.mathematical_views.map((view) => `<article class="content-card"><span class="claim-type">${escapeHtml(view.claim_type)}</span><h4>${escapeHtml(view.model)}</h4><p>${escapeHtml(view.question)}</p><details><summary>Assumptions (${view.assumptions.length})</summary><ul>${list(view.assumptions)}</ul></details>${pills(view.evidence_ids)}</article>`).join("") || `<p>No mathematical views recorded.</p>`}</section>
    ${system.trade_offs?.length ? `<section class="detail-section"><h3>Trade-offs</h3>${system.trade_offs.map((tradeOff) => `<article class="content-card"><h4>${escapeHtml(system.features.find((feature) => feature.id === tradeOff.feature_id)?.name ?? tradeOff.feature_id)}</h4><h5>Benefits</h5><ul>${list(tradeOff.benefits)}</ul><h5>Costs</h5><ul>${list(tradeOff.costs)}</ul></article>`).join("")}</section>` : ""}
    <section class="detail-section"><p class="eyebrow">Feature relationships</p><h3>Feature relations (${featureRelations.length})</h3>${
      featureRelations
        .map((relation) => {
          const sourceFeature =
            featureNames.get(relation.source_feature_id) ?? relation.source_feature_id;
          const targetSystem =
            nodeNames.get(relation.target_system_id) ?? relation.target_system_id;
          return `<article class="content-card feature-relation"><div class="feature-meta"><span>${escapeHtml(relationLabel(relation.type))}</span><span>${escapeHtml([relation.claim_type, relation.claim_status].filter(Boolean).join(" · "))}</span></div><p class="relation-direction"><strong>${escapeHtml(system.name)}</strong> · ${escapeHtml(sourceFeature)} <span aria-hidden="true">→</span> <strong>${escapeHtml(targetSystem)}</strong> · ${escapeHtml(relation.target_feature_id)}</p>${relation.notes ? `<p>${escapeHtml(relation.notes)}</p>` : ""}${pills(relation.evidence_ids ?? [])}</article>`;
        })
        .join("") || `<p>No feature relations recorded.</p>`
    }</section>
    <section class="detail-section"><p class="eyebrow">Keyboard-accessible neighborhood</p><h3>Relations (${relations.length})</h3>${
      relations
        .map((edge) => {
          const other = edge.source === system.id ? edge.target : edge.source;
          return `<article class="content-card"><div class="feature-meta"><span>${escapeHtml(relationLabel(edge.type))}</span><span>${escapeHtml([edge.claim_type, edge.claim_status].filter(Boolean).join(" · "))}</span></div><button data-related="${escapeHtml(other)}">${escapeHtml(graph.nodes.find((node) => node.id === other)?.name ?? other)} ↗</button><p class="muted">${edge.source === system.id ? "Outgoing" : "Incoming"}${edge.type === "related" ? " association" : " relation"}</p>${edge.notes ? `<p>${escapeHtml(edge.notes)}</p>` : ""}${pills(edge.evidence_ids ?? [])}</article>`;
        })
        .join("") || `<p>No relations recorded in the graph.</p>`
    }</section>
     <section class="detail-section"><p class="eyebrow">Primary sources</p><h3>Evidence trail</h3><ol class="evidence-list">${system.evidence.map((item) => `<li class="${item.kind === "experiment" ? "evidence-experiment" : ""}"><span class="evidence-kind eyebrow">${item.kind === "experiment" ? "Experiment" : escapeHtml(item.kind)}</span>${safeHref(item.uri) ? `<a href="${safeHref(item.uri)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)} ↗</a>` : `<span>${escapeHtml(item.title)} (non-web source)</span>`}<small>${escapeHtml(item.id)}${item.accessed ? ` · accessed ${escapeHtml(item.accessed)}` : ""}</small>${item.notes ? `<p>${escapeHtml(item.notes)}</p>` : ""}</li>`).join("")}</ol></section>
  </article>`;
}
