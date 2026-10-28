import assert from "node:assert/strict";
import { test } from "node:test";
import {
  accessSetCookie,
  createAccessCookie,
  InMemoryRateLimiter,
  verifyOidcAccessToken,
  verifyOidcBearerToken,
  parseCookie,
  turnstileHostname,
  verifyAccessCookie,
  verifyTurnstileToken,
} from "./access.js";

const oidcEnv = {
  APP_ENV: "test",
  AUTH0_ISSUER: "https://tenant.example.test/",
  AUTH0_AUDIENCE: "https://mathen.example.test/api",
  AUTH0_JWKS_URI: "https://tenant.example.test/.well-known/jwks.json",
  AUTH0_REQUIRED_SCOPE: "read:cards",
};

function base64Url(value: string | Uint8Array) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

async function oidcFixture(
  overrides: Record<string, unknown> = {},
  keyId = "test-key",
  jwksUri = oidcEnv.AUTH0_JWKS_URI,
) {
  const pair = await crypto.subtle.generateKey(
    {
      name: "RSASSA-PKCS1-v1_5",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"],
  );
  const jwk = {
    ...(await crypto.subtle.exportKey("jwk", pair.publicKey)),
    kid: keyId,
    alg: "RS256",
    use: "sig",
  };
  const claims = {
    iss: oidcEnv.AUTH0_ISSUER,
    aud: oidcEnv.AUTH0_AUDIENCE,
    exp: 1_800_000_100,
    nbf: 1_700_000_000,
    scope: "read:cards",
    ...overrides,
  };
  const encodedHeader = base64Url(JSON.stringify({ alg: "RS256", typ: "JWT", kid: keyId }));
  const encodedClaims = base64Url(JSON.stringify(claims));
  const signingInput = `${encodedHeader}.${encodedClaims}`;
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    pair.privateKey,
    new TextEncoder().encode(signingInput),
  );
  return {
    token: `${signingInput}.${base64Url(new Uint8Array(signature))}`,
    fetcher: async (input: RequestInfo | URL) => {
      assert.equal(String(input), jwksUri);
      return Response.json({ keys: [jwk] });
    },
  };
}

const env = {
  APP_ENV: "test",
  TURNSTILE_SECRET_KEY: "test-secret",
  TURNSTILE_SITE_KEY: "test-site-key",
  TURNSTILE_HOSTNAME: "mathen.example.test",
  TURNSTILE_SESSION_TTL_SECONDS: "600",
};

test("Turnstile verification requires the Mathen action", async () => {
  const requests: Request[] = [];
  const fetcher = async (input: RequestInfo | URL, init?: RequestInit) => {
    requests.push(new Request(input, init));
    return Response.json({
      success: true,
      action: "mathen-access",
      hostname: "mathen.example.test",
    });
  };

  assert.equal(await verifyTurnstileToken("token", "secret", fetcher, "mathen.example.test"), true);
  assert.equal(requests[0]?.method, "POST");
  assert.equal(await requests[0]?.clone().text(), "secret=secret&response=token");
  assert.equal(
    await verifyTurnstileToken(
      "token",
      "secret",
      async () =>
        Response.json({
          success: true,
          action: "mathen-access",
          hostname: "other.example",
        }),
      "mathen.example.test",
    ),
    false,
  );
});

test("Turnstile hostname follows the request unless explicitly pinned", () => {
  for (const url of [
    "https://preview.example.test/api/access/turnstile",
    "https://preview.example.workers.dev/api/access/turnstile",
    "http://localhost:8787/api/access/turnstile",
  ]) {
    const request = new Request(url, {
      headers: { "X-Forwarded-Host": "other.test" },
    });
    assert.equal(turnstileHostname({ APP_ENV: "test" }, request), new URL(url).hostname);
    assert.equal(
      turnstileHostname({ APP_ENV: "test", TURNSTILE_HOSTNAME: " " }, request),
      new URL(url).hostname,
    );
    assert.equal(
      turnstileHostname({ APP_ENV: "test", TURNSTILE_HOSTNAME: " pinned.example.test " }, request),
      "pinned.example.test",
    );
  }
});

