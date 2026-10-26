/**
 * A deterministic, read-only projection of the reviewed knowledge layers.
 *
 * The projection is intentionally not a semantic closure.  It emits only
 * relations represented by a source document: a feature belongs to its card,
 * a view belongs to its card, explicit card relations connect cards, and typed
 * composition edges are copied from the typed contract. Navigation categories
 * and layout are not graph layers.
 */

export type ProjectionLayer =
  | "system"
  | "property"
  | "microstructure"
  | "mathematical-contract"
  | "composition"
  | "component"
  | "property-effect"
  | "relation"
  | "analogy";

export type ProjectionMetadata = {
  claim_type?: string;
  claim_status?: string;
  evidence_ids?: string[];
  validity_scope?: Record<string, unknown>;
  proven?: false;
  discovery?: Record<string, unknown>;
  origin?: string;
  [key: string]: unknown;
};

export type ProjectionNode = {
  id: string;
  layer: ProjectionLayer;
  kind: string;
  label: string;
  metadata: ProjectionMetadata;
};

export type ProjectionEdge = {
  source: string;
  target: string;
  type: string;
  claim_type?: string;
  claim_status?: string;
  evidence_ids?: string[];
  notes?: string;
  metadata?: ProjectionMetadata;
};

export type LayeredGraphProjection = {
  schema_version: "1.0";
  origin?: string;
  nodes: ProjectionNode[];
  edges: ProjectionEdge[];
};

export type ProjectionSystem = {
  id: string;
  name: string;
  scope: string[];
  claim_type?: string;
  claim_status?: string;
  validity_scope?: Record<string, unknown>;
  evidence_ids?: string[];
  features: ProjectionFeature[];
  mathematical_views: ProjectionView[];
  relations?: ProjectionRelation[];
  composition?: Record<string, unknown> | null;
};

export type ProjectionFeature = {
  id: string;
  name: string;
  category: string;
  claim_type: string;
  claim_status?: string;
  description: string;
  evidence_ids: string[];
  metadata?: ProjectionMetadata;
};

export type ProjectionView = {
  id: string | number;
  model: string;
  question: string;
  assumptions: string[];
  claim_type: string;
  claim_status?: string;
  evidence_ids: string[];
  metadata?: ProjectionMetadata;
};

export type ProjectionRelation = {
  target: string;
  type: string;
  claim_type?: string;
  claim_status?: string;
  evidence_ids?: string[];
  notes?: string;
  metadata?: ProjectionMetadata;
};

export type ProjectionMicrostructure = {
  id: string;
  name: string;
  document: Record<string, unknown>;
};

export type ProjectionAnalogy = {
  id: string;
  name: string;
  document: Record<string, unknown>;
};

export type ProjectionInput = {
  systems: ProjectionSystem[];
  microstructures?: ProjectionMicrostructure[];
  analogies?: ProjectionAnalogy[];
};

