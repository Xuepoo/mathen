export const RETRIEVAL_CORPUS = "canonical_cards" as const;
export const RETRIEVAL_INDEX_ID = "canonical-cards-d1-lexical-v1" as const;
export const RETRIEVAL_REPRESENTATION = "canonical-record-v1" as const;

export const RECORD_KINDS = [
  "system",
  "feature",
  "view",
  "trade_off",
  "relation",
  "composition",
] as const;
export type RetrievalRecordKind = (typeof RECORD_KINDS)[number];

const CLAIM_TYPES = new Set(["fact", "inference", "hypothesis", "analogy"]);
const CLAIM_STATUSES = new Set(["proposed", "under-review", "accepted", "rejected", "deprecated"]);
const FILTER_NAMES = new Set([
  "record_kind",
  "system_id",
  "feature_id",
  "category",
  "claim_type",
  "claim_status",
  "version_context",
  "deployment_origin",
]);

export type RetrievalFilters = {
  record_kind?: RetrievalRecordKind[];
  system_id?: string;
  feature_id?: string;
  category?: string;
  claim_type?: string;
  claim_status?: string;
  version_context?: string;
  deployment_origin?: string;
};

export type RetrievalQuery = { query: string; limit: number; filters: RetrievalFilters };

export type RetrievalEvidence = {
  id: string;
  kind: string;
  title: string;
  uri: string;
  accessed?: string | null;
  notes?: string | null;
  scope_context?: Record<string, unknown>;
};

export type RetrievalDocument = {
  id: string;
  record_kind: RetrievalRecordKind;
  system_id: string;
  feature_id?: string;
  category?: string;
  name: string;
  description: string;
  text: string;
  claim_type?: string;
  claim_status?: string;
  lifecycle?: Record<string, unknown>;
  version_context?: string | null;
  validity_scope?: Record<string, unknown>;
  scope_context?: Record<string, unknown>;
  evidence_ids: string[];
  evidence: RetrievalEvidence[];
  source_ref: string;
  source_digest: string;
  document: Record<string, unknown>;
};

export type RetrievalSystemRow = {
  id: string;
  name: string;
  version_context: string | null;
  summary: string;
  scope_json: string;
  temporal_context_json: string | null;
  scope_context_json?: string | null;
  relations_json: string | null;
  composition_json: string | null;
  source_path: string;
};

export type RetrievalFeatureRow = {
  id: string;
  system_id: string;
  system_name: string;
  name: string;
  category: string;
  claim_type: string;
  description: string;
  benefits_json: string;
  costs_json: string;
  metadata_json: string;
  evidence_ids_json: string;
};

export type RetrievalViewRow = {
  id: number;
  system_id: string;
  model: string;
  question: string;
  assumptions_json: string;
  claim_type: string;
  metadata_json: string;
  evidence_ids_json: string;
};

export type RetrievalTradeOffRow = {
  id: number;
  system_id: string;
  feature_id: string;
  benefits_json: string;
  costs_json: string;
};

export type RetrievalRelationRow = {
  id: number;
  source_system_id: string;
  source_feature_id: string;
  target_system_id: string;
  target_feature_id: string;
  type: string;
  claim_type: string;
  claim_status: string;
  notes: string | null;
  evidence_ids_json: string;
};

export type RetrievalCompositionRow = {
  system_id: string;
  system_name: string;
  version_context: string | null;
  composition_json: string;
};

export type RetrievalEvidenceRow = RetrievalEvidence & {
  system_id: string;
  scope_context_json?: string | null;
};

export type RetrievalResult = {
  rank: number;
  score: number;
  score_kind: "lexical_overlap";
  document: Record<string, unknown>;
  evidence: RetrievalEvidence[];
  provenance: {
    source_ref: string;
    source_digest: string;
    retrieval_method: "bounded_lexical_baseline";
  };
};

export class RetrievalRequestError extends Error {}

