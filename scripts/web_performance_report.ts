import { gzipSync } from "node:zlib";
import { readdir, readFile, stat } from "node:fs/promises";
import { join, relative } from "node:path";

export type AssetMetric = {
  path: string;
  bytes: number;
  gzipBytes: number;
};

export type LighthouseSnapshot = {
  categories?: {
    performance?: { score?: number | null };
    accessibility?: { score?: number | null };
  };
  audits?: Record<string, { numericValue?: number; displayValue?: string }>;
};

export type PerformanceReport = {
  commit: string;
  assets: AssetMetric[];
  lighthouse?: LighthouseSnapshot;
};

const graphChunkPattern = /3d-force-graph/i;

async function assetFiles(root: string, directory = root): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await assetFiles(root, path)));
    else if (entry.isFile()) files.push(relative(root, path));
  }
  return files.sort();
}

export async function collectAssets(distDirectory: string): Promise<AssetMetric[]> {
  const assetsDirectory = join(distDirectory, "assets");
  const files = await assetFiles(assetsDirectory);
  return Promise.all(
    files.map(async (path) => {
      const bytes = await readFile(join(assetsDirectory, path));
      return {
        path,
        bytes: bytes.byteLength,
        gzipBytes: gzipSync(bytes).byteLength,
      };
    }),
  );
}

function bytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(2)} KiB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MiB`;
}

function score(value: number | null | undefined) {
  return value == null ? "unavailable" : `${Math.round(value * 100)}/100`;
}

function audit(snapshot: LighthouseSnapshot | undefined, id: string) {
  const item = snapshot?.audits?.[id];
  if (!item) return "unavailable";
  return item.displayValue ?? (item.numericValue == null ? "available" : `${item.numericValue} ms`);
}

export function renderReport(report: PerformanceReport) {
  const entry = report.assets
    .filter((asset) => asset.path.endsWith(".js") && !graphChunkPattern.test(asset.path))
    .sort((left, right) => right.bytes - left.bytes)[0];
  const graph = report.assets
    .filter((asset) => graphChunkPattern.test(asset.path))
    .sort((left, right) => right.bytes - left.bytes)[0];
  const lighthouse = report.lighthouse;
  const lines = [
    "# Mathen web graph performance report",
    "",
    "This report intentionally separates repeatable local smoke measurements from representative mobile hardware evidence.",
    "",
    "## Evidence boundary",
    "",
    `- Run class: **local build measurement${lighthouse ? " + local Lighthouse smoke" : ""}**`,
    `- Source commit: **${report.commit || "not recorded"}**`,
    "- Representative mobile hardware evidence: **unavailable** (no mobile device trace was supplied).",
    "- Interpretation: asset sizes and local Lighthouse values are environment-specific smoke signals, not field-user baselines.",
    "",
    "## Build assets",
    "",
    "| Asset group | Raw | Gzip |",
    "| --- | ---: | ---: |",
    `| Initial JavaScript (largest non-graph JS asset) | ${entry ? bytes(entry.bytes) : "unavailable"} | ${entry ? bytes(entry.gzipBytes) : "unavailable"} |`,
    `| 3d-force-graph chunk | ${graph ? bytes(graph.bytes) : "unavailable"} | ${graph ? bytes(graph.gzipBytes) : "unavailable"} |`,
    "",
    "The graph runtime remains in a lazy chunk; the report does not treat its download size as initial shell cost.",
  ];
  if (lighthouse) {
    lines.push(
      "",
      "## Local Lighthouse smoke",
      "",
      "These values must come from a local preview URL and headless browser run. They are not representative mobile hardware evidence.",
      "",
      `- Performance: **${score(lighthouse.categories?.performance?.score)}**`,
      `- Accessibility: **${score(lighthouse.categories?.accessibility?.score)}**`,
      `- First Contentful Paint: **${audit(lighthouse, "first-contentful-paint")}**`,
      `- Largest Contentful Paint: **${audit(lighthouse, "largest-contentful-paint")}**`,
      `- Total Blocking Time: **${audit(lighthouse, "total-blocking-time")}**`,
    );
  } else {
    lines.push(
      "",
      "## Local Lighthouse smoke",
      "",
      "Not run. Supply `--lighthouse-json` from a local preview run to include these values; do not substitute guessed or borrowed device metrics.",
    );
  }
  lines.push(
    "",
    "## Reproduction",
    "",
    "```sh",
    "bun run build",
    "bun scripts/web_performance_report.ts --dist apps/web/dist --output docs/web-performance-report.md",
    "lighthouse http://127.0.0.1:4174/ --output=json --output-path=/tmp/opencode/mathen-lighthouse.json",
    "bun scripts/web_performance_report.ts --dist apps/web/dist --lighthouse-json=/tmp/opencode/mathen-lighthouse.json --output docs/web-performance-report.md",
    "```",
    "",
    "A mobile claim requires a separately recorded trace naming the device, browser, network profile, build, URL, and workload. This repository does not include one.",
    "",
  );
  return `${lines.join("\n")}\n`;
}

async function argument(name: string) {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
}

async function main() {
  const dist = (await argument("--dist")) ?? "apps/web/dist";
  const output = await argument("--output");
  const lighthousePath = await argument("--lighthouse-json");
  const distStats = await stat(join(dist, "assets"));
  if (!distStats.isDirectory()) throw new Error(`${dist}/assets is not a directory`);
  const lighthouse = lighthousePath
    ? (JSON.parse(await readFile(lighthousePath, "utf8")) as LighthouseSnapshot)
    : undefined;
  const report = renderReport({
    commit: process.env.MATHEN_COMMIT ?? "not recorded",
    assets: await collectAssets(dist),
    lighthouse,
  });
  if (output) await Bun.write(output, report);
  else process.stdout.write(report);
}

if (import.meta.main) await main();
