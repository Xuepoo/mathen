import { Hono } from "hono";

type Bindings = {
  DB: D1Database;
  APP_ENV: string;
  ASSETS: Fetcher;
};

type SystemRow = {
  id: string;
  name: string;
  version_context: string | null;
  temporal_context_json: string | null;
  relations_json: string | null;
  composition_json: string | null;
  summary: string;
  scope_json: string;
  related_systems_json: string;
  source_path: string;
};

type FeatureRow = {
  id: string;
  name: string;
  category: string;
  claim_type: string;
  description: string;
  benefits_json: string;
  costs_json: string;
  evidence_ids_json: string;
};

type EvidenceRow = {
  id: string;
  kind: string;
  title: string;
  uri: string;
  accessed: string | null;
  notes: string | null;
};

type GraphSystem = Pick<
  SystemRow,
  "id" | "name" | "related_systems_json" | "relations_json"
>;

type CompositionSystem = Pick<
  SystemRow,
  "id" | "name" | "version_context" | "composition_json"
> & {
  evidence_json?: string | null;
};

export type GraphEdge = {
  source: string;
  target: string;
  type: string;
  claim_type?: string;
  claim_status?: string;
  evidence_ids?: string[];
  notes?: string;
};

export type Graph = {
  nodes: Array<{ id: string; name: string; type: "system" }>;
  edges: GraphEdge[];
};

const app = new Hono<{ Bindings: Bindings }>().basePath("/api");

app.get("/health", (c) =>
  c.json({ status: "ok", service: "mathen-api", environment: c.env.APP_ENV }),
);

app.get("/systems", async (c) => {
  const query = c.req.query("query")?.trim() ?? "";
  const limit = boundedInteger(c.req.query("limit"), 50, 1, 100);
  const pattern = `%${query}%`;
  const result = await c.env.DB.prepare(
    `SELECT id, name, version_context, summary, scope_json, related_systems_json,
            temporal_context_json, relations_json, composition_json, source_path
     FROM systems
     WHERE (?1 = '' OR id LIKE ?2 OR name LIKE ?2 OR summary LIKE ?2)
     ORDER BY name
     LIMIT ?3`,
  )
    .bind(query, pattern, limit)
    .all<SystemRow>();

  return c.json({ data: result.results.map(serializeSystem) });
});

app.get("/systems/:id", async (c) => {
  const system = await c.env.DB.prepare(
    `SELECT id, name, version_context, summary, scope_json, related_systems_json,
               temporal_context_json, relations_json, composition_json, source_path
     FROM systems WHERE id = ?1`,
  )
    .bind(c.req.param("id"))
    .first<SystemRow>();

  if (!system) {
    return c.json({ error: "System not found" }, 404);
  }

  const [features, views, tradeOffs, evidence] = await Promise.all([
    c.env.DB.prepare(
      `SELECT id, name, category, claim_type, description, benefits_json, costs_json
              , COALESCE((
                SELECT json_group_array(substr(fe.evidence_id, length(fe.system_id) + 2))
                FROM feature_evidence fe
                WHERE fe.system_id = ?1 AND fe.feature_id = features.id
                ORDER BY fe.evidence_id
              ), '[]') AS evidence_ids_json
       FROM features WHERE system_id = ?1 ORDER BY category, name`,
    )
      .bind(system.id)
      .all<FeatureRow>(),
    c.env.DB.prepare(
      `SELECT id, model, question, assumptions_json, claim_type,
              COALESCE((
                SELECT json_group_array(substr(mve.evidence_id, length(mathematical_views.system_id) + 2))
                FROM mathematical_view_evidence mve
                WHERE mve.view_id = mathematical_views.id
                ORDER BY mve.evidence_id
              ), '[]') AS evidence_ids_json
       FROM mathematical_views WHERE system_id = ?1 ORDER BY id`,
    )
      .bind(system.id)
      .all<{
        id: number;
        model: string;
        question: string;
        assumptions_json: string;
        claim_type: string;
        evidence_ids_json: string;
      }>(),
    c.env.DB.prepare(
      `SELECT id, feature_id, benefits_json, costs_json
       FROM trade_offs WHERE system_id = ?1 ORDER BY id`,
    )
      .bind(system.id)
      .all<{
        id: number;
        feature_id: string;
        benefits_json: string;
        costs_json: string;
      }>(),
    c.env.DB.prepare(
      `SELECT substr(id, length(system_id) + 2) AS id, kind, title, uri, accessed, notes
       FROM evidence WHERE system_id = ?1 ORDER BY id`,
    )
      .bind(system.id)
      .all<EvidenceRow>(),
  ]);

  return c.json({
    data: {
      ...serializeSystem(system),
      features: features.results.map(serializeFeature),
      mathematical_views: views.results.map((view) => ({
        id: view.id,
        model: view.model,
        question: view.question,
        assumptions: parseJson<string[]>(view.assumptions_json, []),
        claim_type: view.claim_type,
        evidence_ids: parseJsonArray<string>(view.evidence_ids_json),
      })),
      trade_offs: tradeOffs.results.map((tradeOff) => ({
        id: tradeOff.id,
        feature_id: tradeOff.feature_id,
        benefits: parseJson<string[]>(tradeOff.benefits_json, []),
        costs: parseJson<string[]>(tradeOff.costs_json, []),
      })),
      evidence: evidence.results,
    },
  });
});

