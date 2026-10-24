import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { test } from "node:test";
import { Database } from "bun:sqlite";

test("feature relation evidence rejects evidence owned by another system", async () => {
  const database = new Database(":memory:");
  for (const migration of [
    "0001_initial.sql",
    "0002_modeling_bundles.sql",
    "0003_temporal_composition_contract.sql",
    "0004_feature_relations.sql",
    "0005_feature_relation_evidence_integrity.sql",
  ]) {
    database.exec(
      await readFile(
        resolve(import.meta.dir, "../migrations", migration),
        "utf8",
      ),
    );
  }

  database.exec(`
    INSERT INTO systems (id, name, summary, scope_json, related_systems_json, source_path)
    VALUES ('alpha', 'Alpha', 'Alpha', '[]', '[]', 'alpha.json'),
           ('beta', 'Beta', 'Beta', '[]', '[]', 'beta.json');
    INSERT INTO evidence (id, system_id, kind, title, uri)
    VALUES ('alpha:architecture', 'alpha', 'official-doc', 'Alpha', 'https://alpha.example'),
           ('beta:architecture', 'beta', 'official-doc', 'Beta', 'https://beta.example');
    INSERT INTO features (system_id, id, name, category, claim_type, description, benefits_json, costs_json)
    VALUES ('alpha', 'source', 'Source', 'execution', 'fact', 'Source', '[]', '[]'),
           ('beta', 'target', 'Target', 'execution', 'fact', 'Target', '[]', '[]');
    INSERT INTO feature_relations
      (source_system_id, source_feature_id, target_system_id, target_feature_id, type, claim_type, claim_status)
    VALUES ('alpha', 'source', 'beta', 'target', 'resembles', 'analogy', 'proposed');
    INSERT INTO feature_relation_evidence (relation_id, evidence_id)
    VALUES (1, 'alpha:architecture');
  `);

  assert.throws(
    () =>
      database
        .query(
          "INSERT INTO feature_relation_evidence (relation_id, evidence_id) VALUES (?, ?)",
        )
        .run(1, "beta:architecture"),
    /feature relation evidence must belong to relation source system/,
  );

  assert.throws(
    () =>
      database
        .query("UPDATE evidence SET system_id = ? WHERE id = ?")
        .run("beta", "alpha:architecture"),
    /feature relation evidence must belong to relation source system/,
  );

  database.close();
});
