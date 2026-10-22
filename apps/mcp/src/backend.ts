import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";

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
  listSystems(includeDrafts: boolean): Promise<SystemSummary[]>;
  getSystem(systemId: string, includeDrafts: boolean): Promise<ArchitectureCard | undefined>;
  searchFeatures(
    query: string,
    category: string | undefined,
    claimType: string | undefined,
    includeDrafts: boolean,
    limit: number,
  ): Promise<FeatureSearchResult[]>;
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
  private readonly systemsDirectory: string;
  private readonly draftsDirectory: string;
  private readonly bundlesDirectory: string;

  constructor(repositoryRoot: string) {
    this.systemsDirectory = resolve(repositoryRoot, "data/systems");
    this.draftsDirectory = resolve(repositoryRoot, "data/drafts");
    this.bundlesDirectory = resolve(repositoryRoot, "data/modeling");
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

  async getSystem(systemId: string, includeDrafts: boolean): Promise<ArchitectureCard | undefined> {
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
      .sort((left, right) =>
        left.system_name.localeCompare(right.system_name) ||
        left.system_id.localeCompare(right.system_id),
      )
      .slice(0, limit);
  }

  private async loadAllCards(includeDrafts: boolean): Promise<ArchitectureCard[]> {
    const reviewed = await this.loadCards(this.systemsDirectory);
    if (!includeDrafts) return reviewed;
    const drafts = await this.loadCards(this.draftsDirectory);
    return [
      ...reviewed,
      ...drafts.filter((draft) => !reviewed.some((card) => card.id === draft.id)),
    ];
  }

  private async loadCards(directory: string): Promise<ArchitectureCard[]> {
    const entries = (await readdir(directory, { withFileTypes: true }))
      .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
      .map((entry) => entry.name);
    return Promise.all(
      entries.sort().map((entry) => readJson<ArchitectureCard>(resolve(directory, entry))),
    );
  }
}

type Fetcher = (input: string | URL, init?: RequestInit) => Promise<Response>;

type ApiEnvelope<T> = { data: T };

export class ApiBackend implements Backend {
  private readonly baseUrl: URL;
  private readonly fetcher: Fetcher;
  private readonly timeoutMs: number;

  constructor(baseUrl: string, fetcher: Fetcher = fetch, timeoutMs = 10_000) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
    this.fetcher = fetcher;
    this.timeoutMs = timeoutMs;
  }

  async listSystems(includeDrafts: boolean): Promise<SystemSummary[]> {
    this.rejectDrafts(includeDrafts);
    const data = await this.request<unknown[]>("/systems");
    if (!Array.isArray(data))
      throw new BackendError("API response for GET /api/systems has invalid data");
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

  async getSystem(systemId: string, includeDrafts: boolean): Promise<ArchitectureCard | undefined> {
    this.rejectDrafts(includeDrafts);
    try {
      return normalizeCard(await this.request<unknown>(`/systems/${encodeURIComponent(systemId)}`));
    } catch (error) {
      if (error instanceof ApiHttpError && error.status === 404) return undefined;
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
      throw new BackendError("API response for GET /api/features has invalid data");
    return data.map((result) => {
      const record = asRecord(result);
      return {
        system_id: requiredString(record.system_id, "system_id", "/api/features"),
        system_name: requiredString(record.system_name, "system_name", "/api/features"),
        feature: normalizeFeature(record.feature ?? record),
      };
    });
  }

  async getModelingBundle(systemId: string): Promise<unknown> {
    try {
      return await this.request<unknown>(`/modeling/${encodeURIComponent(systemId)}`);
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
      throw new BackendError("API response for GET /api/compositions has invalid data");
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
        headers: { accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new ApiHttpError(response.status, path);
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        throw new BackendError(`API response for GET /api${path} was not valid JSON`);
      }
      if (!isRecord(body) || !("data" in body)) {
        throw new BackendError(`API response for GET /api${path} did not contain data`);
      }
      return (body as ApiEnvelope<T>).data;
    } catch (error) {
      if (error instanceof BackendError) throw error;
      if (isAbortError(error)) throw new BackendError(`API request timed out: GET /api${path}`);
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
  return apiUrl?.trim() ? new ApiBackend(apiUrl.trim()) : new FilesystemBackend(repositoryRoot);
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
    features: Array.isArray(card.features) ? card.features.map(normalizeFeature) : [],
    mathematical_views: Array.isArray(card.mathematical_views)
      ? card.mathematical_views.map((view) => asRecord(view))
      : [],
    trade_offs: Array.isArray(card.trade_offs)
      ? card.trade_offs.map((tradeOff) => asRecord(tradeOff))
      : [],
    evidence: Array.isArray(card.evidence) ? card.evidence.map(normalizeEvidence) : [],
    related_systems: stringArray(card.related_systems),
    version_context: optionalString(card.version_context),
    temporal_context: optionalRecord(card.temporal_context),
    relations: recordArray(card.relations),
    composition: optionalRecord(card.composition),
  };
}

function normalizeFeature(value: unknown): Feature {
  const feature = asRecord(value);
  return {
    id: requiredString(feature.id, "id", "/api/features"),
    name: requiredString(feature.name, "name", "/api/features"),
    category: requiredString(feature.category, "category", "/api/features"),
    claim_type: requiredString(feature.claim_type, "claim_type", "/api/features"),
    description: requiredString(feature.description, "description", "/api/features"),
    benefits: stringArray(feature.benefits),
    costs: stringArray(feature.costs),
    evidence_ids: stringArray(feature.evidence_ids),
  };
}

function normalizeCompositionResult(value: unknown): CompositionSearchResult {
  const result = asRecord(value);
  return {
    system_id: requiredString(result.system_id, "system_id", "/api/compositions"),
    system_name: requiredString(result.system_name, "system_name", "/api/compositions"),
    version_context: optionalString(result.version_context) ?? null,
    composition: asRecord(result.composition),
    evidence: Array.isArray(result.evidence)
      ? result.evidence.map(normalizeEvidence)
      : [],
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

function requiredString(value: unknown, field: string, endpoint: string): string {
  if (typeof value !== "string")
    throw new BackendError(`API response for GET ${endpoint} has invalid ${field}`);
  return value;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
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
    !value.evidence_ids.every((item) => typeof item === "string" && item.length > 0)
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
