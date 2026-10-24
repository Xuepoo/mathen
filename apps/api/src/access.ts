const SITEVERIFY_URL =
  "https://challenges.cloudflare.com/turnstile/v0/siteverify";
const ACCESS_COOKIE = "mathen_access";
const DEFAULT_SESSION_TTL_SECONDS = 60 * 60;
export type SiteverifyFetcher = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export type AccessEnvironment = {
  APP_ENV: string;
  TURNSTILE_SECRET_KEY?: string;
  TURNSTILE_SITE_KEY?: string;
  TURNSTILE_HOSTNAME?: string;
  TURNSTILE_SESSION_TTL_SECONDS?: string;
  API_ACCESS_TOKEN?: string;
};

export type RateLimitResult =
  { allowed: true } | { allowed: false; retryAfterSeconds: number };

export class InMemoryRateLimiter {
  private readonly buckets = new Map<
    string,
    { count: number; resetAt: number }
  >();

  consume(
    key: string,
    limit: number,
    windowMs: number,
    now = Date.now(),
  ): RateLimitResult {
    if (this.buckets.size > 10_000) {
      for (const [bucketKey, bucket] of this.buckets) {
        if (bucket.resetAt <= now) this.buckets.delete(bucketKey);
      }
    }
    const current = this.buckets.get(key);
    if (!current || current.resetAt <= now) {
      this.buckets.set(key, { count: 1, resetAt: now + windowMs });
      return { allowed: true };
    }
    if (current.count >= limit) {
      return {
        allowed: false,
        retryAfterSeconds: Math.max(
          1,
          Math.ceil((current.resetAt - now) / 1000),
        ),
      };
    }
    current.count += 1;
    return { allowed: true };
  }
}

export function accessProtectionEnabled(env: AccessEnvironment) {
  return Boolean(env.TURNSTILE_SECRET_KEY && env.TURNSTILE_SITE_KEY);
}

export function accessCookieName() {
  return ACCESS_COOKIE;
}

export function accessSiteKey(env: AccessEnvironment) {
  return env.TURNSTILE_SITE_KEY ?? null;
}

export async function verifyTurnstileToken(
  token: string,
  secret: string,
  fetcher: SiteverifyFetcher = fetch,
  expectedHostname?: string,
) {
  const body = new URLSearchParams({
    secret,
    response: token,
  });
  const response = await fetcher(SITEVERIFY_URL, {
    method: "POST",
    body,
  });
  if (!response.ok) return false;
  const result = (await response.json()) as {
    success?: unknown;
    action?: unknown;
    hostname?: unknown;
  };
  return (
    result.success === true &&
    result.action === "mathen-access" &&
    (!expectedHostname || result.hostname === expectedHostname)
  );
}

export function turnstileHostname(env: AccessEnvironment, request: Request) {
  return env.TURNSTILE_HOSTNAME?.trim() || new URL(request.url).hostname;
}

export function hasServiceToken(request: Request, env: AccessEnvironment) {
  const expected = env.API_ACCESS_TOKEN?.trim();
  if (!expected) return false;
  const authorization = request.headers.get("Authorization")?.trim();
  return authorization === `Bearer ${expected}`;
}

export async function createAccessCookie(
  env: AccessEnvironment,
  now = Date.now(),
) {
  const expiresAt = Math.floor(now / 1000) + sessionTtlSeconds(env);
  const payload = String(expiresAt);
  const signature = await sign(payload, env.TURNSTILE_SECRET_KEY ?? "");
  return {
    value: `${base64UrlEncode(payload)}.${base64UrlEncode(signature)}`,
    maxAge: sessionTtlSeconds(env),
  };
}

export async function verifyAccessCookie(
  value: string | undefined,
  env: AccessEnvironment,
  now = Date.now(),
) {
  if (!value || !env.TURNSTILE_SECRET_KEY) return false;
  const [encodedExpiry, encodedSignature] = value.split(".");
  if (!encodedExpiry || !encodedSignature) return false;
  const payload = base64UrlDecodeText(encodedExpiry);
  const signature = base64UrlDecodeBytes(encodedSignature);
  if (!payload || !signature || !/^\d+$/.test(payload)) return false;
  const expiresAt = Number(payload);
  if (!Number.isSafeInteger(expiresAt) || expiresAt <= Math.floor(now / 1000)) {
    return false;
  }
  const expected = await sign(payload, env.TURNSTILE_SECRET_KEY);
  return constantTimeEqual(signature, expected);
}

export function sessionTtlSeconds(env: AccessEnvironment) {
  const value = Number.parseInt(env.TURNSTILE_SESSION_TTL_SECONDS ?? "", 10);
  return Number.isSafeInteger(value) && value >= 300 && value <= 86_400
    ? value
    : DEFAULT_SESSION_TTL_SECONDS;
}

export function parseCookie(header: string | null, name = ACCESS_COOKIE) {
  if (!header) return undefined;
  for (const part of header.split(";")) {
    const separator = part.indexOf("=");
    if (separator < 0) continue;
    if (part.slice(0, separator).trim() === name) {
      return part.slice(separator + 1).trim();
    }
  }
  return undefined;
}

export function accessSetCookie(
  value: string,
  maxAge: number,
  secure: boolean,
) {
  return `${ACCESS_COOKIE}=${value}; Max-Age=${maxAge}; Path=/; HttpOnly; SameSite=Lax${secure ? "; Secure" : ""}`;
}

async function sign(payload: string, secret: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(payload),
  );
  return new Uint8Array(signature);
}

function constantTimeEqual(left: Uint8Array, right: Uint8Array) {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left[index]! ^ right[index]!;
  }
  return difference === 0;
}

function base64UrlEncode(value: string): string;
function base64UrlEncode(value: Uint8Array): string;
function base64UrlEncode(value: string | Uint8Array) {
  const bytes =
    typeof value === "string" ? new TextEncoder().encode(value) : value;
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

function base64UrlDecodeBytes(value: string) {
  try {
    const binary = atob(value.replaceAll("-", "+").replaceAll("_", "/"));
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
  } catch {
    return undefined;
  }
}

function base64UrlDecodeText(value: string) {
  const bytes = base64UrlDecodeBytes(value);
  return bytes ? new TextDecoder().decode(bytes) : "";
}
