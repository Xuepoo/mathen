import {
  normalizeRetrieval,
  retrievalParams,
  RETRIEVAL_LIMIT,
  RETRIEVAL_WARNING,
  type RetrievalResponse,
} from "../../mcp/src/retrieval-contract";

export type RetrievalState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "error"; message: string }
  | { status: "ready"; data: RetrievalResponse };
type Request = (input: string, init?: RequestInit) => Promise<Response>;

/** Latest request wins. Query text stays out of URLs/history except the same-origin API request. */
export function createRetrievalSearch(
  publish: (state: RetrievalState) => void,
  request: Request = fetch,
  timeoutMs = 10_000,
) {
  let sequence = 0;
  let active: AbortController | undefined;
  return {
    async search(query: string) {
      const current = ++sequence;
      active?.abort();
      let params: URLSearchParams;
      try {
        params = retrievalParams({ q: query, limit: RETRIEVAL_LIMIT });
      } catch {
        publish({ status: "error", message: "Enter a query of 1–1,000 characters." });
        return;
      }
      const controller = new AbortController();
      active = controller;
      publish({ status: "loading" });
      const timeout = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await request(`/api/retrieval?${params}`, { signal: controller.signal });
        if (current !== sequence) return;
        if (response.status === 503) {
          publish({ status: "unavailable" });
          return;
        }
        if (!response.ok) {
          publish({
            status: "error",
            message:
              response.status === 401 || response.status === 403
                ? "Access verification is required. Reload the page to verify, then retry discovery."
                : "Unable to retrieve reviewed records. Retry discovery later.",
          });
          return;
        }
        const body: unknown = await response.json();
        const data = normalizeRetrieval(
          typeof body === "object" && body !== null && "data" in body ? body.data : undefined,
          RETRIEVAL_LIMIT,
        );
        if (current === sequence) publish({ status: "ready", data });
      } catch {
        if (current === sequence)
          publish(
            controller.signal.aborted
              ? { status: "unavailable" }
              : {
                  status: "error",
                  message: "Unable to retrieve reviewed records. Retry discovery later.",
                },
          );
      } finally {
        clearTimeout(timeout);
        if (current === sequence) active = undefined;
      }
    },
  };
}

const escapeHtml = (value: string) =>
  value.replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!,
  );
function text(value: unknown) {
  return escapeHtml(
    typeof value === "string" ? value : value == null ? "Not supplied" : JSON.stringify(value),
  );
}
function evidenceLink(uri: string, label: string) {
  try {
    const url = new URL(uri);
    if (["https:", "http:"].includes(url.protocol) && !url.username && !url.password) {
      return `<a href="${escapeHtml(url.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} ↗</a>`;
    }
  } catch {
    /* Non-web evidence remains visible without an active link. */
  }
  return `<span>${escapeHtml(label)} (non-web source)</span>`;
}

