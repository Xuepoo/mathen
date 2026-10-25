export type ModelViewRow = {
  system_id: string;
  system_name: string;
  view_id: string | number;
  model: string;
  question: string;
  assumptions_json: string;
  claim_type: string;
  evidence_ids_json: string;
  metadata_json?: string;
};

export type ModelViewMetadata = {
  id: string | number;
  /** Stable card-local navigation identity; id remains the database row id for compatibility. */
  key: string;
  model: string;
  question: string;
  assumptions: string[];
  claim_type: string;
  evidence_ids: string[];
  claim_status?: string;
  validity_scope?: Record<string, unknown>;
  contract?: Record<string, unknown>;
};

export type ModelGraphNode = {
  id: string;
  name: string;
  type: "system" | "model";
  description?: string;
};

export type ModelGraphEdge = {
  source: string;
  target: string;
  type: "modeled-by";
  claim_type: string;
  metadata: ModelViewMetadata[];
};

export type ModelGraph = {
  nodes: ModelGraphNode[];
  edges: ModelGraphEdge[];
};

type ModelFamily = {
  slug: string;
  name: string;
  description: string;
  matches: RegExp[];
};

const MODEL_FAMILIES: ModelFamily[] = [
  {
    slug: "simulation-refinement",
    name: "Navigation family: simulation/refinement wording",
    description:
      "Navigation by simulation or refinement wording; membership does not establish formal equivalence.",
    matches: [
      /\bbisimulation\b/i,
      /\bsimulation\b/i,
      /\brefinement\b/i,
      /\btrace semantics?\b/i,
      /\bobservational equivalence\b/i,
    ],
  },
  {
    slug: "lattices-orders",
    name: "Navigation family: lattice/order wording",
    description:
      "Navigation by lattice or order wording; membership does not establish formal equivalence.",
    matches: [
      /\bcomplete lattice\b/i,
      /\bsemilattice\b/i,
      /\blattice\b/i,
      /\bjoin[- ]semilattice\b/i,
      /\bmeet[- ]semilattice\b/i,
      /\bpartial order\b/i,
      /\bposet\b/i,
    ],
  },
  {
    slug: "fixed-points-convergence",
    name: "Navigation family: fixed-point/convergence wording",
    description:
      "Navigation by fixed-point or convergence wording; membership does not establish formal equivalence.",
    matches: [/\bfixed[- ]point\b/i, /\bconverg(?:ence|ent)\b/i, /\bmonotone\b/i, /\bcrdt\b/i],
  },
  {
    slug: "algebra-relational-algebra",
    name: "Navigation family: algebra wording",
    description: "Navigation by algebra wording; membership does not establish formal equivalence.",
    matches: [
      /\brelational algebra\b/i,
      /\bquery algebra\b/i,
      /\bcommutative algebra\b/i,
      /\boperator algebra\b/i,
      /\b(?:group|ring|monoid|semigroup) algebra\b/i,
      /\balgebra(?:ic)? (?:model|structure|semantics)\b/i,
    ],
  },
  {
    slug: "queueing-theory",
    name: "Navigation family: queueing-theory wording",
    description:
      "Navigation by explicit queueing-theory wording; membership does not establish formal equivalence.",
    matches: [/\bqueueing (?:theory|model|network)\b/i, /\bm\/m\/\d+\b/i],
  },
  {
    slug: "cost-resource",
    name: "Navigation family: cost/resource wording",
    description:
      "Navigation by cost or resource wording; membership does not establish formal equivalence.",
    matches: [
      /\bcost model\b/i,
      /\bresource model\b/i,
      /\bresource allocation\b/i,
      /\bcapacity model\b/i,
      /\bworkload model\b/i,
      /\bthroughput model\b/i,
      /\blatency model\b/i,
    ],
  },
  {
    slug: "state-transition-systems",
    name: "Navigation family: state/transition wording",
    description:
      "Navigation by state or transition wording; membership does not establish formal equivalence.",
    matches: [
      /\bstate machine\b/i,
      /\bstate transition\b/i,
      /\btransition system\b/i,
      /\btransition model\b/i,
      /\bautomaton\b/i,
      /\bautomata\b/i,
      /\blifecycle state\b/i,
      /\bevent transition\b/i,
      /\boperational semantics\b/i,
    ],
  },
  {
    slug: "graphs-partial-orders",
    name: "Navigation family: graph wording",
    description: "Navigation by graph wording; membership does not establish formal equivalence.",
    matches: [
      /\b(?:dependency|labeled|labelled|process|dataflow|event|state|control[- ]flow) graph\b/i,
      /\bgraph(?: traversal| partition| coloring| colouring| cut| homomorphism)\b/i,
      /\b(?:directed acyclic graph|dag)\b/i,
      /\brooted tree\b/i,
      /\bsyntax tree\b/i,
      /\btopological sort\b/i,
    ],
  },
  {
    slug: "types-grammars",
    name: "Navigation family: types/grammar wording",
    description:
      "Navigation by type or grammar wording; membership does not establish formal equivalence.",
    matches: [
      /\btype system\b/i,
      /\btype checker\b/i,
      /\btyping judgment\b/i,
      /\btyped? intermediate representation\b/i,
      /\b(?:context[- ]free|formal|attribute) grammar\b/i,
      /\bgrammar model\b/i,
      /\bparser (?:grammar|automaton)\b/i,
    ],
  },
  {
    slug: "dataflow-pipelines",
    name: "Navigation family: dataflow/pipeline wording",
    description:
      "Navigation by dataflow or pipeline wording; membership does not establish formal equivalence.",
    matches: [
      /\bdataflow\b/i,
      /\bdata flow\b/i,
      /\bpipeline(?: model| algebra)?\b/i,
      /\bstream processing\b/i,
      /\bstream transformation\b/i,
      /\boperator pipeline\b/i,
    ],
  },
  {
    slug: "probabilistic-stochastic",
    name: "Navigation family: probabilistic/stochastic wording",
    description:
      "Navigation by probabilistic or stochastic wording; membership does not establish formal equivalence.",
    matches: [
      /\bprobabilistic\b/i,
      /\bprobability model\b/i,
      /\bstochastic\b/i,
      /\bmarkov\b/i,
      /\brandom process\b/i,
    ],
  },
  {
    slug: "optimization-scheduling",
    name: "Navigation family: optimization/scheduling wording",
    description:
      "Navigation by optimization or scheduling wording; membership does not establish formal equivalence.",
    matches: [
      /\boptimization\b/i,
      /\boptimisation\b/i,
      /\blinear program(?:ming)?\b/i,
      /\binteger program(?:ming)?\b/i,
      /\bscheduling model\b/i,
      /\bconstraint optimization\b/i,
    ],
  },
];

