import { spawn } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildLayeredGraphProjection,
  type LayeredGraphProjection,
  type ProjectionAnalogy,
  type ProjectionEdge,
  type ProjectionLayer,
  type ProjectionMicrostructure,
  type ProjectionSystem,
  stableProjectionViewId,
} from "../../api/src/graph-projection.js";

export type Evidence = {
  id: string;
  kind: string;
  title: string;
  uri: string;
  accessed?: string;
  notes?: string;
};

export type Feature = {
  id: string;
  name: string;
  category: string;
  claim_type: string;
  description: string;
  benefits?: string[];
  costs?: string[];
  evidence_ids: string[];
  claim_status?: string;
  validity_scope?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type FeatureRelation = {
  source_feature_id: string;
  target_system_id: string;
  target_feature_id: string;
  type: string;
  claim_type: string;
  claim_status: string;
  evidence_ids: string[];
  notes?: string;
};

export type FeatureRelationResult = FeatureRelation & {
  source_system_id: string;
};

export type ArchitectureCard = {
  id: string;
  name: string;
  summary: string;
  scope: string[];
  features: Feature[];
  mathematical_views: Array<Record<string, unknown>>;
  trade_offs: Array<Record<string, unknown>>;
  evidence: Evidence[];
  related_systems?: string[];
  version_context?: string;
  temporal_context?: Record<string, unknown>;
  relations?: Array<Record<string, unknown>>;
  feature_relations?: FeatureRelation[];
  composition?: Record<string, unknown>;
};

export type SystemSummary = Pick<
  ArchitectureCard,
  "id" | "name" | "summary" | "version_context"
> & {
  status: "reviewed" | "reviewed-or-draft";
};

export type FeatureSearchResult = {
  system_id: string;
  system_name: string;
  feature: Feature;
};

export type CompositionSearchResult = {
  system_id: string;
  system_name: string;
  version_context: string | null;
  composition: Record<string, unknown>;
  evidence: Evidence[];
};

export interface Backend {
  getLayeredGraph(origin?: string): Promise<LayeredGraphProjection>;
  listSystems(includeDrafts: boolean): Promise<SystemSummary[]>;
  getSystem(
    systemId: string,
    includeDrafts: boolean,
  ): Promise<ArchitectureCard | undefined>;
  searchFeatures(
    query: string,
    category: string | undefined,
    claimType: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<FeatureSearchResult[]>;
  listFeatureRelations(
    systemId: string | undefined,
    featureId: string | undefined,
    targetSystemId: string | undefined,
    type: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<FeatureRelationResult[]>;
  listCompositions(
    inputSystem: string | undefined,
    claimStatus: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<CompositionSearchResult[]>;
  getModelingBundle(systemId: string): Promise<unknown>;
}

export class BackendError extends Error {}

export class UnsupportedBackendError extends BackendError {}

async function readJson<T>(path: string): Promise<T> {
  return JSON.parse(await readFile(path, "utf8")) as T;
}

export class FilesystemBackend implements Backend {
  private readonly repositoryRoot: string;
  private readonly systemsDirectory: string;
  private readonly draftsDirectory: string;
  private readonly bundlesDirectory: string;

  constructor(repositoryRoot: string) {
    this.repositoryRoot = repositoryRoot;
    this.systemsDirectory = resolve(repositoryRoot, "data/systems");
    this.draftsDirectory = resolve(repositoryRoot, "data/drafts");
    this.bundlesDirectory = resolve(repositoryRoot, "data/modeling");
  }

  async getLayeredGraph(origin?: string): Promise<LayeredGraphProjection> {
    await this.validateGraphDocuments();
    const [cards, analogies, microstructures] = await Promise.all([
      this.loadCards(this.systemsDirectory),
      this.loadDocuments(resolve(this.repositoryRoot, "data/analogies")),
      this.loadDocuments(resolve(this.repositoryRoot, "data/microstructures")),
    ]);
    return buildLayeredGraphProjection(
      {
        systems: cards.map(toProjectionSystem),
        analogies: analogies.map(toProjectionAnalogy),
        microstructures: microstructures.map(toProjectionMicrostructure),
      },
      origin,
    );
  }

  private async validateGraphDocuments(): Promise<void> {
    await Promise.all([
      this.runValidator("validate-microstructures", "data/microstructures"),
      this.runValidator("validate-analogies", "data/analogies"),
    ]);
  }

  private runValidator(command: string, path: string): Promise<void> {
    return new Promise((resolvePromise, reject) => {
      const child = spawn(
        "uv",
        ["run", "mathen", command, resolve(this.repositoryRoot, path)],
        {
          cwd: resolve(fileURLToPath(new URL("../../..", import.meta.url))),
          stdio: ["ignore", "ignore", "pipe"],
        },
      );
      let stderr = "";
      child.stderr?.on("data", (chunk: Buffer) => {
        stderr += chunk.toString();
      });
      child.once("error", reject);
      child.once("close", (code) => {
        if (code === 0) return resolvePromise();
        reject(
          new BackendError(
            `Invalid ${path}: ${stderr.trim() || `validator exited with ${code}`}`,
          ),
        );
      });
    });
  }

  async listSystems(includeDrafts: boolean): Promise<SystemSummary[]> {
    const cards = await this.loadAllCards(includeDrafts);
    return cards.map(({ id, name, summary, version_context }) => ({
      id,
      name,
      summary,
      version_context,
      status: includeDrafts ? "reviewed-or-draft" : "reviewed",
    }));
  }

  async getSystem(
    systemId: string,
    includeDrafts: boolean,
  ): Promise<ArchitectureCard | undefined> {
    const cards = await this.loadAllCards(includeDrafts);
    return cards.find((candidate) => candidate.id === systemId);
  }

  async searchFeatures(
    query: string,
    category: string | undefined,
    claimType: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<FeatureSearchResult[]> {
    const normalizedQuery = query.toLowerCase();
    const cards = await this.loadAllCards(includeDrafts);
    const results = cards.flatMap((card) =>
      card.features
        .filter((feature) => {
          const haystack =
            `${feature.name} ${feature.description} ${feature.category}`.toLowerCase();
          return (
            haystack.includes(normalizedQuery) &&
            (!category || feature.category === category) &&
            (!claimType || feature.claim_type === claimType)
          );
        })
        .map((feature) => ({
          system_id: card.id,
          system_name: card.name,
          feature,
        })),
    );
    return results.slice(0, limit);
  }

  async listFeatureRelations(
    systemId: string | undefined,
    featureId: string | undefined,
    targetSystemId: string | undefined,
    type: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<FeatureRelationResult[]> {
    const cards = await this.loadAllCards(includeDrafts);
    return cards
      .flatMap((card) =>
        (card.feature_relations ?? [])
          .filter(
            (relation) =>
              (!systemId || card.id === systemId) &&
              (!featureId || relation.source_feature_id === featureId) &&
              (!targetSystemId ||
                relation.target_system_id === targetSystemId) &&
              (!type || relation.type === type),
          )
          .map((relation) => ({ source_system_id: card.id, ...relation })),
      )
      .sort(
        (left, right) =>
          left.source_system_id.localeCompare(right.source_system_id) ||
          left.source_feature_id.localeCompare(right.source_feature_id) ||
          left.target_system_id.localeCompare(right.target_system_id) ||
          left.target_feature_id.localeCompare(right.target_feature_id) ||
          left.type.localeCompare(right.type),
      )
      .slice(0, limit);
  }

  async getModelingBundle(systemId: string): Promise<unknown> {
    try {
      return await readJson(resolve(this.bundlesDirectory, `${systemId}.json`));
    } catch {
      throw new BackendError(`modeling bundle not found: ${systemId}`);
    }
  }

  async listCompositions(
    inputSystem: string | undefined,
    claimStatus: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<CompositionSearchResult[]> {
    const cards = await this.loadAllCards(includeDrafts);
    return cards
      .flatMap((card) => {
        const composition = card.composition;
        if (!isCompositionRecord(composition)) return [];
        if (
          inputSystem &&
          !composition.inputs.some((input) => input.system_id === inputSystem)
        ) {
          return [];
        }
        if (claimStatus && composition.claim_status !== claimStatus) return [];
        return [toCompositionResult(card, composition)];
      })
      .sort(
        (left, right) =>
          left.system_name.localeCompare(right.system_name) ||
          left.system_id.localeCompare(right.system_id),
      )
      .slice(0, limit);
  }

  private async loadAllCards(
    includeDrafts: boolean,
  ): Promise<ArchitectureCard[]> {
    const reviewed = await this.loadCards(this.systemsDirectory);
    if (!includeDrafts) return reviewed;
    const drafts = await this.loadCards(this.draftsDirectory);
    return [
      ...reviewed,
      ...drafts.filter(
        (draft) => !reviewed.some((card) => card.id === draft.id),
      ),
    ];
  }

  private async loadCards(directory: string): Promise<ArchitectureCard[]> {
    const entries = (await readdir(directory, { withFileTypes: true }))
      .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
      .map((entry) => entry.name);
    return Promise.all(
      entries
        .sort()
        .map((entry) => readJson<ArchitectureCard>(resolve(directory, entry))),
    );
  }

  private async loadDocuments(
    directory: string,
  ): Promise<Array<Record<string, unknown>>> {
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (isRecord(error) && error.code === "ENOENT") return [];
      throw error;
    }
    return Promise.all(
      entries
        .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
        .sort((left, right) => left.name.localeCompare(right.name))
        .map((entry) =>
          readJson<Record<string, unknown>>(resolve(directory, entry.name)),
        ),
    );
  }
}

type Fetcher = (input: string | URL, init?: RequestInit) => Promise<Response>;

type ApiEnvelope<T> = { data: T };

export class ApiBackend implements Backend {
  private readonly baseUrl: URL;
  private readonly fetcher: Fetcher;
  private readonly timeoutMs: number;
  private readonly apiToken: string | undefined;

  constructor(
    baseUrl: string,
    fetcher: Fetcher = fetch,
    timeoutMs = 10_000,
    apiToken?: string,
  ) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
    this.fetcher = fetcher;
    this.timeoutMs = timeoutMs;
    this.apiToken = apiToken?.trim() || undefined;
  }

  async listSystems(includeDrafts: boolean): Promise<SystemSummary[]> {
    this.rejectDrafts(includeDrafts);
    const data = await this.request<unknown[]>("/systems");
    if (!Array.isArray(data))
      throw new BackendError(
        "API response for GET /api/systems has invalid data",
      );
    return data.map((system) => {
      const card = asRecord(system);
      return {
        id: requiredString(card.id, "id", "/api/systems"),
        name: requiredString(card.name, "name", "/api/systems"),
        summary: requiredString(card.summary, "summary", "/api/systems"),
        version_context: optionalString(card.version_context),
        status: "reviewed" as const,
      };
    });
  }

  async getLayeredGraph(origin?: string): Promise<LayeredGraphProjection> {
    const suffix = origin ? `?origin=${encodeURIComponent(origin)}` : "";
    return normalizeLayeredGraph(await this.request(`/graph/layers${suffix}`));
  }

  async getSystem(
    systemId: string,
    includeDrafts: boolean,
  ): Promise<ArchitectureCard | undefined> {
    this.rejectDrafts(includeDrafts);
    try {
      return normalizeCard(
        await this.request<unknown>(`/systems/${encodeURIComponent(systemId)}`),
      );
    } catch (error) {
      if (error instanceof ApiHttpError && error.status === 404)
        return undefined;
      throw error;
    }
  }

  async searchFeatures(
    query: string,
    category: string | undefined,
    claimType: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<FeatureSearchResult[]> {
    this.rejectDrafts(includeDrafts);
    const params = new URLSearchParams({ query, limit: String(limit) });
    if (category) params.set("category", category);
    if (claimType) params.set("claim_type", claimType);
    const data = await this.request<unknown[]>(`/features?${params}`);
    if (!Array.isArray(data))
      throw new BackendError(
        "API response for GET /api/features has invalid data",
      );
    return data.map((result) => {
      const record = asRecord(result);
      return {
        system_id: requiredString(
          record.system_id,
          "system_id",
          "/api/features",
        ),
        system_name: requiredString(
          record.system_name,
          "system_name",
          "/api/features",
        ),
        feature: normalizeFeature(record.feature ?? record),
      };
    });
  }

  async listFeatureRelations(
    systemId: string | undefined,
    featureId: string | undefined,
    targetSystemId: string | undefined,
    type: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<FeatureRelationResult[]> {
    this.rejectDrafts(includeDrafts);
    const params = new URLSearchParams({ limit: String(limit) });
    if (systemId) params.set("system_id", systemId);
    if (featureId) params.set("feature_id", featureId);
    if (targetSystemId) params.set("target_system_id", targetSystemId);
    if (type) params.set("type", type);
    const data = await this.request<unknown[]>(`/feature-relations?${params}`);
    if (!Array.isArray(data)) {
      throw new BackendError(
        "API response for GET /api/feature-relations has invalid data",
      );
    }
    return data.map((relation) => normalizeFeatureRelationResult(relation));
  }

  async getModelingBundle(systemId: string): Promise<unknown> {
    try {
      return await this.request<unknown>(
        `/modeling/${encodeURIComponent(systemId)}`,
      );
    } catch (error) {
      if (error instanceof ApiHttpError && error.status === 404) {
        throw new BackendError(`modeling bundle not found: ${systemId}`);
      }
      throw error;
    }
  }

  async listCompositions(
    inputSystem: string | undefined,
    claimStatus: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<CompositionSearchResult[]> {
    this.rejectDrafts(includeDrafts);
    const params = new URLSearchParams({ limit: String(limit) });
    if (inputSystem) params.set("input_system", inputSystem);
    if (claimStatus) params.set("claim_status", claimStatus);
    const data = await this.request<unknown[]>(`/compositions?${params}`);
    if (!Array.isArray(data))
      throw new BackendError(
        "API response for GET /api/compositions has invalid data",
      );
    return data.map(normalizeCompositionResult);
  }

  private rejectDrafts(includeDrafts: boolean): void {
    if (includeDrafts) {
      throw new UnsupportedBackendError(
        "include_drafts is unavailable when MATHEN_API_URL is configured",
      );
    }
  }

  private async request<T>(path: string): Promise<T> {
    const endpoint = new URL(`/api${path}`, this.baseUrl);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetcher(endpoint, {
        headers: {
          accept: "application/json",
          ...(this.apiToken
            ? { authorization: `Bearer ${this.apiToken}` }
            : {}),
        },
        signal: controller.signal,
      });
      if (!response.ok) throw new ApiHttpError(response.status, path);
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        throw new BackendError(
          `API response for GET /api${path} was not valid JSON`,
        );
      }
      if (!isRecord(body) || !("data" in body)) {
        throw new BackendError(
          `API response for GET /api${path} did not contain data`,
        );
      }
      return (body as ApiEnvelope<T>).data;
    } catch (error) {
      if (error instanceof BackendError) throw error;
      if (isAbortError(error))
        throw new BackendError(`API request timed out: GET /api${path}`);
      throw new BackendError(`API request failed: GET /api${path}`);
    } finally {
      clearTimeout(timeout);
    }
  }
}

class ApiHttpError extends BackendError {
  constructor(
    readonly status: number,
    path: string,
  ) {
    super(`API request failed with status ${status}: GET /api${path}`);
  }
}

export function createBackend(
  repositoryRoot: string,
  apiUrl = process.env.MATHEN_API_URL,
): Backend {
  return apiUrl?.trim()
    ? new ApiBackend(apiUrl.trim(), fetch, 10_000, process.env.MATHEN_API_TOKEN)
    : new FilesystemBackend(repositoryRoot);
}

function normalizeBaseUrl(value: string): URL {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      throw new Error("unsupported protocol");
    }
    url.username = "";
    url.password = "";
    url.search = "";
    url.hash = "";
    if (url.pathname.endsWith("/api")) url.pathname = url.pathname.slice(0, -4);
    return url;
  } catch {
    throw new BackendError("MATHEN_API_URL must be a valid HTTP(S) URL");
  }
}

function normalizeCard(value: unknown): ArchitectureCard {
  const card = asRecord(value);
  return {
    id: requiredString(card.id, "id", "/api/systems/:id"),
    name: requiredString(card.name, "name", "/api/systems/:id"),
    summary: requiredString(card.summary, "summary", "/api/systems/:id"),
    scope: stringArray(card.scope),
    features: Array.isArray(card.features)
      ? card.features.map(normalizeFeature)
      : [],
    mathematical_views: Array.isArray(card.mathematical_views)
      ? card.mathematical_views.map((view) => asRecord(view))
      : [],
    trade_offs: Array.isArray(card.trade_offs)
      ? card.trade_offs.map((tradeOff) => asRecord(tradeOff))
      : [],
    evidence: Array.isArray(card.evidence)
      ? card.evidence.map(normalizeEvidence)
      : [],
    related_systems: stringArray(card.related_systems),
    version_context: optionalString(card.version_context),
    temporal_context: optionalRecord(card.temporal_context),
    relations: recordArray(card.relations),
    feature_relations: relationArray(card.feature_relations),
    composition: optionalRecord(card.composition),
  };
}

function toProjectionSystem(card: ArchitectureCard): ProjectionSystem {
  return {
    id: card.id,
    name: card.name,
    scope: card.scope,
    features: card.features.map((feature) => ({
      ...feature,
      metadata: {
        ...feature.metadata,
        ...(feature.claim_status ? { claim_status: feature.claim_status } : {}),
        ...(feature.validity_scope
          ? { validity_scope: feature.validity_scope }
          : {}),
      },
    })),
    mathematical_views: card.mathematical_views.flatMap((view) => [
      {
        id:
          typeof view.id === "string" || typeof view.id === "number"
            ? view.id
            : stableProjectionViewId(card.id, {
                model: typeof view.model === "string" ? view.model : "",
                question:
                  typeof view.question === "string" ? view.question : "",
                metadata: optionalRecord(view.metadata) ?? {},
              }),
        model:
          typeof view.model === "string" ? view.model : "Unclassified model",
        question: typeof view.question === "string" ? view.question : "",
        assumptions: stringArray(view.assumptions),
        claim_type:
          typeof view.claim_type === "string" ? view.claim_type : "inference",
        claim_status: optionalString(view.claim_status),
        evidence_ids: stringArray(view.evidence_ids),
        metadata: {
          ...optionalRecord(view.metadata),
          ...(typeof view.claim_status === "string"
            ? { claim_status: view.claim_status }
            : {}),
          ...(isRecord(view.validity_scope)
            ? { validity_scope: view.validity_scope }
            : {}),
          ...(isRecord(view.contract) ? { contract: view.contract } : {}),
        },
      },
    ]),
    composition: card.composition ?? null,
  };
}

function toProjectionAnalogy(
  document: Record<string, unknown>,
): ProjectionAnalogy {
  return {
    id: requiredString(document.id, "id", "filesystem analogy"),
    name: requiredString(document.name, "name", "filesystem analogy"),
    document,
  };
}

function toProjectionMicrostructure(
  document: Record<string, unknown>,
): ProjectionMicrostructure {
  return {
    id: requiredString(document.id, "id", "filesystem microstructure"),
    name: requiredString(document.name, "name", "filesystem microstructure"),
    document,
  };
}

function normalizeFeature(value: unknown): Feature {
  const feature = asRecord(value);
  return {
    id: requiredString(feature.id, "id", "/api/features"),
    name: requiredString(feature.name, "name", "/api/features"),
    category: requiredString(feature.category, "category", "/api/features"),
    claim_type: requiredString(
      feature.claim_type,
      "claim_type",
      "/api/features",
    ),
    description: requiredString(
      feature.description,
      "description",
      "/api/features",
    ),
    benefits: stringArray(feature.benefits),
    costs: stringArray(feature.costs),
    evidence_ids: stringArray(feature.evidence_ids),
    metadata: optionalRecord(feature.metadata),
  };
}

function normalizeCompositionResult(value: unknown): CompositionSearchResult {
  const result = asRecord(value);
  return {
    system_id: requiredString(
      result.system_id,
      "system_id",
      "/api/compositions",
    ),
    system_name: requiredString(
      result.system_name,
      "system_name",
      "/api/compositions",
    ),
    version_context: optionalString(result.version_context) ?? null,
    composition: asRecord(result.composition),
    evidence: Array.isArray(result.evidence)
      ? result.evidence.map(normalizeEvidence)
      : [],
  };
}

function normalizeFeatureRelationResult(value: unknown): FeatureRelationResult {
  const relation = asRecord(value);
  return {
    source_system_id: requiredString(
      relation.source_system_id,
      "source_system_id",
      "/api/feature-relations",
    ),
    ...normalizeFeatureRelation(relation, "/api/feature-relations"),
  };
}

function normalizeFeatureRelation(
  value: unknown,
  endpoint: string,
): FeatureRelation {
  const relation = asRecord(value);
  const notes = optionalString(relation.notes);
  return {
    source_feature_id: requiredString(
      relation.source_feature_id,
      "source_feature_id",
      endpoint,
    ),
    target_system_id: requiredString(
      relation.target_system_id,
      "target_system_id",
      endpoint,
    ),
    target_feature_id: requiredString(
      relation.target_feature_id,
      "target_feature_id",
      endpoint,
    ),
    type: requiredString(relation.type, "type", endpoint),
    claim_type: requiredString(relation.claim_type, "claim_type", endpoint),
    claim_status: requiredString(
      relation.claim_status,
      "claim_status",
      endpoint,
    ),
    evidence_ids: stringArray(relation.evidence_ids),
    ...(notes ? { notes } : {}),
  };
}

function normalizeEvidence(value: unknown): Evidence {
  const evidence = asRecord(value);
  const accessed = optionalString(evidence.accessed);
  const notes = optionalString(evidence.notes);
  return {
    id: requiredString(evidence.id, "id", "/api/systems/:id"),
    kind: requiredString(evidence.kind, "kind", "/api/systems/:id"),
    title: requiredString(evidence.title, "title", "/api/systems/:id"),
    uri: requiredString(evidence.uri, "uri", "/api/systems/:id"),
    ...(accessed ? { accessed } : {}),
    ...(notes ? { notes } : {}),
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new BackendError("API returned an invalid object");
  }
  return value as Record<string, unknown>;
}

function requiredString(
  value: unknown,
  field: string,
  endpoint: string,
): string {
  if (typeof value !== "string")
    throw new BackendError(
      `API response for GET ${endpoint} has invalid ${field}`,
    );
  return value;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function normalizeLayeredGraph(value: unknown): LayeredGraphProjection {
  const graph = asRecord(value);
  if (
    graph.schema_version !== "1.0" ||
    !Array.isArray(graph.nodes) ||
    !Array.isArray(graph.edges)
  ) {
    throw new BackendError(
      "API response for GET /api/graph/layers has invalid data",
    );
  }
  return {
    schema_version: "1.0",
    ...(typeof graph.origin === "string" ? { origin: graph.origin } : {}),
    nodes: graph.nodes.filter(isRecord).map((node) => ({
      id: requiredString(node.id, "id", "/api/graph/layers"),
      layer: projectionLayer(node.layer),
      kind: requiredString(node.kind, "kind", "/api/graph/layers"),
      label: requiredString(node.label, "label", "/api/graph/layers"),
      metadata: optionalRecord(node.metadata) ?? {},
    })),
    edges: graph.edges.filter(isRecord).flatMap(normalizeProjectionEdge),
  };
}

function projectionLayer(value: unknown): ProjectionLayer {
  const layer = requiredString(value, "layer", "/api/graph/layers");
  const allowed: ProjectionLayer[] = [
    "system",
    "property",
    "microstructure",
    "mathematical-contract",
    "composition",
    "component",
    "property-effect",
    "relation",
    "analogy",
  ];
  if (!allowed.includes(layer as ProjectionLayer)) {
    throw new BackendError(
      `API response for GET /api/graph/layers has invalid layer`,
    );
  }
  return layer as ProjectionLayer;
}

function normalizeProjectionEdge(
  value: Record<string, unknown>,
): ProjectionEdge[] {
  const source = optionalString(value.source);
  const target = optionalString(value.target);
  const type = optionalString(value.type);
  if (!source || !target || !type) return [];
  return [
    {
      source,
      target,
      type,
      ...(optionalString(value.claim_type)
        ? { claim_type: optionalString(value.claim_type) }
        : {}),
      ...(optionalString(value.claim_status)
        ? { claim_status: optionalString(value.claim_status) }
        : {}),
      evidence_ids: stringArray(value.evidence_ids),
      ...(optionalString(value.notes)
        ? { notes: optionalString(value.notes) }
        : {}),
      ...(optionalRecord(value.metadata)
        ? { metadata: optionalRecord(value.metadata) }
        : {}),
    },
  ];
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function optionalRecord(value: unknown): Record<string, unknown> | undefined {
  return isRecord(value) ? value : undefined;
}

function recordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function relationArray(value: unknown): FeatureRelation[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter(isRecord)
    .map((relation) => normalizeFeatureRelation(relation, "/api/systems/:id"));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isCompositionRecord(
  value: Record<string, unknown> | undefined,
): value is Record<string, unknown> & {
  inputs: Array<Record<string, unknown> & { system_id: string }>;
  claim_status: string;
  constraints: unknown[];
  preserved_properties: unknown[];
  conflicts: unknown[];
  evidence_ids: string[];
} {
  if (!value || !optionalString(value.claim_status)) return false;
  if (!Array.isArray(value.inputs) || value.inputs.length === 0) return false;
  if (!Array.isArray(value.constraints)) return false;
  if (!Array.isArray(value.preserved_properties)) return false;
  if (!Array.isArray(value.conflicts)) return false;
  if (
    !Array.isArray(value.evidence_ids) ||
    value.evidence_ids.length === 0 ||
    !value.evidence_ids.every(
      (item) => typeof item === "string" && item.length > 0,
    )
  ) {
    return false;
  }
  return value.inputs.every(
    (input) =>
      isRecord(input) &&
      typeof input.system_id === "string" &&
      input.system_id.length > 0,
  );
}

function toCompositionResult(
  card: ArchitectureCard,
  composition: Record<string, unknown> & {
    inputs: Array<Record<string, unknown> & { system_id: string }>;
    claim_status: string;
    constraints: unknown[];
    preserved_properties: unknown[];
    conflicts: unknown[];
    evidence_ids: string[];
  },
): CompositionSearchResult {
  return {
    system_id: card.id,
    system_name: card.name,
    version_context: card.version_context ?? null,
    composition,
    evidence: (card.evidence ?? []).filter((evidence) =>
      composition.evidence_ids.includes(evidence.id),
    ),
  };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
