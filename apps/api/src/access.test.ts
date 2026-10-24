import assert from "node:assert/strict";
import { test } from "node:test";
import {
  accessSetCookie,
  createAccessCookie,
  InMemoryRateLimiter,
  parseCookie,
  turnstileHostname,
  verifyAccessCookie,
  verifyTurnstileToken,
} from "./access.js";

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

  assert.equal(
    await verifyTurnstileToken(
      "token",
      "secret",
      fetcher,
      "mathen.example.test",
    ),
    true,
  );
  assert.equal(requests[0]?.method, "POST");
  assert.equal(
    await requests[0]?.clone().text(),
    "secret=secret&response=token",
  );
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
    assert.equal(
      turnstileHostname({ APP_ENV: "test" }, request),
      new URL(url).hostname,
    );
    assert.equal(
      turnstileHostname({ APP_ENV: "test", TURNSTILE_HOSTNAME: " " }, request),
      new URL(url).hostname,
    );
    assert.equal(
      turnstileHostname(
        { APP_ENV: "test", TURNSTILE_HOSTNAME: " pinned.example.test " },
        request,
      ),
      "pinned.example.test",
    );
  }
});

test("access cookies are signed, expiring, and tamper-resistant", async () => {
  const now = 1_700_000_000_000;
  const cookie = await createAccessCookie(env, now);
  assert.equal(
    await verifyAccessCookie(cookie.value, env, now + 599_000),
    true,
  );
  assert.equal(
    await verifyAccessCookie(cookie.value, env, now + 601_000),
    false,
  );
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
