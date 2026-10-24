import { expect, test } from "bun:test";
import { renderReport, type PerformanceReport } from "./web_performance_report";

const report: PerformanceReport = {
  commit: "abc1234",
  assets: [
    { path: "main.js", bytes: 1000, gzipBytes: 500 },
    { path: "3d-force-graph-abc.js", bytes: 3000, gzipBytes: 1500 },
  ],
};

test("reports local smoke assets without inventing mobile evidence", () => {
  const output = renderReport(report);
  expect(output).toContain("Run class: **local build measurement**");
  expect(output).toContain("Representative mobile hardware evidence: **unavailable**");
  expect(output).toContain("Initial JavaScript (largest non-graph JS asset)");
  expect(output).toContain("3d-force-graph chunk");
  expect(output).toContain("Lighthouse smoke");
  expect(output).toContain("Not run");
});

test("includes Lighthouse values only when supplied as local smoke input", () => {
  const output = renderReport({
    ...report,
    lighthouse: {
      categories: { performance: { score: 0.91 }, accessibility: { score: 1 } },
      audits: {
        "first-contentful-paint": { displayValue: "1.1 s" },
        "largest-contentful-paint": { displayValue: "1.3 s" },
        "total-blocking-time": { displayValue: "0 ms" },
      },
    },
  });
  expect(output).toContain("local build measurement + local Lighthouse smoke");
  expect(output).toContain("Performance: **91/100**");
  expect(output).toContain("First Contentful Paint: **1.1 s**");
  expect(output).toContain("not representative mobile hardware evidence");
});
