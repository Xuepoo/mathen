import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

type JsonRecord = Record<string, unknown>;

export type AcceptanceEvidence = {
  kind: "api" | "browser";
  name: string;
  status: "passed" | "not-run" | "external";
  details: string;
  trace?: TraceMetadata;
};

export type TraceMetadata = {
  format: "playwright-trace";
  path: string;
  browser: "chromium";
  headless: boolean;
  viewport: { width: number; height: number };
};

export type ExternalEvidence = {
  name: string;
  reason: string;
  required: string[];
};

export type AcceptanceReport = {
  baseUrl: string;
  sourceCommit: string;
  generatedAt: string;
  evidence: AcceptanceEvidence[];
  externalEvidenceGaps: string[];
  externalEvidence?: ExternalEvidence[];
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
    "Touch and pinch interaction results remain external unless a named touch-capable browser execution is supplied.",
    "Representative mobile Lighthouse/Core Web Vitals evidence requires a named device, browser, network profile, build, URL, and workload.",
  ];
}

function structuredExternalEvidence(): ExternalEvidence[] {
  return [
    {
      name: "real mobile touch and viewport behavior",
      reason:
        "The opt-in browser path uses a desktop/headless Chromium context and does not emulate or claim mobile hardware.",
      required: ["named device", "browser", "viewport", "touch execution", "URL", "build"],
    },
    {
      name: "mobile Lighthouse/Core Web Vitals",
      reason: "This harness does not execute a mobile Lighthouse workload or network profile.",
      required: ["named device", "browser", "network profile", "build", "URL", "workload"],
    },
  ];
}

function traceDetails(item: AcceptanceEvidence) {
  if (!item.trace) return item.details;
  return `${item.details} (trace=${item.trace.path}, browser=${item.trace.browser}, headless=${String(item.trace.headless)}, viewport=${item.trace.viewport.width}x${item.trace.viewport.height})`;
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
        `| ${item.kind} | ${item.name} | ${item.status} | ${traceDetails(item).replaceAll("|", "\\|")} |`,
    ),
    "",
    "## External evidence gaps",
    "",
    ...report.externalEvidenceGaps.map((gap) => `- ${gap}`),
    "",
    ...(report.externalEvidence?.length
      ? [
          "## Structured external evidence",
          "",
          "| Gap | Why it is external | Required execution metadata |",
          "| --- | --- | --- |",
          ...report.externalEvidence.map(
            (item) => `| ${item.name} | ${item.reason} | ${item.required.join(", ")} |`,
          ),
          "",
        ]
      : []),
  ];
  return `${lines.join("\n")}\n`;
}

function argument(name: string) {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
}

function flag(name: string) {
  return process.argv.includes(name);
}

function printHelp() {
  process.stdout.write(
    `Mathen web acceptance harness\n\nOptions:\n  --base-url URL       API-backed preview URL (default: http://127.0.0.1:5173/)\n  --api-token TOKEN    Optional API service token\n  --output PATH        Markdown report path\n  --browser            Run optional Playwright browser checks\n  --browser-module P  Playwright module name or absolute path\n  --trace PATH         Playwright trace path\n  --drag               With --browser, execute a 2D node pointer drag path\n  --pan                With --browser, execute a 2D background pan path\n  --orbit              With --browser, switch to 3D and execute an orbit path\n  --help               Show this help\n\nInteraction flags are opt-in. Without a matching browser execution they are\nreported as not-run; mobile hardware, touch, and pinch evidence remains external.\n`,
  );
}

type BrowserOptions = {
  drag: boolean;
  pan: boolean;
  orbit: boolean;
};

type BrowserCheckResult = {
  trace: TraceMetadata;
  interactions: AcceptanceEvidence[];
};

const interactionChecks = [
  ["--drag", "2D node drag pointer path"],
  ["--pan", "2D background pan pointer path"],
  ["--orbit", "3D orbit pointer path"],
] as const;

async function pointerPath(
  page: any,
  name: string,
  start: { x: number; y: number },
  end: { x: number; y: number },
  expectedStatus?: string,
) {
  await page.evaluate(() => {
    const canvas = document.querySelector("#graph canvas");
    if (!canvas) throw new Error("graph canvas is missing");
    const events = { down: 0, move: 0, up: 0 };
    (window as any).__mathenAcceptancePointerEvents = events;
    canvas.addEventListener("pointerdown", () => events.down++, {
      once: false,
    });
    canvas.addEventListener("pointermove", () => events.move++, {
      once: false,
    });
    canvas.addEventListener("pointerup", () => events.up++, { once: false });
  });
  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  if (expectedStatus)
    await page.waitForFunction(
      (status: string) => document.querySelector("#simulation-status")?.textContent === status,
      expectedStatus,
    );
  await page.mouse.move(end.x, end.y, { steps: 5 });
  await page.mouse.up();
  const events = await page.evaluate(() => (window as any).__mathenAcceptancePointerEvents);
  if (!events || events.down < 1 || events.move < 1 || events.up < 1)
    throw new Error(`${name} did not observe a complete pointer path on the graph canvas`);
  return `${name}: observed pointerdown=${events.down}, pointermove=${events.move}, pointerup=${events.up}`;
}