export async function buildRetrievalDocuments(input: {
  systems: RetrievalSystemRow[];
  features: RetrievalFeatureRow[];
  views: RetrievalViewRow[];
  tradeOffs: RetrievalTradeOffRow[];
  relations: RetrievalRelationRow[];
  compositions: RetrievalCompositionRow[];
  evidence: RetrievalEvidenceRow[];
}): Promise<RetrievalDocument[]> {
  const evidenceBySystem = new Map<string, Map<string, RetrievalEvidence>>();
  for (const row of input.evidence) {
    const byId = evidenceBySystem.get(row.system_id) ?? new Map<string, RetrievalEvidence>();
    byId.set(row.id, {
      id: row.id,
      kind: row.kind,
      title: row.title,
      uri: row.uri,
      accessed: row.accessed,
      notes: row.notes,
    });
    evidenceBySystem.set(row.system_id, byId);
  }
  for (const row of input.evidence) {
    const byId = evidenceBySystem.get(row.system_id);
    const evidence = byId?.get(row.id);
    const scopeContext = parseScopeContext(row.scope_context_json, new Set(byId?.keys()));
    if (evidence && scopeContext) evidence.scope_context = scopeContext;
  }
  const systems = new Map(input.systems.map((system) => [system.id, system]));
  const documents: RetrievalDocument[] = [];
  const add = async (document: Omit<RetrievalDocument, "source_digest">) => {
    const sourceDigest = await sha256Digest(JSON.stringify(document.document));
    documents.push({ ...document, source_digest: sourceDigest });
  };
  for (const system of input.systems) {
    const systemScope = parseJsonArray(system.scope_json);
    const temporal = parseRecord(system.temporal_context_json);
    const validityScope = recordValue(temporal.validity_scope);
    const temporalEvidenceIds = stringArray(temporal.evidence_ids);
    const evidenceIds = (
      temporalEvidenceIds.length > 0
        ? temporalEvidenceIds
        : [...(evidenceBySystem.get(system.id)?.keys() ?? [])]
    ).sort();
    const evidence = resolveEvidence(evidenceBySystem.get(system.id), evidenceIds);
    if (evidenceIds.length === 0 || evidence.length !== evidenceIds.length) continue;
    const systemScopeContext = parseScopeContext(system.scope_context_json, new Set(evidenceIds));
    const document = {
      id: `system:${system.id}:summary`,
      record_kind: "system" as const,
      system_id: system.id,
      name: system.name,
      description: system.summary,
      summary: system.summary,
      scope: systemScope,
      claim_type: typeof temporal.claim_type === "string" ? temporal.claim_type : undefined,
      claim_status: typeof temporal.claim_status === "string" ? temporal.claim_status : undefined,
      version_context: system.version_context,
      ...(validityScope ? { validity_scope: validityScope } : {}),
      ...(systemScopeContext ? { scope_context: systemScopeContext } : {}),
      evidence_ids: evidenceIds,
    };
    await add({
      id: document.id,
      record_kind: document.record_kind,
      system_id: system.id,
      name: system.name,
      description: system.summary,
      text: renderText(system, "system", system.name, system.summary, system.summary),
      claim_type: document.claim_type,
      claim_status: document.claim_status,
      version_context: system.version_context,
      validity_scope: validityScope,
      scope_context: systemScopeContext,
      evidence_ids: evidenceIds,
      evidence,
      source_ref: `${system.source_path}#summary`,
      document,
    });
    for (const relation of parseJsonArray(system.relations_json)) {
      const relationRecord = recordValue(relation);
      if (!relationRecord) continue;
      const target = typeof relationRecord.target === "string" ? relationRecord.target : undefined;
      const type = typeof relationRecord.type === "string" ? relationRecord.type : undefined;
      const relationEvidenceIds = stringArray(relationRecord.evidence_ids).sort();
      const relationEvidence = resolveEvidence(
        evidenceBySystem.get(system.id),
        relationEvidenceIds,
      );
      if (
        !target ||
        !type ||
        relationEvidenceIds.length === 0 ||
        relationEvidence.length !== relationEvidenceIds.length
      ) {
        continue;
      }
      const relationKey = encodeURIComponent(
        JSON.stringify([
          target,
          type,
          relationRecord.claim_type ?? null,
          relationRecord.claim_status ?? null,
          relationEvidenceIds,
          relationRecord.notes ?? null,
        ]),
      );
      const relationDocument = {
        id: `system:${system.id}:relation:${relationKey}`,
        record_kind: "relation" as const,
        system_id: system.id,
        name: `${system.id} ${type} ${target}`,
        description: typeof relationRecord.notes === "string" ? relationRecord.notes : type,
        target_system_id: target,
        relation_type: type,
        ...(typeof relationRecord.claim_type === "string"
          ? { claim_type: relationRecord.claim_type }
          : {}),
        ...(typeof relationRecord.claim_status === "string"
          ? { claim_status: relationRecord.claim_status }
          : {}),
        version_context: system.version_context,
        ...(recordValue(relationRecord.validity_scope)
          ? { validity_scope: recordValue(relationRecord.validity_scope) }
          : {}),
        evidence_ids: relationEvidenceIds,
      };
      await add({
        id: relationDocument.id,
        record_kind: relationDocument.record_kind,
        system_id: system.id,
        name: relationDocument.name,
        description: relationDocument.description,
        text: renderText(
          system,
          "relation",
          relationDocument.name,
          relationDocument.description,
          type,
        ),
        claim_type: relationDocument.claim_type,
        claim_status: relationDocument.claim_status,
        version_context: system.version_context,
        validity_scope: recordValue(relationRecord.validity_scope),
        evidence_ids: relationEvidenceIds,
        evidence: relationEvidence,
        source_ref: `${system.source_path}#relations/${relationKey}`,
        document: relationDocument,
      });
    }
  }
  for (const row of input.features) {
    const metadata = parseRecord(row.metadata_json);
    const evidenceIds = stringArray(parseJson(row.evidence_ids_json)).sort();
    const evidence = resolveEvidence(evidenceBySystem.get(row.system_id), evidenceIds);
    const system = systems.get(row.system_id);
    if (!system || evidenceIds.length === 0 || evidence.length !== evidenceIds.length) continue;
    const scope = recordValue(metadata.validity_scope);
    const scopeContext = parseScopeContext(metadata.scope_context, new Set(evidenceIds));
    const document = {
      id: `system:${row.system_id}:feature:${row.id}`,
      record_kind: "feature" as const,
      system_id: row.system_id,
      feature_id: row.id,
      category: row.category,
      name: row.name,
      description: row.description,
      benefits: parseJsonArray(row.benefits_json),
      costs: parseJsonArray(row.costs_json),
      claim_type: row.claim_type,
      ...(typeof metadata.claim_status === "string" ? { claim_status: metadata.claim_status } : {}),
      ...(recordValue(metadata.lifecycle) ? { lifecycle: metadata.lifecycle } : {}),
      version_context: system.version_context,
      ...(scope ? { validity_scope: scope } : {}),
      ...(scopeContext ? { scope_context: scopeContext } : {}),
      evidence_ids: evidenceIds,
    };
    await add({
      id: document.id,
      record_kind: document.record_kind,
      system_id: row.system_id,
      feature_id: row.id,
      category: row.category,
      name: row.name,
      description: row.description,
      text: renderText(
        system,
        "feature",
        row.name,
        row.description,
        `${row.category} ${row.benefits_json} ${row.costs_json}`,
      ),
      claim_type: row.claim_type,
      claim_status: typeof metadata.claim_status === "string" ? metadata.claim_status : undefined,
      lifecycle: recordValue(metadata.lifecycle),
      version_context: system.version_context,
      validity_scope: scope,
      scope_context: scopeContext,
      evidence_ids: evidenceIds,
      evidence,
      source_ref: `${system.source_path}#features/${row.id}`,
      document,
    });
  }
  for (const row of input.views) {
    const metadata = parseRecord(row.metadata_json);
    const evidenceIds = stringArray(parseJson(row.evidence_ids_json)).sort();
    const evidence = resolveEvidence(evidenceBySystem.get(row.system_id), evidenceIds);
    const system = systems.get(row.system_id);
    if (!system || evidenceIds.length === 0 || evidence.length !== evidenceIds.length) continue;
    const scope = recordValue(metadata.validity_scope);
    const scopeContext = parseScopeContext(metadata.scope_context, new Set(evidenceIds));
    const viewId =
      typeof metadata.id === "string" || typeof metadata.id === "number" ? metadata.id : row.id;
    const document = {
      id: `system:${row.system_id}:view:${viewId}`,
      record_kind: "view" as const,
      system_id: row.system_id,
      name: row.model,
      description: row.question,
      model: row.model,
      question: row.question,
      assumptions: parseJsonArray(row.assumptions_json),
      claim_type: row.claim_type,
      ...(typeof metadata.claim_status === "string" ? { claim_status: metadata.claim_status } : {}),
      ...(recordValue(metadata.lifecycle) ? { lifecycle: metadata.lifecycle } : {}),
      version_context: system.version_context,
      ...(scope ? { validity_scope: scope } : {}),
      ...(scopeContext ? { scope_context: scopeContext } : {}),
      evidence_ids: evidenceIds,
    };
    await add({
      id: document.id,
      record_kind: document.record_kind,
      system_id: row.system_id,
      name: row.model,
      description: row.question,
      text: renderText(system, "view", row.model, row.question, row.assumptions_json),
      claim_type: row.claim_type,
      claim_status: typeof metadata.claim_status === "string" ? metadata.claim_status : undefined,
      lifecycle: recordValue(metadata.lifecycle),
      version_context: system.version_context,
      validity_scope: scope,
      scope_context: scopeContext,
      evidence_ids: evidenceIds,
      evidence,
      source_ref: `${system.source_path}#mathematical_views/${viewId}`,
      document,
    });
  }
  for (const row of input.tradeOffs) {
    const system = systems.get(row.system_id);
    const feature = input.features.find(
      (item) => item.system_id === row.system_id && item.id === row.feature_id,
    );
    const evidenceIds = feature ? stringArray(parseJson(feature.evidence_ids_json)).sort() : [];
    const evidence = resolveEvidence(evidenceBySystem.get(row.system_id), evidenceIds);
    if (!system || !feature || evidenceIds.length === 0 || evidence.length !== evidenceIds.length)
      continue;
    const featureMetadata = parseRecord(feature.metadata_json);
    const validityScope = recordValue(featureMetadata.validity_scope);
    const scopeContext = parseScopeContext(featureMetadata.scope_context, new Set(evidenceIds));
    const document = {
      id: `system:${row.system_id}:tradeoff:${row.feature_id}`,
      record_kind: "trade_off" as const,
      system_id: row.system_id,
      feature_id: row.feature_id,
      name: `Trade-offs: ${feature.name}`,
      description: `${row.benefits_json} ${row.costs_json}`,
      benefits: parseJsonArray(row.benefits_json),
      costs: parseJsonArray(row.costs_json),
      claim_type: feature.claim_type,
      ...(typeof featureMetadata.claim_status === "string"
        ? { claim_status: featureMetadata.claim_status }
        : {}),
      ...(recordValue(featureMetadata.lifecycle) ? { lifecycle: featureMetadata.lifecycle } : {}),
      version_context: system.version_context,
      ...(validityScope ? { validity_scope: validityScope } : {}),
      ...(scopeContext ? { scope_context: scopeContext } : {}),
      evidence_ids: evidenceIds,
    };
    await add({
      id: document.id,
      record_kind: document.record_kind,
      system_id: row.system_id,
      feature_id: row.feature_id,
      name: document.name,
      description: document.description,
      text: renderText(
        system,
        "trade-off",
        document.name,
        document.description,
        `${row.benefits_json} ${row.costs_json}`,
      ),
      claim_type: feature.claim_type,
      claim_status:
        typeof featureMetadata.claim_status === "string" ? featureMetadata.claim_status : undefined,
      lifecycle: recordValue(featureMetadata.lifecycle),
      version_context: system.version_context,
      validity_scope: validityScope,
      scope_context: scopeContext,
      evidence_ids: evidenceIds,
      evidence,
      source_ref: `${system.source_path}#trade_offs/${row.feature_id}`,
      document,
    });
  }
  for (const row of input.relations) {
    const system = systems.get(row.source_system_id);
    const evidenceIds = stringArray(parseJson(row.evidence_ids_json)).sort();
    const evidence = resolveEvidence(evidenceBySystem.get(row.source_system_id), evidenceIds);
    if (!system || evidenceIds.length === 0 || evidence.length !== evidenceIds.length) continue;
    const document = {
      id: `system:${row.source_system_id}:relation:feature:${row.id}`,
      record_kind: "relation" as const,
      system_id: row.source_system_id,
      feature_id: row.source_feature_id,
      name: `${row.source_feature_id} ${row.type} ${row.target_system_id}:${row.target_feature_id}`,
      description: row.notes ?? row.type,
      target_system_id: row.target_system_id,
      target_feature_id: row.target_feature_id,
      relation_type: row.type,
      claim_type: row.claim_type,
      claim_status: row.claim_status,
      version_context: system.version_context,
      evidence_ids: evidenceIds,
    };
    await add({
      id: document.id,
      record_kind: document.record_kind,
      system_id: row.source_system_id,
      feature_id: row.source_feature_id,
      name: document.name,
      description: document.description,
      text: renderText(system, "relation", document.name, document.description, row.type),
      claim_type: row.claim_type,
      claim_status: row.claim_status,
      version_context: system.version_context,
      evidence_ids: evidenceIds,
      evidence,
      source_ref: `${system.source_path}#feature_relations/${row.id}`,
      document,
    });
  }
  for (const row of input.compositions) {
    const system = systems.get(row.system_id);
    const composition = parseRecord(row.composition_json);
    const evidenceIds = stringArray(composition.evidence_ids).sort();
    const evidence = resolveEvidence(evidenceBySystem.get(row.system_id), evidenceIds);
    if (!system || evidenceIds.length === 0 || evidence.length !== evidenceIds.length) continue;
    const document = {
      id: `system:${row.system_id}:composition`,
      record_kind: "composition" as const,
      system_id: row.system_id,
      name: `Composition proposal: ${row.system_name}`,
      description: JSON.stringify(composition),
      composition,
      claim_type: typeof composition.claim_type === "string" ? composition.claim_type : undefined,
      claim_status:
        typeof composition.claim_status === "string" ? composition.claim_status : undefined,
      version_context: row.version_context,
      ...(recordValue(composition.validity_scope)
        ? { validity_scope: recordValue(composition.validity_scope) }
        : {}),
      evidence_ids: evidenceIds,
    };
    await add({
      id: document.id,
      record_kind: document.record_kind,
      system_id: row.system_id,
      name: document.name,
      description: document.description,
      text: renderText(
        system,
        "composition",
        document.name,
        document.description,
        JSON.stringify(composition.inputs ?? ""),
      ),
      claim_type: document.claim_type,
      claim_status: document.claim_status,
      version_context: row.version_context,
      validity_scope: recordValue(composition.validity_scope),
      evidence_ids: evidenceIds,
      evidence,
      source_ref: `${system.source_path}#composition`,
      document,
    });
  }
  return documents.sort((a, b) => a.id.localeCompare(b.id));
}