app.get("/features", async (c) => {
  const query = c.req.query("query")?.trim() ?? "";
  const category = c.req.query("category")?.trim() ?? "";
  const claimType = c.req.query("claim_type")?.trim() ?? "";
  const limit = boundedInteger(c.req.query("limit"), 100, 1, 200);
  const result = await c.env.DB.prepare(
    `SELECT f.id, f.system_id, s.name AS system_name, f.name, f.category,
            f.claim_type, f.description, f.benefits_json, f.costs_json,
            COALESCE((
              SELECT json_group_array(substr(fe.evidence_id, length(fe.system_id) + 2))
              FROM feature_evidence fe
              WHERE fe.system_id = f.system_id AND fe.feature_id = f.id
              ORDER BY fe.evidence_id
            ), '[]') AS evidence_ids_json
     FROM features f
     JOIN systems s ON s.id = f.system_id
     WHERE (?1 = '' OR f.id LIKE ?2 OR f.name LIKE ?2 OR f.description LIKE ?2)
       AND (?3 = '' OR f.category = ?3)
       AND (?4 = '' OR f.claim_type = ?4)
     ORDER BY f.category, f.name
     LIMIT ?5`,
  )
    .bind(query, `%${query}%`, category, claimType, limit)
    .all<FeatureRow & { system_id: string; system_name: string }>();

  return c.json({
    data: result.results.map((feature) => ({
      ...serializeFeature(feature),
      system_id: feature.system_id,
      system_name: feature.system_name,
    })),
  });
});

app.get("/compositions", async (c) => {
  const inputSystem = c.req.query("input_system")?.trim() ?? "";
  const claimStatus = c.req.query("claim_status")?.trim() ?? "";
  const limit = boundedInteger(c.req.query("limit"), 100, 1, 200);
  const result = await c.env.DB.prepare(
    `SELECT id, name, version_context, composition_json,
            COALESCE((
              SELECT json_group_array(json_object(
                'id', substr(e.id, length(e.system_id) + 2),
                'kind', e.kind,
                'title', e.title,
                'uri', e.uri,
                'accessed', e.accessed,
                'notes', e.notes
              ))
              FROM evidence e
              WHERE e.system_id = systems.id
            ), '[]') AS evidence_json
     FROM systems
     WHERE composition_json IS NOT NULL
     ORDER BY name, id`,
  ).all<CompositionSystem>();

  return c.json({
    data: buildCompositions(result.results, inputSystem, claimStatus, limit),
  });
});

