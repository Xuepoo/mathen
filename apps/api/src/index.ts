import { Hono } from "hono";
import { buildModelGraph, modelViewKey, type ModelViewRow } from "./model-graph.js";
import {
  accessCookieName,
  accessProtectionEnabled,
  accessSetCookie,
  accessSiteKey,
  createAccessCookie,
  InMemoryRateLimiter,
  hasServiceToken,
  parseCookie,
  verifyAccessCookie,
  verifyTurnstileToken,
  turnstileHostname,
  configuredRateLimit,
} from "./access.js";
import {
  createMcpApiBackend,
  handleMcpRequest,
  mcpAuthorized,
  mcpCorsHeaders,
  mcpOriginAllowed,
} from "./mcp.js";
import {
  buildLayeredGraphProjection,
  stableProjectionViewId,
  type ProjectionAnalogy,
  type ProjectionMicrostructure,
  type ProjectionSystem,
} from "./graph-projection.js";

type Bindings = {
  DB: D1Database;
  APP_ENV: string;
  ASSETS: Fetcher;
  TURNSTILE_SECRET_KEY?: string;
  TURNSTILE_SITE_KEY?: string;
  TURNSTILE_HOSTNAME?: string;
  TURNSTILE_SESSION_TTL_SECONDS?: string;
  API_ACCESS_TOKEN?: string;
  API_RATE_LIMIT_PER_MINUTE?: string;
  API_RATE_LIMIT_WINDOW_SECONDS?: string;
  MCP_RATE_LIMIT_PER_MINUTE?: string;
  MCP_RATE_LIMIT_WINDOW_SECONDS?: string;
  MCP_ALLOWED_ORIGINS?: string;
  ARTIFACTS?: R2Bucket;
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
  metadata_json?: string;
};

type EvidenceRow = {
  id: string;
  kind: string;
  title: string;
  uri: string;
  accessed: string | null;
  notes: string | null;
};

