import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

type Card = {
  id: string;
  name: string;
  version_context?: string;
  temporal_context?: Record<string, unknown>;
  scope_context?: Record<string, unknown>;
  relations?: Array<Record<string, unknown>>;
  feature_relations?: FeatureRelation[];
  composition?: Record<string, unknown>;
  summary: string;
  scope: string[];
  related_systems?: string[];
  features: Array<{
    id: string;
    name: string;
    category: string;
    claim_type: string;
    claim_status?: string;
    lifecycle?: Record<string, unknown>;
    validity_scope?: Record<string, unknown>;
    scope_context?: Record<string, unknown>;
    description: string;
    benefits?: string[];
    costs?: string[];
    evidence_ids: string[];
  }>;
  mathematical_views: Array<{
    id?: string | number;
    model: string;
    question: string;
    assumptions: string[];
    claim_type: string;
    claim_status?: string;
    lifecycle?: Record<string, unknown>;
    validity_scope?: Record<string, unknown>;
    scope_context?: Record<string, unknown>;
    contract?: Record<string, unknown>;
    evidence_ids: string[];
  }>;
  trade_offs: Array<{
    feature_id: string;
    benefits: string[];
    costs: string[];
  }>;
  evidence: Array<{
    id: string;
    kind: string;
    title: string;
    uri: string;
    accessed?: string;
    notes?: string;
    scope_context?: Record<string, unknown>;
  }>;
};

type FeatureRelation = {
  source_feature_id: string;
  target_system_id: string;
  target_feature_id: string;
  type: string;
  claim_type: string;
  claim_status: string;
  evidence_ids: string[];
  notes?: string;
};

const featureRelationTypes = new Set([
  "implements",
  "refines",
  "requires",
  "supports",
  "conflicts-with",
  "composes",
  "resembles",
]);
const claimTypes = new Set(["fact", "inference", "hypothesis", "analogy"]);
const claimStatuses = new Set(["proposed", "under-review", "accepted", "rejected", "deprecated"]);

const root = resolve(import.meta.dir, "../../../data/systems");
const modelingRoot = resolve(import.meta.dir, "../../../data/modeling");
const analogyRoot = resolve(import.meta.dir, "../../../data/analogies");
const microstructureRoot = resolve(import.meta.dir, "../../../data/microstructures");
const output = resolve(import.meta.dir, "../.wrangler/generated-seed.sql");
const mode = process.argv.includes("--remote") ? "--remote" : "--local";
const cards = await loadCards();
const modelingBundles = await loadModelingBundles();
await validateGraphDocuments();
const graphDocuments = [
  ...(await loadGraphDocuments(analogyRoot, "analogy")),
  ...(await loadGraphDocuments(microstructureRoot, "microstructure")),
];

await mkdir(resolve(import.meta.dir, "../.wrangler"), { recursive: true });

const statements = [
  "PRAGMA foreign_keys = ON;",
  "DELETE FROM feature_relation_evidence;",
  "DELETE FROM feature_relations;",
  "DELETE FROM mathematical_view_evidence;",
  "DELETE FROM trade_offs;",
  "DELETE FROM mathematical_views;",
  "DELETE FROM feature_evidence;",
  "DELETE FROM features;",
  "DELETE FROM evidence;",
  "DELETE FROM systems;",
  "DELETE FROM modeling_bundles;",
  "DELETE FROM graph_documents;",
  ...cards.flatMap(toStatements),
  ...cards.flatMap(toFeatureRelationStatements),
  ...modelingBundles.map(toModelingBundleStatement),
  ...graphDocuments.map(toGraphDocumentStatement),
];

await writeFile(output, `${statements.join("\n")}\n`, "utf8");
const childProcess = Bun.spawn(["wrangler", "d1", "execute", "mathen-db", mode, "--file", output], {
  cwd: resolve(import.meta.dir, ".."),
  stdout: "inherit",
  stderr: "inherit",
});
const exitCode = await childProcess.exited;
if (exitCode !== 0) {
  throw new Error(`Wrangler seed command failed with exit code ${exitCode}`);
}

async function loadCards() {
  const files = (await readdir(root)).filter((file) => file.endsWith(".json")).sort();
  return Promise.all(
    files.map(async (file) => JSON.parse(await readFile(resolve(root, file), "utf8")) as Card),
  );
}

async function loadModelingBundles() {
  const files = (await readdir(modelingRoot)).filter((file) => file.endsWith(".json")).sort();
  return Promise.all(
    files.map(async (file) => {
      const bundle = JSON.parse(await readFile(resolve(modelingRoot, file), "utf8")) as {
        system?: { id?: string; commit?: string; provenance?: string };
      };
      if (!bundle.system?.id || !bundle.system.commit || !bundle.system.provenance) {
        throw new Error(`Invalid modeling bundle: ${file}`);
      }
      return {
        id: bundle.system.id,
        commit_sha: bundle.system.commit,
        provenance: bundle.system.provenance,
        bundle_json: JSON.stringify(bundle),
        source_path: `data/modeling/${file}`,
      };
    }),
  );
}

