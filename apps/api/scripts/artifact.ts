import { readFile } from "node:fs/promises";
import { basename } from "node:path";

const [key, file] = process.argv.slice(2);
const normalizedKey = key?.trim();
if (
  !normalizedKey ||
  !file ||
  normalizedKey.startsWith("/") ||
  normalizedKey.endsWith("/") ||
  normalizedKey.includes("\\") ||
  normalizedKey.split("/").some((part) => !part || part === "." || part === "..")
) {
  console.error("usage: bun run scripts/artifact.ts KEY FILE");
  process.exit(2);
}

const contentType = file.toLowerCase().endsWith(".json")
  ? "application/json"
  : "application/octet-stream";
await readFile(file);
const result = Bun.spawnSync(
  [
    "bun",
    "run",
    "wrangler",
    "r2",
    "object",
    "put",
    `mathen-artifacts-production/${normalizedKey}`,
    "--file",
    file,
    "--content-type",
    contentType,
    "--cache-control",
    "public, max-age=31536000, immutable",
    "-y",
    "--remote",
  ],
  { stdout: "inherit", stderr: "inherit" },
);
if (result.exitCode !== 0) process.exit(result.exitCode);
console.log(`Uploaded ${basename(file)} to ${normalizedKey}`);
process.exit(result.exitCode);