type FeatureRelationRow = {
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

type GraphSystem = Pick<SystemRow, "id" | "name" | "related_systems_json" | "relations_json">;

type CompositionSystem = Pick<SystemRow, "id" | "name" | "version_context" | "composition_json"> & {
  evidence_json?: string | null;
};

type GraphDocumentRow = {
  id: string;
  kind: "microstructure" | "analogy";
  name: string;
  document_json: string;
};

type GraphLayerSystemRow = {
  id: string;
  name: string;
  scope_json: string;
  relations_json: string | null;
  composition_json: string | null;
  features_json: string;
  views_json: string;
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

export const app = new Hono<{ Bindings: Bindings }>().basePath("/api");

const accessRateLimiter = new InMemoryRateLimiter();
const mcpRateLimiter = new InMemoryRateLimiter();

app.use("*", async (c, next) => {
  const pathname = new URL(c.req.url).pathname;
  if (
    pathname === "/api/health" ||
    pathname === "/api/access/config" ||
    pathname === "/api/access/turnstile"
  ) {
    return next();
  }
  const ip = c.req.header("CF-Connecting-IP") ?? "unknown";
  const limit = accessRateLimiter.consume(
    `api:${ip}`,
    configuredRateLimit(c.env.API_RATE_LIMIT_PER_MINUTE, 120),
    configuredRateLimit(c.env.API_RATE_LIMIT_WINDOW_SECONDS, 60, 1, 3_600) * 1_000,
  );
  if (!limit.allowed) {
    return c.json({ error: "Too many requests", code: "rate_limited" }, 429, {
      "Retry-After": String(limit.retryAfterSeconds),
    });
  }
  if (accessProtectionEnabled(c.env)) {
    const cookie = parseCookie(c.req.header("Cookie") ?? null, accessCookieName());
    if (!hasServiceToken(c.req.raw, c.env) && !(await verifyAccessCookie(cookie, c.env))) {
      return c.json(
        {
          error: "Turnstile access verification required",
          code: "access_required",
        },
        403,
      );
    }
  }
  return next();
});

app.get("/health", (c) =>
  c.json({ status: "ok", service: "mathen-api", environment: c.env.APP_ENV }),
);

app.all("/mcp", async (c) => {
  const corsHeaders = mcpCorsHeaders(c.req.raw, c.env.MCP_ALLOWED_ORIGINS);
  if (c.req.method === "OPTIONS") {
    if (!mcpOriginAllowed(c.req.raw, c.env.MCP_ALLOWED_ORIGINS)) {
      return c.json({ error: "MCP origin is not allowed", code: "origin_denied" }, 403);
    }
    return new Response(null, { status: 204, headers: corsHeaders });
  }
  if (!mcpOriginAllowed(c.req.raw, c.env.MCP_ALLOWED_ORIGINS)) {
    return c.json(
      { error: "MCP origin is not allowed", code: "origin_denied" },
      403,
      Object.fromEntries(corsHeaders),
    );
  }
  if (!mcpAuthorized(c.req.raw, c.env.API_ACCESS_TOKEN)) {
    return c.json({ error: "MCP bearer authentication required", code: "unauthorized" }, 401, {
      "WWW-Authenticate": "Bearer",
      ...Object.fromEntries(corsHeaders),
    });
  }
  const ip = c.req.header("CF-Connecting-IP") ?? "unknown";
  const limit = mcpRateLimiter.consume(
    `mcp:${ip}`,
    configuredRateLimit(c.env.MCP_RATE_LIMIT_PER_MINUTE, 60),
    configuredRateLimit(c.env.MCP_RATE_LIMIT_WINDOW_SECONDS, 60, 1, 3_600) * 1_000,
  );
  if (!limit.allowed) {
    return c.json({ error: "Too many MCP requests", code: "rate_limited" }, 429, {
      "Retry-After": String(limit.retryAfterSeconds),
      ...Object.fromEntries(corsHeaders),
    });
  }
  const apiToken = c.env.API_ACCESS_TOKEN?.trim();
  const backend = createMcpApiBackend(async (path) => {
    const request = new Request(new URL(`/api${path}`, c.req.url), {
      method: "GET",
      headers: { Authorization: `Bearer ${apiToken}` },
    });
    const response = await app.fetch(request, c.env, c.executionCtx);
    if (!response.ok) throw new Error(`API request failed: ${response.status}`);
    const body = (await response.json()) as { data?: unknown };
    return body.data;
  });
  try {
    const response = await handleMcpRequest(c.req.raw, backend);
    const headers = new Headers(response.headers);
    for (const [name, value] of corsHeaders) headers.set(name, value);
    headers.set("X-Request-ID", crypto.randomUUID());
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  } catch {
    return c.json(
      { error: "MCP request failed", code: "mcp_error" },
      500,
      Object.fromEntries(corsHeaders),
    );
  }
});

app.get("/artifacts/*", async (c) => {
  const key = artifactKey(c.req.path);
  if (!key) return c.json({ error: "Invalid artifact key" }, 400);
  if (!c.env.ARTIFACTS) return c.json({ error: "Artifact storage is not configured" }, 503);
  const object = await c.env.ARTIFACTS.get(key);
  if (!object) return c.json({ error: "Artifact not found" }, 404);
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("etag", object.httpEtag);
  headers.set("cache-control", "public, max-age=31536000, immutable");
  return new Response(object.body, { headers });
});

export function artifactKey(path: string): string | undefined {
  const encoded = path.replace(/^\/api\/artifacts\//, "");
  if (!encoded || encoded.includes("\\")) return undefined;
  let key: string;
  try {
    key = decodeURIComponent(encoded);
  } catch {
    return undefined;
  }
  if (
    !key ||
    key.includes("\\") ||
    key.startsWith("/") ||
    key.endsWith("/") ||
    key.split("/").some((part) => part === "" || part === "." || part === "..")
  ) {
    return undefined;
  }
  return key;
}

app.get("/access/config", async (c) =>
  c.json(
    {
      data: {
        enabled: accessProtectionEnabled(c.env),
        authenticated:
          hasServiceToken(c.req.raw, c.env) ||
          (await verifyAccessCookie(
            parseCookie(c.req.header("Cookie") ?? null, accessCookieName()),
            c.env,
          )),
        site_key: accessSiteKey(c.env),
      },
    },
    200,
    { "Cache-Control": "no-store" },
  ),
);

app.post("/access/turnstile", async (c) => {
  if (!accessProtectionEnabled(c.env)) return c.json({ data: { enabled: false } });
  const ip = c.req.header("CF-Connecting-IP") ?? "unknown";
  const limit = accessRateLimiter.consume(`turnstile:${ip}`, 10, 10 * 60_000);
  if (!limit.allowed) {
    return c.json({ error: "Too many verification attempts", code: "rate_limited" }, 429, {
      "Retry-After": String(limit.retryAfterSeconds),
    });
  }
  let token: string | undefined;
  try {
    const body = await c.req.json<{ token?: unknown }>();
    if (typeof body.token === "string") token = body.token;
  } catch {
    token = undefined;
  }
  if (!token || token.length > 2_048) {
    return c.json({ error: "A Turnstile token is required", code: "invalid_token" }, 400);
  }
  let verified = false;
  try {
    verified = await verifyTurnstileToken(
      token,
      c.env.TURNSTILE_SECRET_KEY!,
      fetch,
      turnstileHostname(c.env, c.req.raw),
    );
  } catch {
    return c.json(
      {
        error: "Turnstile verification unavailable",
        code: "verification_unavailable",
      },
      503,
    );
  }
  if (!verified) {
    return c.json({ error: "Turnstile verification failed", code: "verification_failed" }, 403);
  }
  const cookie = await createAccessCookie(c.env);
  return c.json({ data: { enabled: true, expires_in: cookie.maxAge } }, 200, {
    "Cache-Control": "no-store",
    "Set-Cookie": accessSetCookie(cookie.value, cookie.maxAge, c.env.APP_ENV === "production"),
  });
});

app.get("/systems", async (c) => {
  const query = c.req.query("query")?.trim() ?? "";
  const limit = boundedInteger(c.req.query("limit"), 50, 1, 100);
  const offset = boundedInteger(c.req.query("offset"), 0, 0, Number.MAX_SAFE_INTEGER);
  const pattern = `%${query}%`;
  const result = await c.env.DB.prepare(
    `SELECT id, name, version_context, summary, scope_json, related_systems_json,
            temporal_context_json, relations_json, composition_json, source_path
     FROM systems
     WHERE (?1 = '' OR id LIKE ?2 OR name LIKE ?2 OR summary LIKE ?2)
     ORDER BY name, id
     LIMIT ?3 OFFSET ?4`,
  )
    .bind(query, pattern, limit, offset)
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

  const [features, views, tradeOffs, evidence, featureRelations] = await Promise.all([
    c.env.DB.prepare(
      `SELECT id, name, category, claim_type, description, benefits_json, costs_json,
                metadata_json
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
      `SELECT id, model, question, assumptions_json, claim_type, metadata_json,
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
        metadata_json: string;
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
    c.env.DB.prepare(featureRelationQuery("source_system_id = ?1"))
      .bind(system.id)
      .all<FeatureRelationRow>(),
  ]);

  return c.json({
    data: {
      ...serializeSystem(system),
      features: features.results.map(serializeFeature),
      mathematical_views: views.results.map((view) => ({
        id: view.id,
        key: modelViewKey(system.id, view.model, view.question),
        model: view.model,
        question: view.question,
        assumptions: parseJson<string[]>(view.assumptions_json, []),
        claim_type: view.claim_type,
        metadata: parseJson<Record<string, unknown>>(view.metadata_json, {}),
        evidence_ids: parseJsonArray<string>(view.evidence_ids_json),
      })),
      trade_offs: tradeOffs.results.map((tradeOff) => ({
        id: tradeOff.id,
        feature_id: tradeOff.feature_id,
        benefits: parseJson<string[]>(tradeOff.benefits_json, []),
        costs: parseJson<string[]>(tradeOff.costs_json, []),
      })),
      evidence: evidence.results,
      feature_relations: featureRelations.results.map(serializeFeatureRelation),
    },
  });
});

app.get("/feature-relations", async (c) => {
  const filters: string[] = [];
  const bindings: unknown[] = [];
  for (const [name, column] of [
    ["system_id", "source_system_id"],
    ["feature_id", "source_feature_id"],
    ["target_system_id", "target_system_id"],
    ["type", "type"],
  ] as const) {
    const value = c.req.query(name)?.trim();
    if (value) {
      bindings.push(value);
      filters.push(`${column} = ?${bindings.length}`);
    }
  }
  const limit = boundedInteger(c.req.query("limit"), 100, 1, 200);
  bindings.push(limit);
  const where = filters.length ? filters.join(" AND ") : "1 = 1";
  const result = await c.env.DB.prepare(featureRelationQuery(where, `LIMIT ?${bindings.length}`))
    .bind(...bindings)
    .all<FeatureRelationRow>();

  return c.json({
    data: result.results.map((relation) => ({
      source_system_id: relation.source_system_id,
      ...serializeFeatureRelation(relation),
    })),
  });
});

app.get("/features", async (c) => {
  const query = c.req.query("query")?.trim() ?? "";
  const category = c.req.query("category")?.trim() ?? "";
  const claimType = c.req.query("claim_type")?.trim() ?? "";
  const limit = boundedInteger(c.req.query("limit"), 100, 1, 200);
  const result = await c.env.DB.prepare(
    `SELECT f.id, f.system_id, s.name AS system_name, f.name, f.category,
            f.claim_type, f.description, f.benefits_json, f.costs_json, f.metadata_json,
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
  const bundle = parseJson<Record<string, unknown> | null>(row.bundle_json, null);
  if (!bundle) return c.json({ error: "Stored modeling bundle is invalid" }, 500);
  return c.json({ data: bundle });
});

app.get("/graph", async (c) => {
  const systems = await c.env.DB.prepare(
    "SELECT id, name, related_systems_json, relations_json FROM systems ORDER BY name",
  ).all<GraphSystem>();

  return c.json(buildGraph(systems.results));
});

app.get("/graph/layers", async (c) => {
  const origin = c.req.query("origin")?.trim() || undefined;
  const [systems, documents] = await Promise.all([
    c.env.DB.prepare(
      `SELECT s.id, s.name, s.scope_json, s.relations_json, s.composition_json,
       COALESCE((SELECT json_group_array(json_object(
         'id', f.id, 'name', f.name, 'category', f.category,
         'claim_type', f.claim_type, 'description', f.description,
         'evidence_ids', COALESCE((SELECT json_group_array(
           substr(fe.evidence_id, length(fe.system_id) + 2)
         ) FROM feature_evidence fe WHERE fe.system_id = f.system_id
           AND fe.feature_id = f.id ORDER BY fe.evidence_id), '[]'),
         'metadata_json', f.metadata_json
       )) FROM features f WHERE f.system_id = s.id ORDER BY f.id), '[]') AS features_json,
       COALESCE((SELECT json_group_array(json_object(
         'id', v.id, 'model', v.model, 'question', v.question,
         'assumptions', v.assumptions_json, 'claim_type', v.claim_type,
         'evidence_ids', COALESCE((SELECT json_group_array(
           substr(mve.evidence_id, length(v.system_id) + 2)
         ) FROM mathematical_view_evidence mve WHERE mve.view_id = v.id
           ORDER BY mve.evidence_id), '[]'),
         'metadata_json', v.metadata_json
       )) FROM mathematical_views v WHERE v.system_id = s.id ORDER BY v.id), '[]') AS views_json
       FROM systems s ORDER BY s.id`,
    ).all<GraphLayerSystemRow>(),
    c.env.DB.prepare(
      "SELECT id, kind, name, document_json FROM graph_documents ORDER BY kind, id",
    ).all<GraphDocumentRow>(),
  ]);
  const documentsFor = (kind: GraphDocumentRow["kind"]) =>
    documents.results
      .filter((row) => row.kind === kind)
      .flatMap((row) => {
        const document = parseJson<Record<string, unknown> | null>(row.document_json, null);
        return document ? [{ id: row.id, name: row.name, document }] : [];
      });
  return c.json({
    data: buildLayeredGraphProjection(
      {
        systems: systems.results.map(toProjectionSystem),
        microstructures: documentsFor("microstructure") as ProjectionMicrostructure[],
        analogies: documentsFor("analogy") as ProjectionAnalogy[],
      },
      origin,
    ),
  });
});

app.get("/graph/models", async (c) => {
  const views = await c.env.DB.prepare(
    `SELECT systems.id AS system_id, systems.name AS system_name,
            mathematical_views.id AS view_id, mathematical_views.model,
            mathematical_views.question, mathematical_views.assumptions_json,
            mathematical_views.claim_type,
            mathematical_views.metadata_json,
            COALESCE((
              SELECT json_group_array(
                substr(mve.evidence_id, length(mathematical_views.system_id) + 2)
              )
              FROM mathematical_view_evidence mve
              WHERE mve.view_id = mathematical_views.id
              ORDER BY mve.evidence_id
            ), '[]') AS evidence_ids_json
     FROM mathematical_views
     JOIN systems ON systems.id = mathematical_views.system_id
     ORDER BY systems.name, systems.id, mathematical_views.id`,
  ).all<ModelViewRow>();

  return c.json({ data: buildModelGraph(views.results) });
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
      const composition = parseJson<Record<string, unknown> | null>(system.composition_json, null);
      if (!isCompositionRecord(composition)) return [];
      if (inputSystem && !composition.inputs.some((input) => input.system_id === inputSystem)) {
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

function typedRelationEdges(system: GraphSystem, knownSystemIds: Set<string>): GraphEdge[] {
  const relations = parseJsonArray<Record<string, unknown>>(system.relations_json).filter(isRecord);
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

function legacyRelationEdges(system: GraphSystem, knownSystemIds: Set<string>): GraphEdge[] {
  return parseJsonArray<string>(system.related_systems_json).flatMap((target) => {
    const normalizedTarget = stringValue(target);
    return normalizedTarget && knownSystemIds.has(normalizedTarget)
      ? [{ source: system.id, target: normalizedTarget, type: "related" }]
      : [];
  });
}

function serializeSystem(system: SystemRow) {
  return {
    id: system.id,
    name: system.name,
    version_context: system.version_context,
    summary: system.summary,
    scope: parseJson<string[]>(system.scope_json, []),
    related_systems: parseJson<string[]>(system.related_systems_json, []),
    temporal_context: parseJson<Record<string, unknown> | null>(system.temporal_context_json, null),
    relations: parseJson<Array<Record<string, unknown>>>(system.relations_json, []),
    composition: parseJson<Record<string, unknown> | null>(system.composition_json, null),
    source_path: system.source_path,
  };
}

export function serializeFeature(feature: FeatureRow) {
  const metadata = parseJson<Record<string, unknown>>(feature.metadata_json ?? null, {});
  return {
    id: feature.id,
    name: feature.name,
    category: feature.category,
    claim_type: feature.claim_type,
    description: feature.description,
    benefits: parseJson<string[]>(feature.benefits_json, []),
    costs: parseJson<string[]>(feature.costs_json, []),
    evidence_ids: parseJsonArray<string>(feature.evidence_ids_json),
    ...(Object.keys(metadata).length ? { metadata } : {}),
  };
}

export function serializeFeatureRelation(relation: FeatureRelationRow) {
  return {
    source_feature_id: relation.source_feature_id,
    target_system_id: relation.target_system_id,
    target_feature_id: relation.target_feature_id,
    type: relation.type,
    claim_type: relation.claim_type,
    claim_status: relation.claim_status,
    evidence_ids: parseJsonArray<string>(relation.evidence_ids_json),
    ...(relation.notes === null ? {} : { notes: relation.notes }),
  };
}

function featureRelationQuery(where: string, limit = "") {
  return `SELECT fr.id, fr.source_system_id, fr.source_feature_id,
                 fr.target_system_id, fr.target_feature_id, fr.type,
                 fr.claim_type, fr.claim_status, fr.notes,
                 COALESCE((
                   SELECT json_group_array(substr(fre.evidence_id, length(fr.source_system_id) + 2))
                   FROM feature_relation_evidence fre
                   JOIN evidence e
                     ON e.id = fre.evidence_id
                    AND e.system_id = fr.source_system_id
                   WHERE fre.relation_id = fr.id
                   ORDER BY fre.evidence_id
                 ), '[]') AS evidence_ids_json
          FROM feature_relations fr
          WHERE ${where}
            AND NOT EXISTS (
              SELECT 1
              FROM feature_relation_evidence fre
              LEFT JOIN evidence e ON e.id = fre.evidence_id
              WHERE fre.relation_id = fr.id
                AND (e.id IS NULL OR e.system_id <> fr.source_system_id)
            )
          ORDER BY fr.source_system_id, fr.source_feature_id,
                   fr.target_system_id, fr.target_feature_id, fr.type
          ${limit}`;
}

export function serializeMathematicalView(view: {
  id: number;
  model: string;
  question: string;
  assumptions_json: string;
  claim_type: string;
  metadata_json?: string;
  evidence_ids_json: string;
}) {
  const metadata = parseJson<Record<string, unknown>>(view.metadata_json ?? null, {});
  return {
    id: view.id,
    model: view.model,
    question: view.question,
    assumptions: parseJson<string[]>(view.assumptions_json, []),
    claim_type: view.claim_type,
    evidence_ids: parseJsonArray<string>(view.evidence_ids_json),
    ...(Object.keys(metadata).length ? { metadata } : {}),
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

function toProjectionSystem(row: GraphLayerSystemRow): ProjectionSystem {
  return {
    id: row.id,
    name: row.name,
    scope: parseJson<string[]>(row.scope_json, []),
    relations: parseJsonArray<Record<string, unknown>>(row.relations_json).flatMap((relation) => {
      if (!isRecord(relation)) return [];
      const target = stringValue(relation.target);
      const type = stringValue(relation.type);
      if (!target || !type) return [];
      return [
        {
          target,
          type,
          claim_type: stringValue(relation.claim_type),
          claim_status: stringValue(relation.claim_status),
          ...(Array.isArray(relation.evidence_ids)
            ? { evidence_ids: parseStringArray(relation.evidence_ids) }
            : {}),
          notes: stringValue(relation.notes),
          metadata: relationMetadata(relation),
        },
      ];
    }),
    features: parseJsonArray<Record<string, unknown>>(row.features_json).flatMap((feature) => {
      if (!isRecord(feature) || typeof feature.id !== "string" || typeof feature.name !== "string")
        return [];
      const metadata = parseJson<Record<string, unknown>>(
        typeof feature.metadata_json === "string" ? feature.metadata_json : null,
        {},
      );
      return [
        {
          id: feature.id,
          name: feature.name,
          category: stringValue(feature.category) ?? "unclassified",
          claim_type: stringValue(feature.claim_type) ?? "inference",
          claim_status: stringValue(metadata.claim_status),
          description: stringValue(feature.description) ?? "",
          evidence_ids: parseStringArray(feature.evidence_ids),
          metadata,
        },
      ];
    }),
    mathematical_views: parseJsonArray<Record<string, unknown>>(row.views_json).flatMap((view) => {
      if (!isRecord(view) || (typeof view.id !== "string" && typeof view.id !== "number"))
        return [];
      const metadata = parseJson<Record<string, unknown>>(
        typeof view.metadata_json === "string" ? view.metadata_json : null,
        {},
      );
      return [
        {
          id:
            (typeof metadata.id === "string" || typeof metadata.id === "number"
              ? metadata.id
              : undefined) ??
            stableProjectionViewId(row.id, {
              model: stringValue(view.model) ?? "",
              question: stringValue(view.question) ?? "",
              metadata,
            }),
          model: stringValue(view.model) ?? "Unclassified model",
          question: stringValue(view.question) ?? "",
          assumptions: parseStringArray(view.assumptions),
          claim_type: stringValue(view.claim_type) ?? "inference",
          claim_status: stringValue(metadata.claim_status),
          evidence_ids: parseStringArray(view.evidence_ids),
          metadata,
        },
      ];
    }),
    composition: parseJson<Record<string, unknown> | null>(row.composition_json, null),
  };
}

function relationMetadata(value: Record<string, unknown>) {
  return {
    ...(isRecord(value.validity_scope) ? { validity_scope: value.validity_scope } : {}),
    ...(isRecord(value.provenance) ? { provenance: value.provenance } : {}),
    ...(isRecord(value.discovery) ? { discovery: value.discovery } : {}),
  };
}

function parseStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string");
  return typeof value === "string"
    ? parseJson<string[]>(value, []).filter((item): item is string => typeof item === "string")
    : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCompositionRecord(value: Record<string, unknown> | null): value is Record<
  string,
  unknown
> & {
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
    !value.evidence_ids.every((item) => typeof item === "string" && item.length > 0)
  ) {
    return false;
  }
  return value.inputs.every((input) => isRecord(input) && Boolean(stringValue(input.system_id)));
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

function boundedInteger(value: string | undefined, fallback: number, min: number, max: number) {
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
