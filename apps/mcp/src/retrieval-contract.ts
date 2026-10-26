/** Dependency-free reviewed retrieval wire contract, shared by browser and stdio clients. */
export const RETRIEVAL_LIMIT = 10;
export const RETRIEVAL_WARNING =
  "Scores are uncalibrated discovery ranking signals, not semantic proof, compatibility, relation, causality, originality, or historical influence. Results do not add graph edges.";
export const RETRIEVAL_KINDS = [
  "system",
  "feature",
  "view",
  "trade_off",
  "relation",
  "composition",
] as const;
export const RETRIEVAL_CLAIMS = ["fact", "inference", "hypothesis", "analogy"] as const;
export const RETRIEVAL_STATUSES = [
  "proposed",
  "under-review",
  "accepted",
  "rejected",
  "deprecated",
] as const;

export type RetrievalArguments = {
  q: string;
  limit?: number;
  record_kind?: string;
  system_id?: string;
  feature_id?: string;
  category?: string;
  claim_type?: string;
  claim_status?: string;
  version_context?: string;
  deployment_origin?: string;
};
export type RetrievalResponse = {
  schema_version: "1.0";
  query: { q_digest: string; filters: Record<string, unknown> };
  index: {
    status: "ready" | "empty";
    index_id: string;
    corpus: "canonical_cards";
    representation_version: string;
    method: "bounded_lexical_baseline";
    warnings: string[];
  };
  results: Array<{
    rank: number;
    score: number;
    score_kind: "lexical_overlap";
    document: Record<string, unknown> & {
      id: string;
      record_kind: string;
      system_id: string;
      name: string;
      description: string;
      evidence_ids: string[];
      claim_type?: string;
      claim_status?: string;
      version_context?: string | null;
      validity_scope?: Record<string, unknown>;
    };
    evidence: Array<{
      id: string;
      kind: string;
      title: string;
      uri: string;
      accessed?: string | null;
      notes?: string | null;
    }>;
    provenance: {
      source_ref: string;
      source_digest: string;
      retrieval_method: "bounded_lexical_baseline";
    };
  }>;
  warnings: string[];
};

/** Validate before forwarding. Unknown arguments (including draft/provider controls) fail closed. */
export function retrievalParams(value: unknown): URLSearchParams {
  const invalid = () => {
    throw new Error(
      "Invalid retrieval arguments; use a 1–1,000 character query, allowlisted filters, and limit 1–50",
    );
  };
  if (!record(value)) return invalid();
  const allowed = [
    "q",
    "limit",
    "record_kind",
    "system_id",
    "feature_id",
    "category",
    "claim_type",
    "claim_status",
    "version_context",
    "deployment_origin",
  ];
  if (Object.keys(value).some((key) => !allowed.includes(key))) return invalid();
  if (typeof value.q !== "string" || !value.q.trim() || value.q.trim().length > 1000)
    return invalid();
  const limit = value.limit ?? RETRIEVAL_LIMIT;
  if (typeof limit !== "number" || !Number.isInteger(limit) || limit < 1 || limit > 50)
    return invalid();
  const params = new URLSearchParams({ q: value.q.trim(), limit: String(limit) });
  for (const key of allowed.slice(2)) {
    const item = value[key];
    if (item === undefined) continue;
    if (typeof item !== "string" || !item.trim() || item.trim().length > 200) return invalid();
    params.set(key, item.trim());
  }
  const kinds = params
    .get("record_kind")
    ?.split(",")
    .map((kind) => kind.trim())
    .filter(Boolean);
  if (
    kinds &&
    (!kinds.length ||
      kinds.length > 10 ||
      kinds.some((kind) => !RETRIEVAL_KINDS.includes(kind as (typeof RETRIEVAL_KINDS)[number])))
  )
    return invalid();
  if (
    params.has("claim_type") &&
    !RETRIEVAL_CLAIMS.includes(params.get("claim_type") as (typeof RETRIEVAL_CLAIMS)[number])
  )
    return invalid();
  if (
    params.has("claim_status") &&
    !RETRIEVAL_STATUSES.includes(params.get("claim_status") as (typeof RETRIEVAL_STATUSES)[number])
  )
    return invalid();
  if (
    params.has("deployment_origin") &&
    !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$/.test(params.get("deployment_origin")!)
  )
    return invalid();
  return params;
}

/** Preserve hydrated records verbatim, but never publish a draft or broken evidence closure. */
export function normalizeRetrieval(value: unknown, limit = RETRIEVAL_LIMIT): RetrievalResponse {
  const invalid = () => {
    throw new Error("Invalid retrieval response");
  };
  if (
    !record(value) ||
    value.schema_version !== "1.0" ||
    !record(value.query) ||
    typeof value.query.q_digest !== "string" ||
    !record(value.query.filters) ||
    !record(value.index) ||
    value.index.corpus !== "canonical_cards" ||
    !["ready", "empty"].includes(String(value.index.status)) ||
    typeof value.index.index_id !== "string" ||
    typeof value.index.representation_version !== "string" ||
    value.index.method !== "bounded_lexical_baseline" ||
    !strings(value.index.warnings) ||
    !strings(value.warnings) ||
    !Array.isArray(value.results) ||
    value.results.length > Math.min(limit, 50)
  )
    return invalid();
  if (value.index.status === "empty" && value.results.length) return invalid();
  const ids = new Set<string>();
  for (const [index, result] of value.results.entries()) {
    if (
      !record(result) ||
      result.rank !== index + 1 ||
      typeof result.score !== "number" ||
      !Number.isFinite(result.score) ||
      result.score_kind !== "lexical_overlap" ||
      !record(result.document) ||
      !Array.isArray(result.evidence) ||
      !record(result.provenance)
    )
      return invalid();
    const document = result.document;
    const provenance = result.provenance;
    if (
      !["id", "system_id", "record_kind", "name", "description"].every(
        (key) => typeof document[key] === "string",
      ) ||
      !RETRIEVAL_KINDS.includes(document.record_kind as (typeof RETRIEVAL_KINDS)[number]) ||
      !strings(document.evidence_ids) ||
      !document.evidence_ids.length ||
      typeof provenance.source_ref !== "string" ||
      !/^data\/systems\/[a-z0-9-]+\.json#/.test(provenance.source_ref) ||
      typeof provenance.source_digest !== "string" ||
      provenance.retrieval_method !== "bounded_lexical_baseline"
    )
      return invalid();
    if (
      document.claim_type !== undefined &&
      !RETRIEVAL_CLAIMS.includes(document.claim_type as (typeof RETRIEVAL_CLAIMS)[number])
    )
      return invalid();
    if (
      document.claim_status !== undefined &&
      !RETRIEVAL_STATUSES.includes(document.claim_status as (typeof RETRIEVAL_STATUSES)[number])
    )
      return invalid();
    if (document.validity_scope !== undefined && !record(document.validity_scope)) return invalid();
    if (
      document.version_context !== undefined &&
      document.version_context !== null &&
      typeof document.version_context !== "string"
    )
      return invalid();
    if (
      !result.evidence.every(
        (item) =>
          record(item) &&
          ["id", "kind", "title", "uri"].every((key) => typeof item[key] === "string"),
      )
    )
      return invalid();
    const evidenceIds = new Set(result.evidence.map((item) => item.id));
    if (document.evidence_ids.some((id) => !evidenceIds.has(id)) || ids.has(document.id as string))
      return invalid();
    ids.add(document.id as string);
  }
  return structuredClone(value) as RetrievalResponse;
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}