type ModelGroup = {
  node: ModelGraphNode;
  views: Array<{ system_id: string; metadata: ModelViewMetadata }>;
};

type RawModelGroup = {
  name: string;
  description: string;
  views: Array<{ system_id: string; metadata: ModelViewMetadata }>;
};

/**
 * Build a navigational bipartite graph from reviewed, author-labelled views.
 * Family assignment is deliberately bounded to terms in MODEL_FAMILIES.
 */
export function buildModelGraph(rows: ModelViewRow[]): ModelGraph {
  const validRows = Array.isArray(rows)
    ? rows.flatMap((row) => {
        const normalized = normalizeRow(row);
        return normalized ? [normalized] : [];
      })
    : [];
  const systemById = new Map<string, ModelGraphNode>();
  const rawGroups = new Map<string, RawModelGroup>();

  for (const row of validRows) {
    const viewKey = modelViewKey(row.system_id, row.model, row.question);
    if (!systemById.has(row.system_id)) {
      systemById.set(row.system_id, {
        id: row.system_id,
        name: row.system_name,
        type: "system",
      });
    } else {
      const system = systemById.get(row.system_id);
      if (system && row.system_name.localeCompare(system.name) < 0) {
        system.name = row.system_name;
      }
    }

    const families = classifyModel(row.model);
    for (const family of families) {
      addRawGroup(
        rawGroups,
        `family:${family.slug}`,
        family.name,
        family.description,
        row,
        viewKey,
      );
    }
    if (families.length === 0) {
      addRawGroup(
        rawGroups,
        `model:${row.model}`,
        `Same title: ${row.model}`,
        "Same title is a navigation grouping and does not establish formal equivalence.",
        row,
        viewKey,
      );
    }
  }

  const modelGroups = makeModelGroups(rawGroups);
  const nodes = [
    ...[...systemById.values()].sort(compareNodes),
    ...[...modelGroups.values()].map((group) => group.node).sort(compareNodes),
  ];
  const edges: ModelGraphEdge[] = [];

  for (const system of [...systemById.values()].sort(compareNodes)) {
    for (const group of modelGroups.values()) {
      const views = group.views.filter((view) => view.system_id === system.id);
      if (views.length === 0) continue;
      edges.push({
        source: system.id,
        target: group.node.id,
        type: "modeled-by",
        claim_type: aggregateClaimType(views.map((view) => view.metadata)),
        metadata: views.map((view) => view.metadata),
      });
    }
  }

  edges.sort(
    (left, right) =>
      left.source.localeCompare(right.source) || left.target.localeCompare(right.target),
  );
  return { nodes, edges };
}

function normalizeRow(row: ModelViewRow): ModelViewRow | null {
  if (!row || typeof row !== "object") return null;
  const systemId = stringValue(row.system_id);
  if (!systemId) return null;
  const model = stringValue(row.model) || "Unclassified model";
  return {
    system_id: systemId,
    system_name: stringValue(row.system_name) || systemId,
    view_id: viewIdValue(row.view_id),
    model,
    question: stringValue(row.question),
    assumptions_json: stringValue(row.assumptions_json),
    claim_type: stringValue(row.claim_type),
    evidence_ids_json: stringValue(row.evidence_ids_json),
    metadata_json: stringValue(row.metadata_json),
  };
}