export function buildLayeredGraphProjection(
  input: ProjectionInput,
  origin?: string,
): LayeredGraphProjection {
  let nodes: ProjectionNode[] = [];
  const edges: ProjectionEdge[] = [];
  const addNode = (node: ProjectionNode) => {
    if (matchesOrigin(node.metadata, origin)) nodes.push(node);
  };
  const addEdge = (edge: ProjectionEdge) => {
    if (matchesOrigin(edge.metadata ?? {}, origin)) edges.push(edge);
  };

  for (const system of [...input.systems].sort(compareSystems)) {
    addNode({
      id: `system:${system.id}`,
      layer: "system",
      kind: "architecture-card",
      label: system.name,
      metadata: claimMetadata(system),
    });
    for (const feature of [...system.features].sort(compareFeatures)) {
      const propertyId = `property:${system.id}:${feature.id}`;
      addNode({
        id: propertyId,
        layer: "property",
        kind: "system-property",
        label: feature.name,
        metadata: {
          ...feature.metadata,
          claim_type: feature.claim_type,
          ...(feature.claim_status ? { claim_status: feature.claim_status } : {}),
          evidence_ids: feature.evidence_ids,
          category: feature.category,
          description: feature.description,
        },
      });
      addEdge({
        source: `system:${system.id}`,
        target: propertyId,
        type: "has-property",
        claim_type: feature.claim_type,
        ...(feature.claim_status ? { claim_status: feature.claim_status } : {}),
        evidence_ids: feature.evidence_ids,
        metadata: feature.metadata,
      });
    }
    for (const view of [...system.mathematical_views].sort(compareViews)) {
      const stableViewId = stableProjectionViewId(system.id, view);
      const contractId = `math:${system.id}:${stableViewId}`;
      addNode({
        id: contractId,
        layer: "mathematical-contract",
        kind: "mathematical-view",
        label: view.model,
        metadata: {
          ...view.metadata,
          claim_type: view.claim_type,
          ...(view.claim_status ? { claim_status: view.claim_status } : {}),
          evidence_ids: view.evidence_ids,
          question: view.question,
          assumptions: view.assumptions,
          ...(view.metadata?.contract !== undefined ? { contract: view.metadata.contract } : {}),
        },
      });
      addEdge({
        source: `system:${system.id}`,
        target: contractId,
        type: "has-mathematical-contract",
        claim_type: view.claim_type,
        ...(view.claim_status ? { claim_status: view.claim_status } : {}),
        evidence_ids: view.evidence_ids,
        metadata: view.metadata,
      });
    }
    for (const relation of [...(system.relations ?? [])].sort(compareRelations)) {
      const target = stringValue(relation.target);
      const type = stringValue(relation.type);
      if (!target || !type) continue;
      const metadata = relation.metadata ?? {};
      addEdge({
        source: `system:${system.id}`,
        target: `system:${target}`,
        type,
        ...(relation.claim_type ? { claim_type: relation.claim_type } : {}),
        ...(relation.claim_status ? { claim_status: relation.claim_status } : {}),
        ...(relation.evidence_ids ? { evidence_ids: relation.evidence_ids } : {}),
        ...(relation.notes ? { notes: relation.notes } : {}),
        metadata,
      });
    }
    projectComposition(system, addNode, addEdge);
  }

  for (const microstructure of [...(input.microstructures ?? [])].sort(compareDocuments)) {
    const document = microstructure.document;
    const metadata = documentMetadata(document);
    addNode({
      id: `microstructure:${microstructure.id}`,
      layer: "microstructure",
      kind: "architecture-microstructure",
      label: microstructure.name,
      metadata: {
        ...metadata,
        scale: document.scale,
        role: document.role,
        summary: document.summary,
        payload: document,
      },
    });
  }

  for (const analogy of [...(input.analogies ?? [])].sort(compareDocuments)) {
    const metadata = documentMetadata(analogy.document);
    addNode({
      id: `analogy:${analogy.id}`,
      layer: "analogy",
      kind: "cross-domain-analogy",
      label: analogy.name,
      metadata: {
        ...metadata,
        source_domain: analogy.document.source_domain,
        target_domain: analogy.document.target_domain,
        payload: analogy.document,
      },
    });
  }

  // A scoped composition is one unit: never retain descendants when its root
  // was filtered out by the requested deployment origin.
  const visibleCompositionRoots = new Set(
    nodes.filter((node) => node.layer === "composition").map((node) => node.id),
  );
  nodes = nodes.filter(
    (node) =>
      !node.id.startsWith("composition:") ||
      visibleCompositionRoots.has(node.id.split(":", 2).join(":")),
  );

  // A dangling explicit edge is never emitted.  This keeps filters and future
  // source bugs from creating an invented relation to an unknown system.
  const nodeIds = new Set(nodes.map((node) => node.id));
  const filteredEdges = edges.filter(
    (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target),
  );
  nodes.sort(compareNodes);
  filteredEdges.sort(compareEdges);
  return {
    schema_version: "1.0",
    ...(origin ? { origin } : {}),
    nodes,
    edges: filteredEdges,
  };
}

