CREATE TRIGGER IF NOT EXISTS feature_relation_evidence_source_system_insert
BEFORE INSERT ON feature_relation_evidence
FOR EACH ROW
WHEN NOT EXISTS (
  SELECT 1
  FROM feature_relations fr
  JOIN evidence e ON e.id = NEW.evidence_id
  WHERE fr.id = NEW.relation_id
    AND e.system_id = fr.source_system_id
)
BEGIN
  SELECT RAISE(ABORT, 'feature relation evidence must belong to relation source system');
END;

CREATE TRIGGER IF NOT EXISTS feature_relation_evidence_source_system_update
BEFORE UPDATE OF relation_id, evidence_id ON feature_relation_evidence
FOR EACH ROW
WHEN NOT EXISTS (
  SELECT 1
  FROM feature_relations fr
  JOIN evidence e ON e.id = NEW.evidence_id
  WHERE fr.id = NEW.relation_id
    AND e.system_id = fr.source_system_id
)
BEGIN
  SELECT RAISE(ABORT, 'feature relation evidence must belong to relation source system');
END;

CREATE TRIGGER IF NOT EXISTS feature_relation_source_system_update
BEFORE UPDATE OF source_system_id ON feature_relations
FOR EACH ROW
WHEN EXISTS (
  SELECT 1
  FROM feature_relation_evidence fre
  LEFT JOIN evidence e ON e.id = fre.evidence_id
  WHERE fre.relation_id = OLD.id
    AND (e.id IS NULL OR e.system_id <> NEW.source_system_id)
)
BEGIN
  SELECT RAISE(ABORT, 'feature relation evidence must belong to relation source system');
END;

CREATE TRIGGER IF NOT EXISTS evidence_source_system_update
BEFORE UPDATE OF system_id ON evidence
FOR EACH ROW
WHEN EXISTS (
  SELECT 1
  FROM feature_relation_evidence fre
  JOIN feature_relations fr ON fr.id = fre.relation_id
  WHERE fre.evidence_id = OLD.id
    AND fr.source_system_id <> NEW.system_id
)
BEGIN
  SELECT RAISE(ABORT, 'feature relation evidence must belong to relation source system');
END;