/**
 * Lossless tuple encoding avoids hash, slug, and delimiter collisions.
 * Repeated rows with the same normalized identity intentionally share a key;
 * their database ids and individual claims remain available in metadata.
 */
export function modelViewKey(systemId: string, model: string, question: string): string {
  return `view:${encodeURIComponent(
    JSON.stringify([
      systemId.trim(),
      normalizeIdentityPart(model),
      normalizeIdentityPart(question),
    ]),
  )}`;
}

function normalizeIdentityPart(value: string): string {
  return value.normalize("NFKC").trim().replace(/\s+/g, " ").toLowerCase();
}

function addRawGroup(
  groups: Map<string, RawModelGroup>,
  key: string,
  name: string,
  description: string,
  row: ModelViewRow,
  viewKey: string,
): void {
  const group = groups.get(key) ?? { name, description, views: [] };
  group.views.push({
    system_id: row.system_id,
    metadata: toMetadata(row, viewKey),
  });
  groups.set(key, group);
}

function toMetadata(row: ModelViewRow, key: string): ModelViewMetadata {
  const metadata = parseRecord(row.metadata_json);
  return {
    id: row.view_id,
    key,
    model: row.model,
    question: row.question,
    assumptions: stringArray(row.assumptions_json),
    claim_type: row.claim_type,
    evidence_ids: stringArray(row.evidence_ids_json),
    ...(typeof metadata.claim_status === "string" ? { claim_status: metadata.claim_status } : {}),
    ...(isRecord(metadata.validity_scope) ? { validity_scope: metadata.validity_scope } : {}),
    ...(isRecord(metadata.contract) ? { contract: metadata.contract } : {}),
  };
}

function classifyModel(model: string): ModelFamily[] {
  return MODEL_FAMILIES.filter((family) => family.matches.some((pattern) => pattern.test(model)));
}

function makeModelGroups(rawGroups: Map<string, RawModelGroup>): Map<string, ModelGroup> {
  const unknowns = [...rawGroups.entries()]
    .filter(([key]) => key.startsWith("model:"))
    .sort((left, right) => left[1].name.localeCompare(right[1].name));
  const usedIds = new Set<string>();
  const result = new Map<string, ModelGroup>();

  for (const [key, group] of rawGroups) {
    if (key.startsWith("family:")) {
      const family = MODEL_FAMILIES.find((candidate) => `family:${candidate.slug}` === key);
      if (!family) continue;
      const id = `model:${family.slug}`;
      usedIds.add(id);
      result.set(key, {
        node: {
          id,
          name: group.name,
          description: group.description,
          type: "model",
        },
        views: sortViews(group.views),
      });
    }
  }

  for (const [key, group] of unknowns) {
    const id = uniqueModelId(key.slice("model:".length), usedIds);
    usedIds.add(id);
    result.set(key, {
      node: {
        id,
        name: group.name,
        description: group.description,
        type: "model",
      },
      views: sortViews(group.views),
    });
  }
  return result;
}

function sortViews(
  views: Array<{ system_id: string; metadata: ModelViewMetadata }>,
): Array<{ system_id: string; metadata: ModelViewMetadata }> {
  return [...views].sort(
    (left, right) =>
      left.system_id.localeCompare(right.system_id) ||
      compareViewMetadata(left.metadata, right.metadata),
  );
}

function compareViewMetadata(left: ModelViewMetadata, right: ModelViewMetadata): number {
  return (
    left.key.localeCompare(right.key) ||
    left.model.localeCompare(right.model) ||
    left.question.localeCompare(right.question)
  );
}

function aggregateClaimType(views: ModelViewMetadata[]): string {
  const claims = new Set(views.map((view) => view.claim_type));
  return claims.size === 1 ? (views[0]?.claim_type ?? "") : "mixed";
}

function uniqueModelId(name: string, usedIds: Set<string>): string {
  const base = `model:${stableSlug(name)}`;
  if (!usedIds.has(base)) return base;
  let candidate = `${base}-${stableHash(name)}`;
  let suffix = 2;
  while (usedIds.has(candidate)) candidate = `${base}-${stableHash(name)}-${suffix++}`;
  return candidate;
}

function compareNodes(left: ModelGraphNode, right: ModelGraphNode): number {
  const typeOrder = left.type === right.type ? 0 : left.type === "system" ? -1 : 1;
  return typeOrder || left.id.localeCompare(right.id);
}

function stableSlug(value: string): string {
  const slug = value
    .normalize("NFKD")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "unclassified";
}

function stableHash(value: string): string {
  let hash = 2166136261;
  for (const character of value) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function stringArray(value: string): string[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    return [];
  }
  return Array.isArray(parsed)
    ? parsed.filter((item): item is string => typeof item === "string")
    : [];
}

function parseRecord(value: unknown): Record<string, unknown> {
  if (typeof value !== "string") return {};
  try {
    const parsed: unknown = JSON.parse(value);
    return isRecord(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function viewIdValue(value: unknown): string | number {
  return typeof value === "string" || typeof value === "number" ? value : "unknown";
}