function projectComposition(
  system: ProjectionSystem,
  addNode: (node: ProjectionNode) => void,
  addEdge: (edge: ProjectionEdge) => void,
) {
  const composition = system.composition;
  const typed = isRecord(composition?.typed_semantics) ? composition.typed_semantics : undefined;
  if (!typed || typed.proven !== false) return;
  const compositionId = `composition:${system.id}`;
  const compositionMetadata = documentMetadata(typed);
  const compositionScope = compositionValidityScope(typed);
  addNode({
    id: compositionId,
    layer: "composition",
    kind: "typed-composition",
    label: `Typed composition for ${system.name}`,
    metadata: {
      ...compositionMetadata,
      proven: false,
      ...(isRecord(typed.discovery) ? { discovery: typed.discovery } : {}),
      ...(isRecord(typed.validity_scope) ? { validity_scope: typed.validity_scope } : {}),
      ...(typed.uncertainties !== undefined ? { uncertainties: typed.uncertainties } : {}),
      ...(typed.disagreements !== undefined ? { disagreements: typed.disagreements } : {}),
    },
  });
  addEdge({
    source: `system:${system.id}`,
    target: compositionId,
    type: "has-composition-contract",
    claim_type: stringValue(typed.claim_type),
    claim_status: stringValue(typed.claim_status),
    evidence_ids: stringArray(typed.evidence_ids),
    metadata: {
      ...compositionMetadata,
      proven: false,
      ...(isRecord(typed.discovery) ? { discovery: typed.discovery } : {}),
      ...(isRecord(typed.validity_scope) ? { validity_scope: typed.validity_scope } : {}),
      ...(typed.uncertainties !== undefined ? { uncertainties: typed.uncertainties } : {}),
      ...(typed.disagreements !== undefined ? { disagreements: typed.disagreements } : {}),
    },
  });

  const componentIds = new Set<string>();
  for (const component of records(typed.components)) {
    const id = stringValue(component.id);
    if (!id || componentIds.has(id)) continue;
    componentIds.add(id);
    addNode({
      id: `${compositionId}:component:${id}`,
      layer: "component",
      kind: "composition-component",
      label: stringValue(component.role) || id,
      metadata: {
        ...inheritedCompositionMetadata(component, compositionMetadata, compositionScope),
        component_id: id,
        role: component.role,
      },
    });
    addEdge({
      source: compositionId,
      target: `${compositionId}:component:${id}`,
      type: "has-component",
      claim_type: stringValue(component.claim_type),
      claim_status: stringValue(component.claim_status),
      evidence_ids: stringArray(component.evidence_ids),
      metadata: inheritedCompositionMetadata(component, compositionMetadata, compositionScope),
    });
  }
  for (const adapter of records(typed.adapters)) {
    addTypedRelation(
      addNode,
      addEdge,
      compositionId,
      componentIds,
      adapter,
      "adapter",
      compositionMetadata,
      compositionScope,
    );
  }
  for (const boundary of records(typed.boundaries)) {
    addTypedRelation(
      addNode,
      addEdge,
      compositionId,
      componentIds,
      boundary,
      "boundary",
      compositionMetadata,
      compositionScope,
    );
  }
  for (const effect of records(typed.property_effects)) {
    const id = stringValue(effect.id);
    if (!id) continue;
    const effectId = `${compositionId}:property-effect:${id}`;
    addNode({
      id: effectId,
      layer: "property-effect",
      kind: "typed-property-effect",
      label: stringValue(effect.property) || id,
      metadata: {
        ...inheritedCompositionMetadata(effect, compositionMetadata, compositionScope),
        relation: effect.relation,
      },
    });
    addEdge({
      source: compositionId,
      target: effectId,
      type: "declares-property-effect",
      claim_type: stringValue(effect.claim_type),
      claim_status: stringValue(effect.claim_status),
      evidence_ids: stringArray(effect.evidence_ids),
      metadata: inheritedCompositionMetadata(effect, compositionMetadata, compositionScope),
    });
  }
}

function addTypedRelation(
  addNode: (node: ProjectionNode) => void,
  addEdge: (edge: ProjectionEdge) => void,
  compositionId: string,
  componentIds: Set<string>,
  relation: Record<string, unknown>,
  type: "adapter" | "boundary",
  compositionMetadata: ProjectionMetadata,
  compositionScope: Record<string, unknown> | undefined,
) {
  const source = stringValue(relation.source) || stringValue(relation.inside);
  const target = stringValue(relation.target) || stringValue(relation.outside);
  if (!source || !target || !componentIds.has(source) || !componentIds.has(target)) return;
  const relationId = `${compositionId}:relation:${type}:${stringValue(relation.id) ?? `${source}-${target}`}`;
  const metadata = inheritedCompositionMetadata(relation, compositionMetadata, compositionScope);
  addNode({
    id: relationId,
    layer: "relation",
    kind: "typed-relation",
    label: stringValue(relation.description) || type,
    metadata: { ...metadata, relation_type: type },
  });
  addEdge({
    source: compositionId,
    target: relationId,
    type: "has-typed-relation",
    claim_type: stringValue(relation.claim_type),
    claim_status: stringValue(relation.claim_status),
    evidence_ids: stringArray(relation.evidence_ids),
    metadata,
  });
  addEdge({
    source: `${compositionId}:component:${source}`,
    target: `${compositionId}:component:${target}`,
    type,
    claim_type: stringValue(relation.claim_type),
    claim_status: stringValue(relation.claim_status),
    evidence_ids: stringArray(relation.evidence_ids),
    notes: stringValue(relation.description),
    metadata,
  });
}