test("access cookies are signed, expiring, and tamper-resistant", async () => {
  const now = 1_700_000_000_000;
  const cookie = await createAccessCookie(env, now);
  assert.equal(await verifyAccessCookie(cookie.value, env, now + 599_000), true);
  assert.equal(await verifyAccessCookie(cookie.value, env, now + 601_000), false);
  assert.equal(await verifyAccessCookie(`${cookie.value}x`, env, now), false);
  const header = accessSetCookie(cookie.value, cookie.maxAge, true);
  assert.equal(parseCookie(header, "mathen_access"), cookie.value);
  assert.match(header, /HttpOnly/);
  assert.match(header, /Secure/);
});

test("in-memory rate limiter returns a retry window", () => {
  const limiter = new InMemoryRateLimiter();
  assert.deepEqual(limiter.consume("ip", 1, 1_000, 0), { allowed: true });
  assert.deepEqual(limiter.consume("ip", 1, 1_000, 100), {
    allowed: false,
    retryAfterSeconds: 1,
  });
  assert.deepEqual(limiter.consume("ip", 1, 1_000, 1_000), { allowed: true });
});

test("OIDC access tokens validate offline against a bounded synthetic JWKS", async () => {
  const fixture = await oidcFixture();
  assert.equal(
    await verifyOidcAccessToken(fixture.token, oidcEnv, fixture.fetcher, 1_700_000_001_000),
    true,
  );
  assert.equal(
    await verifyOidcAccessToken(
      fixture.token,
      { ...oidcEnv, AUTH0_AUDIENCE: "wrong-audience" },
      fixture.fetcher,
      1_700_000_001_000,
    ),
    false,
  );
  const noScope = await oidcFixture({ scope: "other" });
  assert.equal(
    await verifyOidcAccessToken(noScope.token, oidcEnv, noScope.fetcher, 1_700_000_001_000),
    false,
  );
  const permission = await oidcFixture(
    { permissions: ["read:cards"] },
    "permissions-key",
    "https://tenant.example.test/permissions-jwks.json",
  );
  assert.equal(
    await verifyOidcAccessToken(
      permission.token,
      {
        ...oidcEnv,
        AUTH0_JWKS_URI: "https://tenant.example.test/permissions-jwks.json",
        AUTH0_REQUIRED_SCOPE: "read:cards",
      },
      permission.fetcher,
      1_700_000_001_000,
    ),
    true,
  );
  assert.equal(
    await verifyOidcBearerToken(
      new Request("https://example.test", {
        headers: { Authorization: `Bearer ${fixture.token}` },
      }),
      oidcEnv,
      fixture.fetcher,
      1_700_000_001_000,
    ),
    true,
  );
});

test("OIDC validation rejects expired, not-yet-valid, wrong-algorithm, and oversized tokens", async () => {
  const fixture = await oidcFixture();
  assert.equal(
    await verifyOidcAccessToken(fixture.token, oidcEnv, fixture.fetcher, 1_800_000_100_000),
    false,
  );
  const future = await oidcFixture({ nbf: 1_800_000_101 });
  assert.equal(
    await verifyOidcAccessToken(future.token, oidcEnv, future.fetcher, 1_800_000_100_000),
    false,
  );
  const parts = fixture.token.split(".");
  const badHeader = `${base64Url(JSON.stringify({ alg: "HS256", kid: "test-key" }))}.${parts[1]}.${parts[2]}`;
  assert.equal(
    await verifyOidcAccessToken(badHeader, oidcEnv, fixture.fetcher, 1_700_000_001_000),
    false,
  );
  assert.equal(
    await verifyOidcAccessToken(`${fixture.token}${"x".repeat(16_384)}`, oidcEnv, fixture.fetcher),
    false,
  );
});
