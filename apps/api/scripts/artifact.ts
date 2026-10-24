import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { join } from "node:path";

const CLOUDFLARE_API = "https://api.cloudflare.com/client/v4";
const PRODUCTION_BUCKET = "mathen-artifacts-production";
const PREVIEW_BUCKET = "mathen-artifacts-preview";

export type ArtifactObject = {
  key: string;
  last_modified?: string;
  size?: number;
  etag?: string;
};

export type ArtifactRunner = (args: string[]) => Promise<void>;
export type ArtifactFetcher = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export function normalizeRelease(value: string | undefined): string {
  const release = value?.trim() ?? "";
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(release)) {
    throw new Error("release must be 1-64 safe path characters");
  }
  return release;
}

export function normalizeArtifactKey(release: string, key: string): string {
  const normalizedRelease = normalizeRelease(release);
  const normalizedKey = key.trim();
  if (
    !normalizedKey ||
    normalizedKey.startsWith("/") ||
    normalizedKey.endsWith("/") ||
    normalizedKey.includes("\\") ||
    /%(?:2e|2f|5c)/i.test(normalizedKey) ||
    normalizedKey
      .split("/")
      .some((part) => !part || part === "." || part === "..")
  ) {
    throw new Error("artifact key must be a relative path without traversal");
  }
  return `releases/${normalizedRelease}/${normalizedKey}`;
}

export function artifactBucket(
  env: Record<string, string | undefined> = process.env,
): string {
  if (env.R2_ARTIFACT_BUCKET?.trim()) return env.R2_ARTIFACT_BUCKET.trim();
  if (env.APP_ENV === "preview" || env.WRANGLER_ENV === "preview") {
    return env.R2_BUCKET_PREVIEW?.trim() || PREVIEW_BUCKET;
  }
  return env.R2_BUCKET_PRODUCTION?.trim() || PRODUCTION_BUCKET;
}

export function artifactPrefix(release: string): string {
  return `releases/${normalizeRelease(release)}/`;
}

export function normalizeArtifactPrefix(value: string): string {
  const prefix = value.trim();
  const releaseParts = prefix.split("/").slice(1, -1);
  if (
    !prefix.startsWith("releases/") ||
    !prefix.endsWith("/") ||
    prefix.includes("\\") ||
    /%(?:2e|2f|5c)/i.test(prefix) ||
    releaseParts.some((part) => !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(part))
  ) {
    throw new Error("artifact prefix must stay within the releases/ namespace");
  }
  return prefix;
}

