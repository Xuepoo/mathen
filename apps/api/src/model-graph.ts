export type ModelViewRow = {
  system_id: string;
  system_name: string;
  view_id: string | number;
  model: string;
  question: string;
  assumptions_json: string;
  claim_type: string;
  evidence_ids_json: string;
};

export type ModelViewMetadata = {
  id: string | number;
  model: string;
  question: string;
  assumptions: string[];
  claim_type: string;
  evidence_ids: string[];
};

export type ModelGraphNode = {
  id: string;
  name: string;
  type: "system" | "model";
};

export type ModelGraphEdge = {
  source: string;
  target: string;
  type: "modeled-by";
  claim_type: "inference";
  metadata: ModelViewMetadata[];
};

export type ModelGraph = {
  nodes: ModelGraphNode[];
  edges: ModelGraphEdge[];
};

type ModelFamily = {
  slug: string;
  name: string;
  matches: RegExp[];
};

const MODEL_FAMILIES: ModelFamily[] = [
  {
    slug: "simulation-refinement",
    name: "Simulation and refinement",
    matches: [
      /\bbisimulation\b/i,
      /\bsimulation\b/i,
      /\brefinement\b/i,
      /\btrace semantics?\b/i,
      /\bobservational equivalence\b/i,
    ],
  },
  {
    slug: "lattices-convergence",
    name: "Lattices and convergence",
    matches: [
      /\bcomplete lattice\b/i,
      /\bsemilattice\b/i,
      /\blattice\b/i,
      /\bjoin[- ]semilattice\b/i,
      /\bmeet[- ]semilattice\b/i,
      /\bfixed[- ]point\b/i,
      /\bconvergence\b/i,
      /\bmonotone\b/i,
      /\bcrdt\b/i,
    ],
  },
  {
    slug: "algebra-relational-algebra",
    name: "Algebra and relational algebra",
    matches: [
      /\brelational algebra\b/i,
      /\bquery algebra\b/i,
      /\bcommutative algebra\b/i,
      /\boperator algebra\b/i,
      /\b(?:group|ring|monoid|semigroup)\b/i,
      /\balgebra(?:ic)?\b/i,
    ],
  },
  {
    slug: "queueing-cost-resource",
    name: "Queueing, cost, and resource models",
    matches: [
      /\bqueue(?:ing|ing theory)?\b/i,
      /\bqueueing network\b/i,
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
    name: "State and transition systems",
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
    name: "Graphs and partial orders",
    matches: [
      /\b(?:dependency|labeled|labelled|process|dataflow|event|state|control[- ]flow) graph\b/i,
      /\bgraph(?: traversal| partition| coloring| colouring| cut| homomorphism)\b/i,
      /\b(?:directed acyclic graph|dag)\b/i,
      /\bpartial order\b/i,
      /\bposet\b/i,
      /\brooted tree\b/i,
      /\bsyntax tree\b/i,
      /\btopological sort\b/i,
    ],
  },
  {
    slug: "types-grammars",
    name: "Types and grammars",
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
    name: "Dataflow and pipelines",
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
    name: "Probabilistic and stochastic models",
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
    name: "Optimization and scheduling",
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

    const family = classifyModel(row.model);
    const key = family ? `family:${family.slug}` : `model:${row.model}`;
    const group = rawGroups.get(key) ?? {
      name: family?.name ?? row.model,
      views: [],
    };
    group.views.push({ system_id: row.system_id, metadata: toMetadata(row) });
    rawGroups.set(key, group);
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
        claim_type: "inference",
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
  };
}

function toMetadata(row: ModelViewRow): ModelViewMetadata {
  return {
    id: row.view_id,
    model: row.model,
    question: row.question,
    assumptions: stringArray(row.assumptions_json),
    claim_type: row.claim_type,
    evidence_ids: stringArray(row.evidence_ids_json),
  };
}

function classifyModel(model: string): ModelFamily | null {
  return (
    MODEL_FAMILIES.find((family) => family.matches.some((pattern) => pattern.test(model))) ?? null
  );
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
        node: { id, name: group.name, type: "model" },
        views: sortViews(group.views),
      });
    }
  }

  for (const [key, group] of unknowns) {
    const id = uniqueModelId(group.name, usedIds);
    usedIds.add(id);
    result.set(key, {
      node: { id, name: group.name, type: "model" },
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
    compareViewIds(left.id, right.id) ||
    left.model.localeCompare(right.model) ||
    left.question.localeCompare(right.question)
  );
}

function compareViewIds(left: string | number, right: string | number): number {
  if (typeof left === "number" && typeof right === "number") return left - right;
  if (typeof left === "number") return -1;
  if (typeof right === "number") return 1;
  return left.localeCompare(right);
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

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function viewIdValue(value: unknown): string | number {
  return typeof value === "string" || typeof value === "number" ? value : "unknown";
}