async function loadGraphDocuments(directory: string, kind: "microstructure" | "analogy") {
  let files: string[];
  try {
    files = (await readdir(directory)).filter((file) => file.endsWith(".json")).sort();
  } catch (error) {
    if (isMissingDirectory(error)) return [];
    throw error;
  }
  return Promise.all(
    files.map(async (file) => {
      const document = JSON.parse(await readFile(resolve(directory, file), "utf8")) as {
        id?: unknown;
        name?: unknown;
      };
      if (typeof document.id !== "string" || typeof document.name !== "string") {
        throw new Error(`Invalid ${kind} document: ${file}`);
      }
      return {
        id: document.id,
        kind,
        name: document.name,
        document_json: JSON.stringify(document),
        source_path: `data/${kind === "analogy" ? "analogies" : "microstructures"}/${file}`,
      };
    }),
  );
}

async function validateGraphDocuments() {
  await Promise.all([
    runValidator("validate-microstructures", microstructureRoot),
    runValidator("validate-analogies", analogyRoot),
  ]);
}

async function runValidator(command: string, path: string) {
  const childProcess = Bun.spawn(["uv", "run", "mathen", command, path], {
    cwd: resolve(import.meta.dir, "../../.."),
    stdout: "inherit",
    stderr: "inherit",
  });
  const exitCode = await childProcess.exited;
  if (exitCode !== 0) {
    throw new Error(`Document validation failed: ${command} ${path}`);
  }
}

function toStatements(card: Card) {
  const statements = [
    insert("systems", {
      id: card.id,
      name: card.name,
      version_context: card.version_context ?? null,
      temporal_context_json: card.temporal_context ? JSON.stringify(card.temporal_context) : null,
      scope_context_json: card.scope_context ? JSON.stringify(card.scope_context) : null,
      relations_json: card.relations ? JSON.stringify(card.relations) : null,
      composition_json: card.composition ? JSON.stringify(card.composition) : null,
      summary: card.summary,
      scope_json: JSON.stringify(card.scope),
      related_systems_json: JSON.stringify(card.related_systems ?? []),
      source_path: `data/systems/${card.id}.json`,
    }),
    ...card.evidence.map(({ scope_context, ...item }) =>
      insert("evidence", {
        system_id: card.id,
        ...item,
        id: evidenceKey(card.id, item.id),
        accessed: item.accessed ?? null,
        notes: item.notes ?? null,
        scope_context_json: scope_context ? JSON.stringify(scope_context) : null,
      }),
    ),
    ...card.features.map((feature) =>
      insert("features", {
        system_id: card.id,
        id: feature.id,
        name: feature.name,
        category: feature.category,
        claim_type: feature.claim_type,
        description: feature.description,
        benefits_json: JSON.stringify(feature.benefits ?? []),
        costs_json: JSON.stringify(feature.costs ?? []),
        metadata_json: JSON.stringify(featureMetadata(feature)),
      }),
    ),
    ...card.features.flatMap((feature) =>
      feature.evidence_ids.map((evidence_id) =>
        insert("feature_evidence", {
          system_id: card.id,
          feature_id: feature.id,
          evidence_id: evidenceKey(card.id, evidence_id),
        }),
      ),
    ),
    ...card.mathematical_views.flatMap((view) => [
      insert("mathematical_views", {
        system_id: card.id,
        model: view.model,
        question: view.question,
        assumptions_json: JSON.stringify(view.assumptions),
        claim_type: view.claim_type,
        metadata_json: JSON.stringify(viewMetadata(card.id, view)),
      }),
      ...view.evidence_ids.map(
        (evidence_id) =>
          "INSERT INTO mathematical_view_evidence (view_id, evidence_id) " +
          `SELECT id, ${quote(evidenceKey(card.id, evidence_id))} FROM mathematical_views ` +
          `WHERE system_id = ${quote(card.id)} AND id = (` +
          `SELECT MAX(id) FROM mathematical_views WHERE system_id = ${quote(card.id)}` +
          `);`,
      ),
    ]),
    ...card.trade_offs.map((tradeOff) =>
      insert("trade_offs", {
        system_id: card.id,
        feature_id: tradeOff.feature_id,
        benefits_json: JSON.stringify(tradeOff.benefits),
        costs_json: JSON.stringify(tradeOff.costs),
      }),
    ),
  ];

  return statements;
}

function toModelingBundleStatement(bundle: {
  id: string;
  commit_sha: string;
  provenance: string;
  bundle_json: string;
  source_path: string;
}) {
  return insert("modeling_bundles", bundle);
}

function toGraphDocumentStatement(document: {
  id: string;
  kind: "microstructure" | "analogy";
  name: string;
  document_json: string;
  source_path: string;
}) {
  return insert("graph_documents", document);
}

