import assert from "node:assert/strict";
import { test } from "node:test";
import { Database, type SQLQueryBindings } from "bun:sqlite";
import { app } from "./index.js";

test("GET /api/feature-relations omits wrong-system evidence", async () => {
  const db = new Database(":memory:");
  db.exec(`
    CREATE TABLE evidence (id TEXT PRIMARY KEY, system_id TEXT NOT NULL);
    CREATE TABLE feature_relations (
      id INTEGER PRIMARY KEY,
      source_system_id TEXT NOT NULL,
      source_feature_id TEXT NOT NULL,
      target_system_id TEXT NOT NULL,
      target_feature_id TEXT NOT NULL,
      type TEXT NOT NULL,
      claim_type TEXT NOT NULL,
      claim_status TEXT NOT NULL,
      notes TEXT
    );
    CREATE TABLE feature_relation_evidence (
      relation_id INTEGER NOT NULL,
      evidence_id TEXT NOT NULL
    );
    INSERT INTO evidence VALUES ('alpha:architecture', 'alpha');
    INSERT INTO evidence VALUES ('beta:architecture', 'beta');
    INSERT INTO feature_relations VALUES
      (1, 'alpha', 'source', 'beta', 'target', 'resembles', 'analogy', 'proposed', NULL),
      (2, 'alpha', 'source', 'beta', 'target', 'supports', 'inference', 'proposed', NULL);
    INSERT INTO feature_relation_evidence VALUES (1, 'alpha:architecture');
    INSERT INTO feature_relation_evidence VALUES (2, 'beta:architecture');
  `);

  const response = await app.request(
    "/api/feature-relations?system_id=alpha",
    {},
    { DB: sqliteD1(db), APP_ENV: "test", ASSETS: {} as Fetcher },
  );

  assert.equal(response.status, 200);
  const body = (await response.json()) as {
    data: Array<Record<string, unknown>>;
  };
  assert.deepEqual(body.data, [
    {
      source_system_id: "alpha",
      source_feature_id: "source",
      target_system_id: "beta",
      target_feature_id: "target",
      type: "resembles",
      claim_type: "analogy",
      claim_status: "proposed",
      evidence_ids: ["architecture"],
    },
  ]);
  db.close();
});

function sqliteD1(database: Database) {
  return {
    prepare(sql: string) {
      return {
        bind(...bindings: unknown[]) {
          const statement = database.query(sql);
          return {
            all<T>() {
              return Promise.resolve({
                results: statement.all(
                  ...(bindings as SQLQueryBindings[]),
                ) as T[],
              });
            },
          };
        },
      };
    },
  } as unknown as D1Database;
}