function inheritedCompositionMetadata(
  value: Record<string, unknown>,
  compositionMetadata: ProjectionMetadata,
  compositionScope: Record<string, unknown> | undefined,
): ProjectionMetadata {
  return {
    ...compositionMetadata,
    ...documentMetadata(value),
    ...(compositionScope ? { validity_scope: compositionScope } : {}),
  };
}

function compositionValidityScope(
  value: Record<string, unknown>,
): Record<string, unknown> | undefined {
  return isRecord(value.validity_scope) ? value.validity_scope : undefined;
}

function claimMetadata(value: Record<string, unknown>): ProjectionMetadata {
  const claimType = stringValue(value.claim_type);
  const claimStatus = stringValue(value.claim_status);
  return {
    ...(claimType ? { claim_type: claimType } : {}),
    ...(claimStatus ? { claim_status: claimStatus } : {}),
    evidence_ids: stringArray(value.evidence_ids),
    ...(value.scope !== undefined ? { scope: value.scope } : {}),
    ...(value.provenance !== undefined ? { provenance: value.provenance } : {}),
  };
}

function documentMetadata(value: Record<string, unknown>): ProjectionMetadata {
  const claimType = stringValue(value.claim_type);
  const claimStatus = stringValue(value.claim_status);
  const scope = isRecord(value.validity_scope)
    ? value.validity_scope
    : isRecord(value.scope)
      ? value.scope
      : undefined;
  return {
    ...(claimType ? { claim_type: claimType } : {}),
    ...(claimStatus ? { claim_status: claimStatus } : {}),
    evidence_ids: stringArray(value.evidence_ids),
    ...(scope ? { validity_scope: scope } : {}),
    ...(value.proven === false ? { proven: false } : {}),
    ...(isRecord(value.discovery) ? { discovery: value.discovery } : {}),
    ...(isRecord(value.provenance) ? { provenance: value.provenance } : {}),
    ...(value.uncertainties ? { uncertainties: value.uncertainties } : {}),
    ...(value.uncertainty ? { uncertainty: value.uncertainty } : {}),
    ...(value.disagreements ? { disagreements: value.disagreements } : {}),
    ...(value.counterexamples ? { counterexamples: value.counterexamples } : {}),
    ...(value.non_equivalence ? { non_equivalence: value.non_equivalence } : {}),
  };
}

export function stableProjectionViewId(
  systemId: string,
  view: Pick<ProjectionView, "model" | "question" | "metadata"> & {
    id?: string | number;
  },
): string {
  const explicit = view.metadata?.id;
  if (typeof explicit === "string" || typeof explicit === "number") {
    return String(explicit);
  }
  if (typeof view.id === "string" || typeof view.id === "number") {
    return String(view.id);
  }
  return `view:${encodeURIComponent(
    JSON.stringify([
      systemId.trim(),
      view.model.normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase(),
      view.question.normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase(),
    ]),
  )}`;
}

function matchesOrigin(metadata: ProjectionMetadata, origin?: string): boolean {
  if (!origin) return true;
  const scope = metadata.validity_scope;
  const origins = isRecord(scope) ? stringArray(scope.deployment_origins) : [];
  return origins.length === 0 || origins.includes(origin);
}

function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];
}
function compareSystems(left: ProjectionSystem, right: ProjectionSystem) {
  return left.id.localeCompare(right.id);
}
function compareFeatures(left: ProjectionFeature, right: ProjectionFeature) {
  return left.id.localeCompare(right.id);
}
function compareViews(left: ProjectionView, right: ProjectionView) {
  return String(left.id).localeCompare(String(right.id));
}
function compareRelations(left: ProjectionRelation, right: ProjectionRelation) {
  return left.target.localeCompare(right.target) || left.type.localeCompare(right.type);
}
function compareDocuments(left: { id: string }, right: { id: string }) {
  return left.id.localeCompare(right.id);
}
function compareNodes(left: ProjectionNode, right: ProjectionNode) {
  return left.id.localeCompare(right.id);
}
function compareEdges(left: ProjectionEdge, right: ProjectionEdge) {
  return (
    left.source.localeCompare(right.source) ||
    left.target.localeCompare(right.target) ||
    left.type.localeCompare(right.type)
  );
}
