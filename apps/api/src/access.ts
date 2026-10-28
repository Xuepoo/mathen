const SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";
const ACCESS_COOKIE = "mathen_access";
const DEFAULT_SESSION_TTL_SECONDS = 60 * 60;
const OIDC_JWKS_CACHE_TTL_MS = 5 * 60 * 1_000;
const OIDC_JWKS_REFRESH_INTERVAL_MS = 30 * 1_000;
const OIDC_JWKS_FETCH_TIMEOUT_MS = 5_000;
const OIDC_JWKS_CACHE_MAX_ENTRIES = 8;
const OIDC_JWKS_MAX_BYTES = 64 * 1024;
const OIDC_JWKS_MAX_KEYS = 32;
const OIDC_MAX_TOKEN_BYTES = 16 * 1024;
export type SiteverifyFetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
export type OidcFetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export type AccessEnvironment = {
  APP_ENV: string;
  TURNSTILE_SECRET_KEY?: string;
  TURNSTILE_SITE_KEY?: string;
  TURNSTILE_HOSTNAME?: string;
  TURNSTILE_SESSION_TTL_SECONDS?: string;
  API_ACCESS_TOKEN?: string;
  AUTH0_ISSUER?: string;
  AUTH0_AUDIENCE?: string;
  AUTH0_JWKS_URI?: string;
  AUTH0_REQUIRED_SCOPE?: string;
  API_RATE_LIMIT_PER_MINUTE?: string;
  API_RATE_LIMIT_WINDOW_SECONDS?: string;
};

type CachedJwks = { expiresAt: number; refreshAfter: number; keys: Map<string, JsonWebKey> };

const oidcJwksCache = new Map<string, CachedJwks>();

export type RateLimitResult = { allowed: true } | { allowed: false; retryAfterSeconds: number };

export class InMemoryRateLimiter {
  private readonly buckets = new Map<string, { count: number; resetAt: number }>();

