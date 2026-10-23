CREATE TABLE IF NOT EXISTS feature_relations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_system_id TEXT NOT NULL,
  source_feature_id TEXT NOT NULL,
  target_system_id TEXT NOT NULL,
  target_feature_id TEXT NOT NULL,
  type TEXT NOT NULL,
  claim_type TEXT NOT NULL,
  claim_status TEXT NOT NULL,
  notes TEXT,
  FOREIGN KEY (source_system_id, source_feature_id)
    REFERENCES features(system_id, id) ON DELETE CASCADE,
  FOREIGN KEY (target_system_id, target_feature_id)
    REFERENCES features(system_id, id) ON DELETE CASCADE,
  UNIQUE (
    source_system_id,
    source_feature_id,
    target_system_id,
    target_feature_id,
    type
  )
);

CREATE TABLE IF NOT EXISTS feature_relation_evidence (
  relation_id INTEGER NOT NULL REFERENCES feature_relations(id) ON DELETE CASCADE,
  evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
  PRIMARY KEY (relation_id, evidence_id)
);

CREATE INDEX IF NOT EXISTS idx_feature_relations_source
  ON feature_relations(source_system_id, source_feature_id);
CREATE INDEX IF NOT EXISTS idx_feature_relations_target
  ON feature_relations(target_system_id, target_feature_id);
CREATE INDEX IF NOT EXISTS idx_feature_relations_type
  ON feature_relations(type);
CREATE INDEX IF NOT EXISTS idx_feature_relation_evidence_evidence
  ON feature_relation_evidence(evidence_id);