export function sha256(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

export async function uploadArtifact(options: {
  bucket: string;
  release: string;
  key: string;
  file: string;
  verify?: boolean;
  runner?: ArtifactRunner;
  readback?: (bucket: string, key: string) => Promise<Uint8Array>;
}) {
  const objectKey = normalizeArtifactKey(options.release, options.key);
  const content = await readFile(options.file);
  const runner = options.runner ?? runWrangler;
  await runner([
    "r2",
    "object",
    "put",
    `${options.bucket}/${objectKey}`,
    "--file",
    options.file,
    "--content-type",
    options.file.toLowerCase().endsWith(".json")
      ? "application/json"
      : "application/octet-stream",
    "--cache-control",
    "public, max-age=31536000, immutable",
    "--force",
    "--remote",
  ]);
  if (options.verify) {
    if (!options.readback)
      throw new Error("--verify requires a readback function");
    const actual = await options.readback(options.bucket, objectKey);
    if (sha256(content) !== sha256(actual)) {
      throw new Error(`readback verification failed for ${objectKey}`);
    }
  }
  return { bucket: options.bucket, key: objectKey, bytes: content.byteLength };
}

export async function listArtifacts(
  options: {
    accountId: string;
    token: string;
    bucket: string;
    prefix?: string;
  },
  fetcher: ArtifactFetcher = fetch,
): Promise<ArtifactObject[]> {
  const objects: ArtifactObject[] = [];
  let cursor: string | undefined;
  do {
    const url = new URL(
      `${CLOUDFLARE_API}/accounts/${encodeURIComponent(options.accountId)}/r2/buckets/${encodeURIComponent(options.bucket)}/objects`,
    );
    url.searchParams.set("per_page", "1000");
    if (options.prefix) url.searchParams.set("prefix", options.prefix);
    if (cursor) url.searchParams.set("cursor", cursor);
    const response = await fetcher(url, {
      headers: { Authorization: `Bearer ${options.token}` },
    });
    const body = (await response.json()) as {
      success?: boolean;
      result?: ArtifactObject[];
      result_info?: { cursor?: string; is_truncated?: boolean };
    };
    if (!response.ok || body.success !== true || !Array.isArray(body.result)) {
      throw new Error(`R2 list failed: ${response.status}`);
    }
    objects.push(...body.result);
    cursor = body.result_info?.is_truncated
      ? body.result_info.cursor
      : undefined;
  } while (cursor);
  return objects;
}

export async function pruneArtifacts(
  options: {
    accountId: string;
    token: string;
    bucket: string;
    release: string;
    retentionDays: number;
    dryRun?: boolean;
    yes?: boolean;
  },
  fetcher: ArtifactFetcher = fetch,
) {
  if (!Number.isInteger(options.retentionDays) || options.retentionDays < 1) {
    throw new Error("retention days must be a positive integer");
  }
  if (!options.dryRun && !options.yes) {
    throw new Error("prune requires --dry-run or --yes");
  }
  const objects = await listArtifacts(
    { ...options, prefix: artifactPrefix(options.release) },
    fetcher,
  );
  const cutoff = Date.now() - options.retentionDays * 86_400_000;
  const stale = objects.filter(
    (object) =>
      object.last_modified && Date.parse(object.last_modified) < cutoff,
  );
  if (options.dryRun) return stale;
  for (const object of stale) {
    const prefix = artifactPrefix(options.release);
    if (!object.key.startsWith(prefix)) {
      throw new Error(
        `refusing to delete artifact outside ${prefix}: ${object.key}`,
      );
    }
    const url = `${CLOUDFLARE_API}/accounts/${encodeURIComponent(options.accountId)}/r2/buckets/${encodeURIComponent(options.bucket)}/objects/${object.key.split("/").map(encodeURIComponent).join("/")}`;
    const response = await fetcher(url, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${options.token}` },
    });
    if (!response.ok)
      throw new Error(`R2 delete failed for ${object.key}: ${response.status}`);
  }
  return stale;
}

async function runWrangler(args: string[]): Promise<void> {
  const result = Bun.spawnSync(["wrangler", ...args], {
    stdout: "inherit",
    stderr: "inherit",
  });
  if (result.exitCode !== 0)
    throw new Error(`wrangler exited with ${result.exitCode}`);
}

function option(args: string[], name: string): string | undefined {
  const index = args.indexOf(name);
  return index < 0 ? undefined : args[index + 1];
}

function has(args: string[], name: string): boolean {
  return args.includes(name);
}

async function main(args: string[]) {
  const command = args[0] ?? "put";
  const bucket = option(args, "--bucket") ?? artifactBucket();
  if (command === "put") {
    const release = option(args, "--release");
    const key = option(args, "--key");
    const file = option(args, "--file");
    if (!release || !key || !file) {
      throw new Error(
        "usage: artifact.ts put --release RELEASE --key KEY --file FILE [--verify]",
      );
    }
    await uploadArtifact({
      bucket,
      release,
      key,
      file,
      verify: has(args, "--verify"),
      readback: async (readBucket, readKey) => {
        const directory = await mkdtemp("/tmp/opencode/mathen-artifact-");
        const output = join(directory, "object.bin");
        try {
          await runWrangler([
            "r2",
            "object",
            "get",
            `${readBucket}/${readKey}`,
            "--file",
            output,
            "--remote",
          ]);
          return await readFile(output);
        } finally {
          await rm(directory, { recursive: true, force: true });
        }
      },
    });
    console.log(
      `Uploaded ${file} to ${bucket}/${normalizeArtifactKey(release, key)}`,
    );
    return;
  }
  const accountId = process.env.CLOUDFLARE_ACCOUNT_ID?.trim();
  const token = (
    process.env.CLOUDFLARE_API_TOKEN ?? process.env.CLOUDFLARE_API_KEY
  )?.trim();
  if (!accountId || !token)
    throw new Error("list/prune require Cloudflare account credentials");
  if (command === "list") {
    const release = option(args, "--release");
    const explicitPrefix = option(args, "--prefix");
    if (release && explicitPrefix)
      throw new Error("list accepts --release or --prefix, not both");
    console.log(
      JSON.stringify(
        await listArtifacts({
          accountId,
          token,
          bucket,
          prefix: release
            ? artifactPrefix(release)
            : explicitPrefix
              ? normalizeArtifactPrefix(explicitPrefix)
              : "releases/",
        }),
        null,
        2,
      ),
    );
    return;
  }
  if (command === "prune") {
    const release = option(args, "--release");
    const retentionDays = Number(option(args, "--retention-days"));
    if (!release || !Number.isInteger(retentionDays))
      throw new Error(
        "usage: artifact.ts prune --release RELEASE --retention-days DAYS --dry-run|--yes",
      );
    console.log(
      JSON.stringify(
        await pruneArtifacts({
          accountId,
          token,
          bucket,
          release,
          retentionDays,
          dryRun: has(args, "--dry-run"),
          yes: has(args, "--yes"),
        }),
        null,
        2,
      ),
    );
    return;
  }
  throw new Error(`unknown artifact command: ${command}`);
}

if (import.meta.main) {
  main(process.argv.slice(2)).catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(2);
  });
}