  consume(key: string, limit: number, windowMs: number, now = Date.now()): RateLimitResult {
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
        retryAfterSeconds: Math.max(1, Math.ceil((current.resetAt - now) / 1000)),
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

export function oidcAuthenticationConfigured(env: AccessEnvironment) {
  return Boolean(oidcIssuer(env) && env.AUTH0_AUDIENCE?.trim());
}

export function oidcIssuer(env: AccessEnvironment) {
  const issuer = env.AUTH0_ISSUER?.trim();
  if (!issuer) return undefined;
  try {
    return new URL(issuer).protocol === "https:" ? issuer : undefined;
  } catch {
    return undefined;
  }
}

export function oidcJwksUri(env: AccessEnvironment) {
  const configured = env.AUTH0_JWKS_URI?.trim();
  const fallback = oidcIssuer(env);
  const uri =
    configured || (fallback ? `${fallback.replace(/\/$/, "")}/.well-known/jwks.json` : undefined);
  if (!uri) return undefined;
  try {
    const url = new URL(uri);
    return url.protocol === "https:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

export function oidcRequiredScopes(env: AccessEnvironment) {
  return (env.AUTH0_REQUIRED_SCOPE ?? "").trim().split(/\s+/).filter(Boolean);
}

export async function verifyOidcBearerToken(
  request: Request,
  env: AccessEnvironment,
  fetcher: OidcFetcher = fetch,
  now = Date.now(),
) {
  if (!oidcAuthenticationConfigured(env)) return false;
  const authorization = request.headers.get("Authorization")?.trim() ?? "";
  const match = /^Bearer\s+(\S+)$/i.exec(authorization);
  return match ? verifyOidcAccessToken(match[1]!, env, fetcher, now) : false;
}

export async function verifyOidcAccessToken(
  token: string,
  env: AccessEnvironment,
  fetcher: OidcFetcher = fetch,
  now = Date.now(),
) {
  if (!oidcAuthenticationConfigured(env) || token.length > OIDC_MAX_TOKEN_BYTES) return false;
  const parts = token.split(".");
  if (parts.length !== 3 || parts.some((part) => !part)) return false;

  const header = decodeJson(parts[0]!);
  const claims = decodeJson(parts[1]!);
  const signature = base64UrlDecodeBytes(parts[2]!);
  if (!isRecord(header) || !isRecord(claims) || !signature) return false;
  if (header.alg !== "RS256" || typeof header.kid !== "string" || !header.kid) return false;

  const issuer = oidcIssuer(env);
  const audience = env.AUTH0_AUDIENCE?.trim();
  if (!issuer || !audience || claims.iss !== issuer || !hasAudience(claims.aud, audience)) {
    return false;
  }
  if (typeof claims.exp !== "number" || !Number.isFinite(claims.exp)) return false;
  const nowSeconds = Math.floor(now / 1_000);
  if (claims.exp <= nowSeconds) return false;
  if (
    claims.nbf !== undefined &&
    (typeof claims.nbf !== "number" || !Number.isFinite(claims.nbf) || claims.nbf > nowSeconds)
  ) {
    return false;
  }
  if (!hasRequiredScopes(claims, oidcRequiredScopes(env))) return false;

  const jwksUri = oidcJwksUri(env);
  if (!jwksUri) return false;
  const jwk = await findJwk(jwksUri, header.kid, fetcher, now);
  if (!jwk) return false;
  try {
    const key = await crypto.subtle.importKey(
      "jwk",
      jwk,
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
      false,
      ["verify"],
    );
    return await crypto.subtle.verify(
      "RSASSA-PKCS1-v1_5",
      key,
      signature,
      new TextEncoder().encode(`${parts[0]}.${parts[1]}`),
    );
  } catch {
    return false;
  }
}

export async function createAccessCookie(env: AccessEnvironment, now = Date.now()) {
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

export function configuredRateLimit(
  value: string | undefined,
  fallback: number,
  minimum = 1,
  maximum = 10_000,
) {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isSafeInteger(parsed) && parsed >= minimum && parsed <= maximum ? parsed : fallback;
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

export function accessSetCookie(value: string, maxAge: number, secure: boolean) {
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
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
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
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
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

function decodeJson(value: string): unknown {
  try {
    const decoded = base64UrlDecodeText(value);
    return decoded ? JSON.parse(decoded) : undefined;
  } catch {
    return undefined;
  }
}

function hasAudience(value: unknown, expected: string) {
  return value === expected || (Array.isArray(value) && value.includes(expected));
}

function hasRequiredScopes(claims: Record<string, unknown>, required: string[]) {
  if (!required.length) return true;
  const scopes = new Set<string>();
  if (typeof claims.scope === "string") {
    for (const scope of claims.scope.split(/\s+/)) if (scope) scopes.add(scope);
  }
  if (Array.isArray(claims.permissions)) {
    for (const permission of claims.permissions) {
      if (typeof permission === "string") scopes.add(permission);
    }
  }
  return required.every((scope) => scopes.has(scope));
}

async function findJwk(uri: string, kid: string, fetcher: OidcFetcher, now: number) {
  const cached = oidcJwksCache.get(uri);
  if (cached && cached.expiresAt > now) {
    const key = cached.keys.get(kid);
    if (key || cached.refreshAfter > now) return key;
  }
  const keys = await fetchJwks(uri, fetcher, now);
  return keys?.get(kid);
}

async function fetchJwks(uri: string, fetcher: OidcFetcher, now: number) {
  try {
    const response = await fetcher(uri, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(OIDC_JWKS_FETCH_TIMEOUT_MS),
    });
    if (!response.ok) return undefined;
    const body = await response.text();
    if (new TextEncoder().encode(body).byteLength > OIDC_JWKS_MAX_BYTES) return undefined;
    const parsed = JSON.parse(body) as { keys?: unknown };
    if (!Array.isArray(parsed.keys) || parsed.keys.length > OIDC_JWKS_MAX_KEYS) return undefined;
    const keys = new Map<string, JsonWebKey>();
    for (const value of parsed.keys) {
      if (!isRecord(value) || typeof value.kid !== "string" || value.kty !== "RSA") continue;
      if (value.use !== undefined && value.use !== "sig") continue;
      if (value.alg !== undefined && value.alg !== "RS256") continue;
      if (typeof value.n !== "string" || typeof value.e !== "string") continue;
      keys.set(value.kid, value as JsonWebKey);
    }
    oidcJwksCache.delete(uri);
    while (oidcJwksCache.size >= OIDC_JWKS_CACHE_MAX_ENTRIES) {
      const oldest = oidcJwksCache.keys().next().value as string | undefined;
      if (!oldest) break;
      oidcJwksCache.delete(oldest);
    }
    oidcJwksCache.set(uri, {
      expiresAt: now + OIDC_JWKS_CACHE_TTL_MS,
      refreshAfter: now + OIDC_JWKS_REFRESH_INTERVAL_MS,
      keys,
    });
    return keys;
  } catch {
    return undefined;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