export function parseRetrievalQuery(params: URLSearchParams): RetrievalQuery {
  for (const key of params.keys()) {
    if (key !== "q" && key !== "limit" && !FILTER_NAMES.has(key)) {
      throw new RetrievalRequestError(`Unknown retrieval parameter: ${key}`);
    }
  }
  const query = params.get("q")?.trim() ?? "";
  if (!query || query.length > 1_000) {
    throw new RetrievalRequestError("q must contain 1 to 1,000 characters");
  }
  const rawLimit = params.get("limit");
  const limit = rawLimit === null ? 10 : parseBoundedInteger(rawLimit, 1, 50, "limit");
  const filters: RetrievalFilters = {};
  const kinds = params.getAll("record_kind").flatMap((value) =>
    value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  );
  if (
    kinds.length > 10 ||
    kinds.some((kind) => !RECORD_KINDS.includes(kind as RetrievalRecordKind))
  ) {
    throw new RetrievalRequestError("record_kind contains an unsupported value or too many values");
  }
  if (kinds.length) filters.record_kind = [...new Set(kinds)] as RetrievalRecordKind[];
  for (const name of ["system_id", "feature_id", "category", "version_context"] as const) {
    const value = params.get(name)?.trim();
    if (value) {
      if (value.length > 200) throw new RetrievalRequestError(`${name} is too long`);
      filters[name] = value;
    }
  }
  const claimType = params.get("claim_type")?.trim();
  if (claimType) {
    if (!CLAIM_TYPES.has(claimType)) throw new RetrievalRequestError("claim_type is unsupported");
    filters.claim_type = claimType;
  }
  const claimStatus = params.get("claim_status")?.trim();
  if (claimStatus) {
    if (!CLAIM_STATUSES.has(claimStatus))
      throw new RetrievalRequestError("claim_status is unsupported");
    filters.claim_status = claimStatus;
  }
  const origin = params.get("deployment_origin")?.trim();
  if (origin) {
    if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$/.test(origin)) {
      throw new RetrievalRequestError("deployment_origin is malformed");
    }
    filters.deployment_origin = origin;
  }
  return { query, limit, filters };
}

