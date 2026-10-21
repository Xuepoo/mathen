import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

type Card = {
  id: string;
  name: string;
  version_context?: string;
  summary: string;
  scope: string[];
  related_systems?: string[];
  features: Array<{
    id: string;
    name: string;
    category: string;
    claim_type: string;
    description: string;
    benefits?: string[];
    costs?: string[];
    evidence_ids: string[];
  }>;
  mathematical_views: Array<{
    model: string;
    question: string;
    assumptions: string[];
    claim_type: string;
    evidence_ids: string[];
  }>;
  trade_offs: Array<{ feature_id: string; benefits: string[]; costs: string[] }>;
  evidence: Array<{
    id: string;
    kind: string;
    title: string;
    uri: string;
    accessed?: string;
    notes?: string;
  }>;
};

const root = resolve(import.meta.dir, "../../../data/systems");
const modelingRoot = resolve(import.meta.dir, "../../../data/modeling");
const output = resolve(import.meta.dir, "../.wrangler/generated-seed.sql");
const cards = await loadCards();
const modelingBundles = await loadModelingBundles();

await mkdir(resolve(import.meta.dir, "../.wrangler"), { recursive: true });

const statements = [
  "PRAGMA foreign_keys = ON;",
  "DELETE FROM mathematical_view_evidence;",
  "DELETE FROM trade_offs;",
  "DELETE FROM mathematical_views;",
  "DELETE FROM feature_evidence;",
  "DELETE FROM features;",
  "DELETE FROM evidence;",
  "DELETE FROM systems;",
  "DELETE FROM modeling_bundles;",
  ...cards.flatMap(toStatements),
  ...modelingBundles.map(toModelingBundleStatement),
];

await writeFile(output, `${statements.join("\n")}\n`, "utf8");
const process = Bun.spawn(
  ["wrangler", "d1", "execute", "mathen-db", "--local", "--file", output],
  { cwd: resolve(import.meta.dir, ".."), stdout: "inherit", stderr: "inherit" },
);
const exitCode = await process.exited;
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
  const files = (await readdir(modelingRoot))
    .filter((file) => file.endsWith(".json"))
    .sort();
  return Promise.all(
    files.map(async (file) => {
      const bundle = JSON.parse(
        await readFile(resolve(modelingRoot, file), "utf8"),
      ) as {
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

function toStatements(card: Card) {
  const statements = [
    insert("systems", {
      id: card.id,
      name: card.name,
      version_context: card.version_context ?? null,
      summary: card.summary,
      scope_json: JSON.stringify(card.scope),
      related_systems_json: JSON.stringify(card.related_systems ?? []),
      source_path: `data/systems/${card.id}.json`,
    }),
    ...card.evidence.map((item) =>
      insert("evidence", { system_id: card.id, ...item, accessed: item.accessed ?? null, notes: item.notes ?? null }),
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
      }),
    ),
    ...card.features.flatMap((feature) =>
      feature.evidence_ids.map((evidence_id) =>
        insert("feature_evidence", { system_id: card.id, feature_id: feature.id, evidence_id }),
      ),
    ),
    ...card.mathematical_views.flatMap((view) => [
      insert("mathematical_views", {
        system_id: card.id,
        model: view.model,
        question: view.question,
        assumptions_json: JSON.stringify(view.assumptions),
        claim_type: view.claim_type,
      }),
      ...view.evidence_ids.map(
        (evidence_id) =>
          "INSERT INTO mathematical_view_evidence (view_id, evidence_id) " +
          `SELECT last_insert_rowid(), ${quote(evidence_id)};`,
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
