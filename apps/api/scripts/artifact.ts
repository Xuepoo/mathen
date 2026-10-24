import { readFile } from "node:fs/promises";
import { basename } from "node:path";

const [key, file] = process.argv.slice(2);
if (!key || !file) {
  console.error("usage: bun run scripts/artifact.ts KEY FILE");
  process.exit(2);
}

const contentType = file.endsWith(".json")
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
    `mathen-artifacts-production/${key}`,
    "--file",
    file,
    "--content-type",
    contentType,
  ],
  { stdout: "inherit", stderr: "inherit" },
);
console.log(`Uploaded ${basename(file)} to ${key}`);
process.exit(result.exitCode);