app.get("/modeling/:id", async (c) => {
  const row = await c.env.DB.prepare(
    `SELECT id, commit_sha, provenance, bundle_json, source_path
     FROM modeling_bundles WHERE id = ?1`,
  )
    .bind(c.req.param("id"))
    .first<{
      id: string;
      commit_sha: string;
      provenance: string;
      bundle_json: string;
      source_path: string;
    }>();

  if (!row) return c.json({ error: "Modeling bundle not found" }, 404);
  const bundle = parseJson<Record<string, unknown> | null>(
    row.bundle_json,
    null,
  );
  if (!bundle)
    return c.json({ error: "Stored modeling bundle is invalid" }, 500);
  return c.json({ data: bundle });
});

app.get("/graph", async (c) => {
  const systems = await c.env.DB.prepare(
    "SELECT id, name, related_systems_json, relations_json FROM systems ORDER BY name",
  ).all<GraphSystem>();

  return c.json(buildGraph(systems.results));
});

export function buildGraph(systems: GraphSystem[]): Graph {
  const knownSystemIds = new Set(systems.map((system) => system.id));
  const nodes = systems.map((system) => ({
    id: system.id,
    name: system.name,
    type: "system" as const,
  }));
  const edges = systems.flatMap((system) => [
    ...typedRelationEdges(system, knownSystemIds),
    ...legacyRelationEdges(system, knownSystemIds),
  ]);

  return { nodes, edges };
}

export type CompositionResult = {
  system_id: string;
  system_name: string;
  version_context: string | null;
  composition: Record<string, unknown>;
  evidence: EvidenceRow[];
};

export function buildCompositions(
  systems: CompositionSystem[],
  inputSystem = "",
  claimStatus = "",
  limit = 100,
): CompositionResult[] {
  return systems
    .flatMap((system) => {
      const composition = parseJson<Record<string, unknown> | null>(
        system.composition_json,
        null,
      );
      if (!isCompositionRecord(composition)) return [];
      if (
        inputSystem &&
        !composition.inputs.some((input) => input.system_id === inputSystem)
      ) {
        return [];
      }
      if (claimStatus && composition.claim_status !== claimStatus) return [];

      return [
        {
          system_id: system.id,
          system_name: system.name,
          version_context: system.version_context,
          composition,
          evidence: compositionEvidence(system, composition),
        },
      ];
    })
    .slice(0, limit);
}

function compositionEvidence(
  system: CompositionSystem,
  composition: { evidence_ids: string[] },
): EvidenceRow[] {
  const byId = new Map(
    parseJsonArray<EvidenceRow>(system.evidence_json ?? null).map((evidence) => [
      evidence.id,
      evidence,
    ]),
  );
  return composition.evidence_ids.flatMap((id) => {
    const evidence = byId.get(id);
    return evidence ? [evidence] : [];
  });
}

function typedRelationEdges(
  system: GraphSystem,
  knownSystemIds: Set<string>,
): GraphEdge[] {
  const relations = parseJsonArray<Record<string, unknown>>(
    system.relations_json,
  ).filter(isRecord);
  return relations.flatMap((relation) => {
    const target = stringValue(relation.target);
    const type = stringValue(relation.type);
    if (!target || !type || !knownSystemIds.has(target)) return [];

    const edge: GraphEdge = { source: system.id, target, type };
    const claimType = stringValue(relation.claim_type);
    const claimStatus = stringValue(relation.claim_status);
    const notes = stringValue(relation.notes);
    const evidenceIds = stringArrayValue(relation.evidence_ids);
    if (claimType) edge.claim_type = claimType;
    if (claimStatus) edge.claim_status = claimStatus;
    if (notes) edge.notes = notes;
    if (evidenceIds) edge.evidence_ids = evidenceIds;
    return [edge];
  });
}