function featureMetadata(feature: Card["features"][number]) {
  return {
    ...(feature.claim_status ? { claim_status: feature.claim_status } : {}),
    ...(feature.lifecycle ? { lifecycle: feature.lifecycle } : {}),
    ...(feature.validity_scope ? { validity_scope: feature.validity_scope } : {}),
    ...(feature.scope_context ? { scope_context: feature.scope_context } : {}),
  };
}

function viewMetadata(systemId: string, view: Card["mathematical_views"][number]) {
  return {
    id: view.id ?? stableViewId(systemId, view.model, view.question),
    ...(view.claim_status ? { claim_status: view.claim_status } : {}),
    ...(view.lifecycle ? { lifecycle: view.lifecycle } : {}),
    ...(view.validity_scope ? { validity_scope: view.validity_scope } : {}),
    ...(view.scope_context ? { scope_context: view.scope_context } : {}),
    ...(view.contract ? { contract: view.contract } : {}),
  };
}

function stableViewId(systemId: string, model: string, question: string) {
  return `view:${encodeURIComponent(
    JSON.stringify([
      systemId.trim(),
      model.normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase(),
      question.normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase(),
    ]),
  )}`;
}

function toFeatureRelationStatements(card: Card) {
  return (card.feature_relations ?? []).flatMap((relation) => {
    validateFeatureRelation(card, relation);
    const relationValues = {
      source_system_id: card.id,
      source_feature_id: relation.source_feature_id,
      target_system_id: relation.target_system_id,
      target_feature_id: relation.target_feature_id,
      type: relation.type,
      claim_type: relation.claim_type,
      claim_status: relation.claim_status,
      notes: relation.notes ?? null,
    };
    const relationLookup =
      `SELECT id FROM feature_relations WHERE source_system_id = ${quote(card.id)}` +
      ` AND source_feature_id = ${quote(relation.source_feature_id)}` +
      ` AND target_system_id = ${quote(relation.target_system_id)}` +
      ` AND target_feature_id = ${quote(relation.target_feature_id)}` +
      ` AND type = ${quote(relation.type)}`;
    return [
      insert("feature_relations", relationValues),
      ...relation.evidence_ids.map(
        (evidenceId) =>
          "INSERT INTO feature_relation_evidence (relation_id, evidence_id) " +
          `VALUES ((${relationLookup}), ${quote(evidenceKey(card.id, evidenceId))});`,
      ),
    ];
  });
}

function validateFeatureRelation(card: Card, relation: FeatureRelation) {
  const sourceFeatureIds = new Set(card.features.map((feature) => feature.id));
  if (!sourceFeatureIds.has(relation.source_feature_id)) {
    throw new Error(
      `Invalid feature relation in ${card.id}: unknown source feature ${relation.source_feature_id}`,
    );
  }
  for (const [field, value] of [
    ["target_system_id", relation.target_system_id],
    ["target_feature_id", relation.target_feature_id],
  ] as const) {
    if (!value) throw new Error(`Invalid feature relation in ${card.id}: ${field} is required`);
  }
  if (!featureRelationTypes.has(relation.type)) {
    throw new Error(`Invalid feature relation in ${card.id}: type is invalid`);
  }
  if (!claimTypes.has(relation.claim_type)) {
    throw new Error(`Invalid feature relation in ${card.id}: claim_type is invalid`);
  }
  if (!claimStatuses.has(relation.claim_status)) {
    throw new Error(`Invalid feature relation in ${card.id}: claim_status is invalid`);
  }
  if (!Array.isArray(relation.evidence_ids) || relation.evidence_ids.length === 0) {
    throw new Error(`Invalid feature relation in ${card.id}: evidence_ids is required`);
  }
  const evidenceIds = new Set(card.evidence.map((evidence) => evidence.id));
  for (const evidenceId of relation.evidence_ids) {
    if (!evidenceIds.has(evidenceId)) {
      throw new Error(`Invalid feature relation in ${card.id}: unknown evidence ${evidenceId}`);
    }
  }
  if (relation.notes !== undefined && typeof relation.notes !== "string") {
    throw new Error(`Invalid feature relation in ${card.id}: notes must be a string`);
  }
}

function evidenceKey(systemId: string, evidenceId: string) {
  return `${systemId}:${evidenceId}`;
}

function insert(table: string, values: Record<string, unknown>) {
  const columns = Object.keys(values);
  const encoded = columns.map((column) => `${quoteIdentifier(column)}`).join(", ");
  const data = columns.map((column) => quote(values[column])).join(", ");
  return `INSERT INTO ${quoteIdentifier(table)} (${encoded}) VALUES (${data});`;
}

function quoteIdentifier(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

function quote(value: unknown) {
  if (value === null) return "NULL";
  if (typeof value === "number") return String(value);
  return `'${String(value).replaceAll("'", "''")}'`;
}

function isMissingDirectory(error: unknown): boolean {
  return isRecord(error) && error.code === "ENOENT";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
