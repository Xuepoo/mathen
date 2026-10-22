import { Hono } from "hono";

type Bindings = {
  DB: D1Database;
  APP_ENV: string;
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
};

type EvidenceRow = {
  id: string;
  kind: string;
  title: string;
  uri: string;
  accessed: string | null;
  notes: string | null;
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
       FROM features WHERE system_id = ?1 ORDER BY category, name`,
    )
      .bind(system.id)
      .all<FeatureRow>(),
    c.env.DB.prepare(
      `SELECT id, model, question, assumptions_json, claim_type
       FROM mathematical_views WHERE system_id = ?1 ORDER BY id`,
    )
      .bind(system.id)
      .all<{
        id: number;
        model: string;
        question: string;
        assumptions_json: string;
        claim_type: string;
      }>(),
    c.env.DB.prepare(
      `SELECT id, feature_id, benefits_json, costs_json
       FROM trade_offs WHERE system_id = ?1 ORDER BY id`,
    )
      .bind(system.id)
      .all<{ id: number; feature_id: string; benefits_json: string; costs_json: string }>(),
    c.env.DB.prepare(
      `SELECT id, kind, title, uri, accessed, notes
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
            f.claim_type, f.description, f.benefits_json, f.costs_json
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
  const systems = await c.env.DB.prepare("SELECT id, name FROM systems ORDER BY name").all<{
    id: string;
    name: string;
  }>();
  const relations = await c.env.DB.prepare("SELECT id, related_systems_json FROM systems").all<{
    id: string;
    related_systems_json: string;
  }>();
  const edges = relations.results.flatMap((row) =>
    parseJson<string[]>(row.related_systems_json, [])
      .filter((target) => systems.results.some((system) => system.id === target))
      .map((target) => ({ source: row.id, target, type: "related" })),
  );

  return c.json({
    nodes: systems.results.map((system) => ({ ...system, type: "system" })),
    edges,
  });
});

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

function serializeFeature(feature: FeatureRow) {
  return {
    id: feature.id,
    name: feature.name,
    category: feature.category,
    claim_type: feature.claim_type,
    description: feature.description,
    benefits: parseJson<string[]>(feature.benefits_json, []),
    costs: parseJson<string[]>(feature.costs_json, []),
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

function boundedInteger(value: string | undefined, fallback: number, min: number, max: number) {
  const parsed = Number.parseInt(value ?? "", 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(Math.max(parsed, min), max);
}

export default app;
