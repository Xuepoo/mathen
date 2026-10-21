CREATE TABLE IF NOT EXISTS systems (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version_context TEXT,
  summary TEXT NOT NULL,
  scope_json TEXT NOT NULL,
  related_systems_json TEXT NOT NULL,
  source_path TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  system_id TEXT NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  uri TEXT NOT NULL,
  accessed TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS features (
  id TEXT NOT NULL,
  system_id TEXT NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  claim_type TEXT NOT NULL,
  description TEXT NOT NULL,
  benefits_json TEXT NOT NULL,
  costs_json TEXT NOT NULL,
  PRIMARY KEY (system_id, id)
);

CREATE TABLE IF NOT EXISTS feature_evidence (
  system_id TEXT NOT NULL,
  feature_id TEXT NOT NULL,
  evidence_id TEXT NOT NULL,
  PRIMARY KEY (system_id, feature_id, evidence_id),
  FOREIGN KEY (system_id, feature_id) REFERENCES features(system_id, id) ON DELETE CASCADE,
  FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mathematical_views (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  system_id TEXT NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
  model TEXT NOT NULL,
  question TEXT NOT NULL,
  assumptions_json TEXT NOT NULL,
  claim_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mathematical_view_evidence (
  view_id INTEGER NOT NULL REFERENCES mathematical_views(id) ON DELETE CASCADE,
  evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
  PRIMARY KEY (view_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS trade_offs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  system_id TEXT NOT NULL,
  feature_id TEXT NOT NULL,
  benefits_json TEXT NOT NULL,
  costs_json TEXT NOT NULL,
  FOREIGN KEY (system_id, feature_id) REFERENCES features(system_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_features_category ON features(category);
CREATE INDEX IF NOT EXISTS idx_features_claim_type ON features(claim_type);
CREATE INDEX IF NOT EXISTS idx_evidence_system ON evidence(system_id);
CREATE INDEX IF NOT EXISTS idx_views_system ON mathematical_views(system_id);
