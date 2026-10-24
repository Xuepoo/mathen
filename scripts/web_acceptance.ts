import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

type JsonRecord = Record<string, unknown>;

export type AcceptanceEvidence = {
  kind: "api" | "browser";
  name: string;
  status: "passed" | "not-run";
  details: string;
};

export type AcceptanceReport = {
  baseUrl: string;
  sourceCommit: string;
  generatedAt: string;
  evidence: AcceptanceEvidence[];
  externalEvidenceGaps: string[];
};

export type ApiAcceptanceReport = {
  accessConfig: JsonRecord;
  graph: { nodes: unknown[]; edges: unknown[] };
  modelGraph: { nodes: unknown[]; edges: unknown[] };
};

type Request = (input: string, init?: RequestInit) => Promise<Response>;

function record(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null;
}

function array(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${label} is not an array`);
  return value;
}

function dataEnvelope(value: unknown, label: string): JsonRecord {
  if (!record(value) || !record(value.data)) throw new Error(`${label} is not a data envelope`);
  return value.data;
}

async function json(response: Response, label: string) {
  if (!response.ok) throw new Error(`${label} returned HTTP ${response.status}`);
  return response.json() as Promise<unknown>;
}

export async function runApiChecks(
  baseUrl: string,
  token = "",
  request: Request = fetch,
): Promise<ApiAcceptanceReport> {
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  const get = (path: string) => request(new URL(path, baseUrl).toString(), { headers });

  const access = dataEnvelope(
    await json(await get("/api/access/config"), "access config"),
    "access config",
  );
  if (typeof access.enabled !== "boolean" || typeof access.authenticated !== "boolean")
    throw new Error("access config does not expose enabled/authenticated booleans");

  const graphPayload = await json(await get("/api/graph"), "graph");
  if (!record(graphPayload)) throw new Error("graph is not an object");
  const graph = {
    nodes: array(graphPayload.nodes, "graph nodes"),
    edges: array(graphPayload.edges, "graph edges"),
  };

  const modelPayload = dataEnvelope(
    await json(await get("/api/graph/models"), "model graph"),
    "model graph",
  );
  const modelGraph = {
    nodes: array(modelPayload.nodes, "model graph nodes"),
    edges: array(modelPayload.edges, "model graph edges"),
  };
  if (!modelGraph.nodes.some((node) => record(node) && node.type === "model"))
    throw new Error("model graph has no model node");
  if (!modelGraph.edges.every((edge) => record(edge) && edge.type === "modeled-by"))
    throw new Error("model graph contains a non-modeled-by edge");

  return { accessConfig: access, graph, modelGraph };
}

function evidence(
  name: string,
  details: string,
  kind: AcceptanceEvidence["kind"] = "api",
): AcceptanceEvidence {
  return { kind, name, status: "passed", details };
}

function gaps(): string[] {
  return [
    "Real mobile-device browser coverage, including touch and viewport behavior, remains external.",
    "Drag-node, pan, orbit, and pinch interaction results are not asserted by this harness and remain external.",
    "Representative mobile Lighthouse/Core Web Vitals evidence requires a named device, browser, network profile, build, URL, and workload.",
  ];
}

export function renderAcceptanceReport(report: AcceptanceReport) {
  const lines = [
    "# Mathen web acceptance evidence",
    "",
    "This report contains only checks actually executed by the harness. It does not infer browser, device, touch, or drag results.",
    "",
    "## Run metadata",
    "",
    `- Base URL: **${report.baseUrl}**`,
    `- Source commit: **${report.sourceCommit || "not recorded"}**`,
    `- Generated: **${report.generatedAt}**`,
    "",
    "## Executed evidence",
    "",
    "| Kind | Check | Status | Details |",
    "| --- | --- | --- | --- |",
    ...report.evidence.map(
      (item) =>
        `| ${item.kind} | ${item.name} | ${item.status} | ${item.details.replaceAll("|", "\\|")} |`,
    ),
    "",
    "## External evidence gaps",
    "",
    ...report.externalEvidenceGaps.map((gap) => `- ${gap}`),
    "",
  ];
  return `${lines.join("\n")}\n`;
}

function argument(name: string) {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
}

async function browserChecks(baseUrl: string, tracePath: string, modulePath?: string) {
  const moduleName = modulePath ?? "playwright";
  let chromium: { launch(options?: JsonRecord): Promise<JsonRecord> };
  try {
    const playwright = (await import(moduleName)) as {
      chromium?: { launch(options?: JsonRecord): Promise<JsonRecord> };
    };
    if (!playwright.chromium) throw new Error("module has no chromium export");
    chromium = playwright.chromium;
  } catch (error) {
    throw new Error(
      `Browser checks require Playwright. Install it as an opt-in dependency or pass --browser-module /absolute/path/to/playwright/index.mjs (${String(error)})`,
    );
  }

  const browser = await chromium.launch({ headless: true });
  const context = (await (browser as any).newContext()) as any;
  await context.tracing.start({
    screenshots: true,
    snapshots: true,
    sources: true,
  });
  const page = await context.newPage();
  try {
    await page.goto(new URL("/", baseUrl).toString(), {
      waitUntil: "domcontentloaded",
    });
    await page.locator("#counts").waitFor({ state: "visible" });
    await page.locator("#counts").waitFor({ state: "attached" });
    await page.waitForFunction(() =>
      /systems \/ \d+ relations/.test(document.querySelector("#counts")?.textContent ?? ""),
    );

    const resources = await page.evaluate(() =>
      performance.getEntriesByType("resource").map((entry) => entry.name),
    );
    if (!resources.some((name: string) => /3d-force-graph/i.test(name)))
      throw new Error("lazy graph runtime chunk was not requested");

    await page.getByRole("button", { name: "Math models" }).click();
    await page.waitForFunction(() =>
      /systems \/ \d+ models \/ \d+ model links/.test(
        document.querySelector("#counts")?.textContent ?? "",
      ),
    );
    await page.getByRole("button", { name: "Systems" }).click();
    await page.waitForFunction(() =>
      /systems \/ \d+ relations/.test(document.querySelector("#counts")?.textContent ?? ""),
    );

    const catalog = page.getByRole("button", { name: /Browse systems/ });
    await catalog.focus();
    await page.keyboard.press("Enter");
    await page.getByRole("dialog", { name: "Browse systems" }).waitFor({ state: "visible" });
    await page.keyboard.press("Escape");
    await page.getByRole("dialog", { name: "Browse systems" }).waitFor({ state: "hidden" });
    if ((await page.evaluate(() => document.activeElement?.id)) !== "catalog-open")
      throw new Error("Escape did not restore focus to catalog opener");

    await page.keyboard.press("/");
    if ((await page.evaluate(() => document.activeElement?.id)) !== "search")
      throw new Error("slash keyboard shortcut did not focus search");
    await page.getByRole("searchbox", { name: /Search systems/ }).fill("Temporal");
    await page.keyboard.press("Enter");
    await page.locator("#inspector").waitFor({ state: "visible" });
  } finally {
    await context.tracing.stop({ path: resolve(tracePath) });
    await context.close();
    await browser.close();
  }
}

async function main() {
  const baseUrl = argument("--base-url") ?? "http://127.0.0.1:5173/";
  const token = argument("--api-token") ?? process.env.MATHEN_API_ACCESS_TOKEN ?? "";
  const output = argument("--output") ?? "docs/web-acceptance-report.md";
  const tracePath = argument("--trace") ?? "/tmp/opencode/mathen-web-acceptance.zip";
  const api = await runApiChecks(baseUrl, token);
  const report: AcceptanceReport = {
    baseUrl,
    sourceCommit: process.env.MATHEN_COMMIT ?? "",
    generatedAt: new Date().toISOString(),
    evidence: [
      evidence(
        "access config",
        `enabled=${String(api.accessConfig.enabled)}, authenticated=${String(api.accessConfig.authenticated)}`,
      ),
      evidence(
        "systems graph",
        `${api.graph.nodes.length} nodes / ${api.graph.edges.length} edges`,
      ),
      evidence(
        "mathematical model graph",
        `${api.modelGraph.nodes.length} nodes / ${api.modelGraph.edges.length} modeled-by edges`,
      ),
    ],
    externalEvidenceGaps: gaps(),
  };
  if (process.argv.includes("--browser")) {
    await mkdir(dirname(resolve(tracePath)), { recursive: true });
    await browserChecks(baseUrl, tracePath, argument("--browser-module"));
    report.evidence.push(
      evidence("lazy graph and keyboard browser flow", `headless trace: ${tracePath}`, "browser"),
    );
  } else {
    report.evidence.push({
      kind: "browser",
      name: "lazy graph and keyboard browser flow",
      status: "not-run",
      details: "Opt-in: pass --browser and an available Playwright module.",
    });
  }
  await mkdir(dirname(resolve(output)), { recursive: true });
  await writeFile(output, renderAcceptanceReport(report), "utf8");
  process.stdout.write(renderAcceptanceReport(report));
}

if (import.meta.main) await main();