function legacyRelationEdges(
  system: GraphSystem,
  knownSystemIds: Set<string>,
): GraphEdge[] {
  return parseJsonArray<string>(system.related_systems_json).flatMap(
    (target) => {
      const normalizedTarget = stringValue(target);
      return normalizedTarget && knownSystemIds.has(normalizedTarget)
        ? [{ source: system.id, target: normalizedTarget, type: "related" }]
        : [];
    },
  );
}

function serializeSystem(system: SystemRow) {
  return {
    id: system.id,
    name: system.name,
    version_context: system.version_context,
    summary: system.summary,
    scope: parseJson<string[]>(system.scope_json, []),
    related_systems: parseJson<string[]>(system.related_systems_json, []),
    temporal_context: parseJson<Record<string, unknown> | null>(
      system.temporal_context_json,
      null,
    ),
    relations: parseJson<Array<Record<string, unknown>>>(
      system.relations_json,
      [],
    ),
    composition: parseJson<Record<string, unknown> | null>(
      system.composition_json,
      null,
    ),
    source_path: system.source_path,
  };
}

export function serializeFeature(feature: FeatureRow) {
  return {
    id: feature.id,
    name: feature.name,
    category: feature.category,
    claim_type: feature.claim_type,
    description: feature.description,
    benefits: parseJson<string[]>(feature.benefits_json, []),
    costs: parseJson<string[]>(feature.costs_json, []),
    evidence_ids: parseJsonArray<string>(feature.evidence_ids_json),
  };
}

export function serializeMathematicalView(view: {
  id: number;
  model: string;
  question: string;
  assumptions_json: string;
  claim_type: string;
  evidence_ids_json: string;
}) {
  return {
    id: view.id,
    model: view.model,
    question: view.question,
    assumptions: parseJson<string[]>(view.assumptions_json, []),
    claim_type: view.claim_type,
    evidence_ids: parseJsonArray<string>(view.evidence_ids_json),
  };
}

function parseJson<T>(value: string | null, fallback: T): T {
  if (value === null) return fallback;
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function parseJsonArray<T>(value: string | null): T[] {
  const parsed = parseJson<unknown>(value, null);
  return Array.isArray(parsed) ? (parsed as T[]) : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCompositionRecord(
  value: Record<string, unknown> | null,
): value is Record<string, unknown> & {
  inputs: Array<Record<string, unknown> & { system_id: string }>;
  claim_status: string;
  constraints: unknown[];
  preserved_properties: unknown[];
  conflicts: unknown[];
  evidence_ids: string[];
} {
  if (!value || !stringValue(value.claim_status)) return false;
  if (!Array.isArray(value.inputs) || value.inputs.length === 0) return false;
  if (!Array.isArray(value.constraints)) return false;
  if (!Array.isArray(value.preserved_properties)) return false;
  if (!Array.isArray(value.conflicts)) return false;
  if (
    !Array.isArray(value.evidence_ids) ||
    value.evidence_ids.length === 0 ||
    !value.evidence_ids.every(
      (item) => typeof item === "string" && item.length > 0,
    )
  ) {
    return false;
  }
  return value.inputs.every(
    (input) => isRecord(input) && Boolean(stringValue(input.system_id)),
  );
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function stringArrayValue(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const values = value.filter(
    (item): item is string => typeof item === "string" && item.length > 0,
  );
  return values.length ? values : undefined;
}

function boundedInteger(
  value: string | undefined,
  fallback: number,
  min: number,
  max: number,
) {
  const parsed = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(Math.max(parsed, min), max);
}

const worker = {
  fetch(request: Request, env: Bindings, ctx: ExecutionContext) {
    const pathname = new URL(request.url).pathname;
    if (pathname === "/api" || pathname.startsWith("/api/")) {
      return app.fetch(request, env, ctx);
    }
    return env.ASSETS.fetch(request);
  },
};

export default worker;
