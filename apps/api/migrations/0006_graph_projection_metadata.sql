ALTER TABLE features ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE mathematical_views ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS graph_documents (
  id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('microstructure', 'analogy')),
  name TEXT NOT NULL,
  document_json TEXT NOT NULL,
  source_path TEXT NOT NULL,
  PRIMARY KEY (kind, id)
);

CREATE INDEX IF NOT EXISTS idx_graph_documents_kind_id
  ON graph_documents(kind, id);