async function browserInteractions(page: any, options: BrowserOptions) {
  const canvas = page.locator("#graph canvas");
  const box = await canvas.boundingBox();
  if (!box) throw new Error("graph canvas has no bounding box");
  const results: AcceptanceEvidence[] = [];

  if (options.drag) {
    const label = page.locator("#graph-names .graph-name:not([hidden])").first();
    const labelBox = await label.boundingBox();
    if (!labelBox) throw new Error("no visible graph node label available for drag assertion");
    const start = {
      x: Math.max(box.x + 8, labelBox.x - 15),
      y: labelBox.y + labelBox.height / 2,
    };
    const end = {
      x: Math.min(box.x + box.width - 8, start.x + 36),
      y: start.y + 18,
    };
    results.push({
      kind: "browser",
      name: "2D node drag pointer path",
      status: "passed",
      details: await pointerPath(page, "2D node drag", start, end, "Forces settling…"),
    });
  }
  if (options.pan) {
    const start = { x: box.x + box.width * 0.2, y: box.y + box.height * 0.8 };
    const end = { x: start.x + 40, y: start.y - 24 };
    results.push({
      kind: "browser",
      name: "2D background pan pointer path",
      status: "passed",
      details: await pointerPath(page, "2D background pan", start, end),
    });
  }
  if (options.orbit) {
    await page.getByRole("button", { name: "3D" }).click();
    await page.waitForFunction(
      () => document.querySelector("#mode-3")?.getAttribute("aria-pressed") === "true",
    );
    const start = { x: box.x + box.width * 0.72, y: box.y + box.height * 0.45 };
    const end = { x: start.x - 48, y: start.y + 20 };
    results.push({
      kind: "browser",
      name: "3D orbit pointer path",
      status: "passed",
      details: await pointerPath(page, "3D orbit", start, end),
    });
  }
  return results;
}

async function browserChecks(
  baseUrl: string,
  tracePath: string,
  modulePath: string | undefined,
  options: BrowserOptions,
): Promise<BrowserCheckResult> {
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
  const viewport = { width: 1280, height: 900 };
  const context = (await (browser as any).newContext({ viewport })) as any;
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
    const interactions = await browserInteractions(page, options);
    return {
      trace: {
        format: "playwright-trace",
        path: tracePath,
        browser: "chromium",
        headless: true,
        viewport,
      },
      interactions,
    };
  } finally {
    await context.tracing.stop({ path: resolve(tracePath) });
    await context.close();
    await (browser as any).close();
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
    externalEvidence: structuredExternalEvidence(),
  };
  report.evidence.push(
    ...(report.externalEvidence ?? []).map((item) => ({
      kind: "browser" as const,
      name: item.name,
      status: "external" as const,
      details: item.reason,
    })),
  );
  if (flag("--browser")) {
    await mkdir(dirname(resolve(tracePath)), { recursive: true });
    const browser = await browserChecks(baseUrl, tracePath, argument("--browser-module"), {
      drag: flag("--drag"),
      pan: flag("--pan"),
      orbit: flag("--orbit"),
    });
    report.evidence.push({
      ...evidence(
        "lazy graph and keyboard browser flow",
        `headless trace: ${tracePath}`,
        "browser",
      ),
      trace: browser.trace,
    });
    report.evidence.push(
      ...browser.interactions.map((item) => ({
        ...item,
        trace: browser.trace,
      })),
    );
    const executed = new Set(browser.interactions.map((item) => item.name));
    for (const [flagName, name] of interactionChecks) {
      if (!executed.has(name))
        report.evidence.push({
          kind: "browser",
          name,
          status: "not-run",
          details: `Opt-in: pass ${flagName} with --browser to execute this pointer path.`,
          trace: browser.trace,
        });
    }
  } else {
    report.evidence.push({
      kind: "browser",
      name: "lazy graph and keyboard browser flow",
      status: "not-run",
      details: "Opt-in: pass --browser and an available Playwright module.",
    });
    for (const [flagName, name] of interactionChecks) {
      if (flag(flagName))
        report.evidence.push({
          kind: "browser",
          name,
          status: "not-run",
          details: `Requested with ${flagName}, but no browser was executed. Pass --browser with an available Playwright module.`,
        });
    }
  }
  await mkdir(dirname(resolve(output)), { recursive: true });
  await writeFile(output, renderAcceptanceReport(report), "utf8");
  process.stdout.write(renderAcceptanceReport(report));
}

if (import.meta.main) {
  if (flag("--help")) printHelp();
  else await main();
}