export function rankRetrievalDocuments(
  documents: RetrievalDocument[],
  retrievalQuery: RetrievalQuery,
): RetrievalResult[] {
  const terms = tokenize(retrievalQuery.query);
  if (terms.length === 0) return [];
  return documents
    .filter((document) => matchesFilters(document, retrievalQuery.filters))
    .map((document) => ({ document, score: lexicalScore(document, terms) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || a.document.id.localeCompare(b.document.id))
    .slice(0, retrievalQuery.limit)
    .map(({ document, score }, index) => ({
      rank: index + 1,
      score: Number(score.toFixed(6)),
      score_kind: "lexical_overlap",
      document: document.document,
      evidence: document.evidence,
      provenance: {
        source_ref: document.source_ref,
        source_digest: document.source_digest,
        retrieval_method: "bounded_lexical_baseline",
      },
    }));
}

export function matchesFilters(document: RetrievalDocument, filters: RetrievalFilters): boolean {
  if (filters.record_kind && !filters.record_kind.includes(document.record_kind)) return false;
  if (filters.system_id && filters.system_id !== document.system_id) return false;
  if (filters.feature_id && filters.feature_id !== document.feature_id) return false;
  if (filters.category && filters.category !== document.category) return false;
  if (filters.claim_type && filters.claim_type !== document.claim_type) return false;
  if (filters.claim_status && filters.claim_status !== document.claim_status) return false;
  if (filters.version_context && filters.version_context !== document.version_context) return false;
  if (filters.deployment_origin) {
    const origins = document.validity_scope?.deployment_origins;
    if (!Array.isArray(origins) || !origins.includes(filters.deployment_origin)) return false;
  }
  return true;
}

export async function sha256Digest(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

function lexicalScore(document: RetrievalDocument, terms: string[]): number {
  const titleTerms = new Set(tokenize(document.name));
  const bodyTerms = new Set(tokenize(document.text));
  const matched = terms.filter((term) => bodyTerms.has(term)).length;
  const titleMatched = terms.filter((term) => titleTerms.has(term)).length;
  return Math.min(1, (matched + titleMatched * 0.5) / terms.length);
}

function tokenize(value: string): string[] {
  return [
    ...new Set(
      value
        .normalize("NFKC")
        .toLowerCase()
        .match(/[\p{L}\p{N}]+/gu) ?? [],
    ),
  ];
}

function parseBoundedInteger(value: string, min: number, max: number, name: string): number {
  if (!/^[0-9]+$/.test(value)) throw new RetrievalRequestError(`${name} must be an integer`);
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < min || number > max) {
    throw new RetrievalRequestError(`${name} must be between ${min} and ${max}`);
  }
  return number;
}

function parseJson(value: string | null): unknown {
  if (!value) return [];
  try {
    return JSON.parse(value);
  } catch {
    return [];
  }
}

function parseJsonArray(value: string | null): unknown[] {
  const parsed = parseJson(value);
  return Array.isArray(parsed) ? parsed : [];
}

function parseRecord(value: string | null): Record<string, unknown> {
  const parsed = parseJson(value);
  return recordValue(parsed) ?? {};
}

function parseOptionalRecord(
  value: string | null | undefined,
): Record<string, unknown> | undefined {
  if (!value) return undefined;
  const parsed = parseRecord(value);
  return Object.keys(parsed).length ? parsed : undefined;
}

function parseScopeContext(
  value: unknown,
  evidenceIds: Set<string>,
): Record<string, unknown> | undefined {
  const parsed = typeof value === "string" ? parseOptionalRecord(value) : recordValue(value);
  if (!parsed) return undefined;
  const fields = [
    "validity_scope",
    "workload",
    "runtime_conditions",
    "scale",
    "failure_conditions",
  ];
  if (
    Object.keys(parsed).length !== fields.length ||
    fields.some((field) => !Object.hasOwn(parsed, field)) ||
    !validValidityScope(parsed.validity_scope, evidenceIds) ||
    fields.slice(1).some((field) => !validScopeDimension(parsed[field], evidenceIds))
  )
    return undefined;
  return parsed;
}

function validValidityScope(value: unknown, evidenceIds: Set<string>): boolean {
  if (!recordValue(value)) return false;
  const scope = recordValue(value)!;
  const required = [
    "status",
    "systems",
    "versions",
    "deployment_origins",
    "conditions",
    "exclusions",
    "evidence_ids",
  ];
  if (
    Object.keys(scope).some(
      (field) =>
        !required.includes(field) && !["claim_type", "claim_status", "notes"].includes(field),
    ) ||
    required.some((field) => !Object.hasOwn(scope, field)) ||
    !["specified", "unknown", "unspecified", "not-applicable"].includes(String(scope.status))
  )
    return false;
  if (!required.slice(1).every((field) => isStringArray(scope[field]))) return false;
  if (!localScopeEvidence(scope, evidenceIds)) return false;
  if (scope.status === "unspecified") {
    return (
      !Object.hasOwn(scope, "claim_type") &&
      !Object.hasOwn(scope, "claim_status") &&
      required.slice(1).every((field) => stringArray(scope[field]).length === 0)
    );
  }
  if (scope.status === "unknown" && scope.claim_type === "analogy") return false;
  return (
    validClaimFields(scope) &&
    (scope.status === "specified"
      ? required.slice(1, 6).some((field) => stringArray(scope[field]).length > 0)
      : required.slice(1, 6).every((field) => stringArray(scope[field]).length === 0)) &&
    (scope.status !== "not-applicable" ||
      (typeof scope.notes === "string" && scope.notes.trim().length > 0))
  );
}

function validScopeDimension(value: unknown, evidenceIds: Set<string>): boolean {
  const dimension = recordValue(value);
  if (
    !dimension ||
    !["status", "values", "evidence_ids"].every((field) => Object.hasOwn(dimension, field))
  )
    return false;
  if (
    !Object.keys(dimension).every((field) =>
      ["status", "values", "evidence_ids", "claim_type", "claim_status", "notes"].includes(field),
    )
  )
    return false;
  if (!["specified", "unknown", "unspecified", "not-applicable"].includes(String(dimension.status)))
    return false;
  const values = stringArray(dimension.values);
  const cited = stringArray(dimension.evidence_ids);
  if (
    !isStringArray(dimension.values) ||
    !isStringArray(dimension.evidence_ids) ||
    !localScopeEvidence(dimension, evidenceIds)
  )
    return false;
  if (dimension.status === "unspecified")
    return (
      values.length === 0 &&
      cited.length === 0 &&
      !Object.hasOwn(dimension, "claim_type") &&
      !Object.hasOwn(dimension, "claim_status")
    );
  return (
    validClaimFields(dimension) &&
    (dimension.status === "specified" ? values.length > 0 : values.length === 0) &&
    (dimension.status !== "not-applicable" ||
      (typeof dimension.notes === "string" && dimension.notes.trim().length > 0))
  );
}

function validClaimFields(value: Record<string, unknown>): boolean {
  return (
    ["fact", "inference", "hypothesis", "analogy"].includes(String(value.claim_type)) &&
    ["proposed", "under-review", "accepted", "rejected", "deprecated"].includes(
      String(value.claim_status),
    ) &&
    stringArray(value.evidence_ids).length > 0
  );
}

function localScopeEvidence(value: Record<string, unknown>, evidenceIds: Set<string>): boolean {
  const cited = stringArray(value.evidence_ids);
  return isStringArray(value.evidence_ids) && cited.every((id) => evidenceIds.has(id));
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function resolveEvidence(
  byId: Map<string, RetrievalEvidence> | undefined,
  ids: string[],
): RetrievalEvidence[] {
  return ids.flatMap((id) => {
    const evidence = byId?.get(id);
    return evidence ? [evidence] : [];
  });
}

function renderText(
  system: RetrievalSystemRow,
  kind: string,
  name: string,
  description: string,
  extra: string,
): string {
  return [
    `system: ${system.id}`,
    `record: ${kind} ${name}`,
    `name: ${name}`,
    `summary: ${description}`,
    `scope: ${system.scope_json}`,
    `version_context: ${system.version_context ?? ""}`,
    extra,
  ].join("\n");
}
