import { expect, test } from "bun:test";
import { renderAcceptanceReport, runApiChecks } from "./web_acceptance";

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("checks access, systems graph, and model graph API contracts", async () => {
  const requests: string[] = [];
  const report = await runApiChecks("http://api.test", "secret", async (input, init) => {
    requests.push(`${input} ${init?.headers ? "authorized" : "anonymous"}`);
    if (input.endsWith("/api/access/config"))
      return response({
        data: { enabled: false, authenticated: false, site_key: null },
      });
    if (input.endsWith("/api/graph"))
      return response({
        nodes: [{ id: "git", name: "Git", type: "system" }],
        edges: [],
      });
    return response({
      data: {
        nodes: [
          { id: "git", name: "Git", type: "system" },
          { id: "model:graph", name: "Graph", type: "model" },
        ],
        edges: [{ source: "git", target: "model:graph", type: "modeled-by" }],
      },
    });
  });

  expect(report.graph.nodes).toHaveLength(1);
  expect(report.modelGraph.edges).toHaveLength(1);
  expect(requests).toEqual([
    "http://api.test/api/access/config authorized",
    "http://api.test/api/graph authorized",
    "http://api.test/api/graph/models authorized",
  ]);
});

test("rejects an uncontracted model graph", async () => {
  await expect(
    runApiChecks("http://api.test", "", async () =>
      response({ data: { nodes: [{ id: "git", type: "system" }], edges: [] } }),
    ),
  ).rejects.toThrow("access config does not expose enabled/authenticated booleans");
});

test("renders explicit unrun and external evidence boundaries", () => {
  const output = renderAcceptanceReport({
    baseUrl: "http://127.0.0.1:5173/",
    sourceCommit: "abc123",
    generatedAt: "2026-10-25T00:00:00.000Z",
    evidence: [
      {
        kind: "api",
        name: "systems graph",
        status: "passed",
        details: "1 node / 0 edges",
      },
      {
        kind: "browser",
        name: "browser flow",
        status: "not-run",
        details: "opt-in",
      },
      {
        kind: "browser",
        name: "3D orbit pointer path",
        status: "external",
        details: "Requires an executed browser path; no result inferred.",
      },
    ],
    externalEvidenceGaps: [
      "Real mobile-device browser coverage remains external.",
      "Touch and pinch interaction results remain external unless a named touch-capable browser execution is supplied.",
    ],
  });
  expect(output).toContain("browser flow");
  expect(output).toContain("not-run");
  expect(output).toContain("Real mobile-device browser coverage remains external.");
  expect(output).toContain("Touch and pinch interaction results remain external");
  expect(output).not.toContain("mobile pass");
});

test("renders structured external requirements and trace metadata", () => {
  const output = renderAcceptanceReport({
    baseUrl: "http://preview.test/",
    sourceCommit: "abc123",
    generatedAt: "2026-10-25T00:00:00.000Z",
    evidence: [
      {
        kind: "browser",
        name: "3D orbit pointer path",
        status: "passed",
        details: "observed pointer path",
        trace: {
          format: "playwright-trace",
          path: "/tmp/opencode/trace.zip",
          browser: "chromium",
          headless: true,
          viewport: { width: 1280, height: 900 },
        },
      },
    ],
    externalEvidenceGaps: ["Touch remains external."],
    externalEvidence: [
      {
        name: "real mobile touch",
        reason: "No mobile hardware was executed.",
        required: ["device", "browser", "touch execution"],
      },
    ],
  });
  expect(output).toContain("Status | Details");
  expect(output).toContain("trace=/tmp/opencode/trace.zip");
  expect(output).toContain("Structured external evidence");
  expect(output).toContain("device, browser, touch execution");
  expect(output).toContain("external");
});