/** Render supplied metadata only: a ranking signal never upgrades a claim or adds a relation. */
export function renderRetrievalState(state: RetrievalState): string {
  const warning = `<p class="retrieval-warning">${RETRIEVAL_WARNING}</p>`;
  const browse =
    '<button type="button" data-retrieval-browse>Browse systems by name or scope instead ↓</button>';
  if (state.status === "idle")
    return `<p>Search reviewed card records, features, views, relations, trade-offs, and compositions. Up to ${RETRIEVAL_LIMIT} results; independent of graph filters. No drafts, embeddings, or semantic/vector similarity.</p>${warning}`;
  if (state.status === "loading")
    return `<p role="status">Searching reviewed records…</p>${warning}`;
  if (state.status === "unavailable")
    return `<p role="status">Retrieval is unavailable. Retry discovery later; no fallback search was run.</p>${browse}${warning}`;
  if (state.status === "error")
    return `<p role="alert">${escapeHtml(state.message)}</p>${browse}${warning}`;
  const { data } = state;
  const index = `<p class="muted">${text(data.index.method)} · ${text(data.index.status)} · ${text(data.index.corpus)} · ${text(data.index.index_id)} · ${text(data.index.representation_version)}</p>`;
  const warnings = [...data.index.warnings, ...data.warnings];
  const notices = warnings.length
    ? `<p class="retrieval-warning">Service warnings: ${warnings.map(escapeHtml).join(" · ")}</p>`
    : "";
  const scope = `<p class="muted">Applied retrieval filters: ${Object.keys(data.query.filters).length ? text(data.query.filters) : "None (all reviewed records)"}</p>`;
  if (!data.results.length)
    return `${index}${scope}<p role="status">${data.index.status === "empty" ? "No eligible reviewed records in the retrieval corpus." : "No matching reviewed records for this query."} This does not establish that no relevant architecture exists. Try other terms or browse systems.</p>${notices}${browse}${warning}`;
  return `${index}${scope}<p role="status">${data.results.length} reviewed result${data.results.length === 1 ? "" : "s"} · maximum ${RETRIEVAL_LIMIT}</p>${warning}${notices}<ol class="retrieval-results">${data.results
    .map((result) => {
      const { document, provenance } = result;
      const evidence = new Map(result.evidence.map((item) => [item.id, item]));
      return `<li><article class="content-card"><p class="eyebrow">#${result.rank} · ${text(document.record_kind)} · ${text(document.system_id)}</p><h3>${text(document.name)}</h3><p>${text(document.description)}</p><dl>
       <dt>Claim type / review status</dt><dd>${text(document.claim_type)} / ${text(document.claim_status)}</dd>
       <dt>Lifecycle status</dt><dd>${text(document.lifecycle)}</dd>
      <dt>Discovery ranking · score_kind</dt><dd>${result.score} · ${text(result.score_kind)} (uncalibrated)</dd>
      <dt>Version context</dt><dd>${text(document.version_context)}</dd>
      <dt>Validity / deployment scope (not universal applicability)</dt><dd>${text(document.validity_scope)}</dd>
      <dt>Evidence IDs · source-local links</dt><dd>${document.evidence_ids
        .map((id) => {
          const item = evidence.get(id)!;
          return `${evidenceLink(item.uri, `${id} · ${item.title}`)} <small>(${text(item.kind)}${item.accessed ? ` · accessed ${text(item.accessed)}` : ""}${item.notes ? ` · ${text(item.notes)}` : ""})</small>`;
        })
        .join("<br>")}</dd>
      <dt>Source / provenance</dt><dd>${text(provenance.source_ref)}<br>${text(provenance.source_digest)}<br>${text(provenance.retrieval_method)}</dd>
      <dt>Document ID</dt><dd>${text(document.id)}</dd></dl><button type="button" data-retrieval-card="${text(document.system_id)}">Read ${text(document.system_id)} card & evidence ↗</button></article></li>`;
    })
    .join("")}</ol>`;
}

/** Mount inside the existing catalog; preserve its keyboard navigation and detail dialog. */
export function mountRetrieval(
  host: HTMLElement,
  openCard: (id: string) => void,
  browse: () => void,
) {
  host.innerHTML = `<h3 id="retrieval-title">Discover reviewed records</h3><p class="muted">Bounded lexical baseline · words and phrases, not semantic similarity</p><form class="catalog-search" aria-labelledby="retrieval-title"><label for="retrieval-query">Find an architectural idea across the reviewed atlas</label><input id="retrieval-query" name="q" type="search" required maxlength="1000" placeholder="e.g. embedded execution or ordered events" autocomplete="off"><button type="submit" class="primary-button">Discover records</button></form><div data-retrieval-state aria-live="polite" aria-busy="false"></div>`;
  const form = host.querySelector<HTMLFormElement>("form")!;
  const input = host.querySelector<HTMLInputElement>("input")!;
  const output = host.querySelector<HTMLElement>("[data-retrieval-state]")!;
  const submit = form.querySelector<HTMLButtonElement>("button")!;
  const publish = (state: RetrievalState) => {
    output.innerHTML = renderRetrievalState(state);
    output.setAttribute("aria-busy", String(state.status === "loading"));
    submit.disabled = state.status === "loading";
  };
  publish({ status: "idle" });
  const search = createRetrievalSearch(publish);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void search.search(input.value);
  });
  output.addEventListener("click", (event) => {
    const button = (event.target as Element).closest<HTMLButtonElement>("button");
    if (button?.dataset.retrievalCard) openCard(button.dataset.retrievalCard);
    if (button?.hasAttribute("data-retrieval-browse")) browse();
  });
}
