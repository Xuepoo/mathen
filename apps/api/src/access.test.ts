import assert from "node:assert/strict";
import { test } from "node:test";
import {
  accessSetCookie,
  createAccessCookie,
  InMemoryRateLimiter,
  parseCookie,
  verifyAccessCookie,
  verifyTurnstileToken,
} from "./access.js";

const env = {
  APP_ENV: "test",
  TURNSTILE_SECRET_KEY: "test-secret",
  TURNSTILE_SITE_KEY: "test-site-key",
  TURNSTILE_HOSTNAME: "mathen.xuepoo.xyz",
  TURNSTILE_SESSION_TTL_SECONDS: "600",
};

test("Turnstile verification requires the Mathen action", async () => {
  const requests: Request[] = [];
  const fetcher = async (input: RequestInfo | URL, init?: RequestInit) => {
    requests.push(new Request(input, init));
    return Response.json({
      success: true,
      action: "mathen-access",
      hostname: "mathen.xuepoo.xyz",
    });
  };

  assert.equal(
    await verifyTurnstileToken("token", "secret", fetcher, "mathen.xuepoo.xyz"),
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
      "mathen.xuepoo.xyz",
    ),
    false,
  );
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
