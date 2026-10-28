<!-- markdownlint-disable MD013 -->

# Hosting and Integration Boundaries

## Current deployment target

The first production target is a single Cloudflare Worker. It serves the Vite
client and Hono API from one deployment origin (for example,
`https://mathen.example.com`):

```text
Vite client
    │
    ├── Workers Static Assets
    │
    Hono Worker API (`/api/*`)
    ├── D1: canonical relational source of truth
    └── Vectorize: planned optional semantic retrieval index
```

The repository implements the following read API routes:

- `GET /api/systems` and `GET /api/systems/:id` for reviewed cards;
- `GET /api/features` for reusable feature retrieval;
- `GET /api/feature-relations` and `GET /api/compositions` for reviewed
  relations and composition proposals;
- `GET /api/modeling/:id` for fixed-commit modeling bundles.
- `GET /api/graph` and `GET /api/graph/models` for navigational projections.
- `POST /api/mcp` for the stateless, reviewed-only hosted MCP transport.

The routes are interfaces, not a guarantee that every repository artifact is
populated or exposed. Migrations create the D1 schema, and the seed workflow
loads reviewed cards and modeling bundles; a deployment that has not been
seeded can return no records. JSON Schemas, validators, fixtures, and local
benchmark manifests remain repository artifacts and do not populate D1 or make
their contents available through the API or MCP. The hosted card and MCP data
boundary is reviewed-only; the separate artifact route serves operator-uploaded
deployment artifacts. The local stdio MCP server can read the repository
filesystem for internal filesystem-mode calls; its registered tools still
return reviewed records only.

D1 is intentionally sufficient for the first knowledge graph. Systems,
features, evidence, mathematical views, trade-offs, and explicit relations are
stored as normalized tables. Recursive SQL, join tables, and API-side graph
assembly cover the initial query surface.

Vectorize is documented as a future optimization and retrieval companion. A
planned integration would store embeddings and metadata that point back to D1
records; it would not be authoritative and could be rebuilt from reviewed
cards. The current Worker has no Vectorize binding. The implemented retrieval
route is the provider-neutral `GET /api/retrieval` bounded lexical baseline;
it builds a bounded snapshot from hydrated D1 records for each request and is
not embeddings or semantic/vector similarity.

The deployment workflow expects the repository secrets
`CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_KEY`. The latter must contain a
Cloudflare API token with the required D1 and Workers permissions; the secret
name is retained for compatibility with the planned repository configuration.
The checked-in Wrangler configuration names the production R2 bucket
`mathen-artifacts-production` and the preview bucket
`mathen-artifacts-preview`, but naming a binding does not create either bucket.
The account, bucket existence, and token permissions must be verified by an
operator before a remote deployment or artifact command is run.

The deployment command builds the Vite client, applies remote D1 migrations,
and deploys the Worker:

```bash
just deploy
```

### Retrieval MVP deployment read-back (operator checklist)

This checklist prepares a release but does not itself authorize or perform a
production deployment. The retrieval MVP uses the existing Worker, D1, R2,
and Workers Static Assets resources. Do not add a Vectorize binding, provider,
secret, or remote index for this release. Record the exact Git commit/tag,
Worker deployment version, deployment timestamp, database migration result,
and operator identity in the release record; never record credentials.

Before deployment, verify the `production` GitHub environment contains the
existing account/API credentials and, when enabled, the Turnstile and
`API_ACCESS_TOKEN` values. Confirm that the custom domain binding is
`https://mathen.xuepoo.xyz`, that the alternate `workers.dev` origin is still
expected, and that the configured production R2 bucket is
`mathen-artifacts-production`. The checked-in configuration is sufficient for
the MVP; resource creation and DNS changes remain operator actions.

Run the existing workflow or its reviewed manual equivalent, in this order:

1. Build the browser asset and confirm the generated `apps/web/dist/` output is
   not staged or committed.
2. Apply the checked-in D1 migrations and read back the migration list/status
   from the target `mathen-db`; record the database ID, migration names, and
   result. Seed reviewed cards separately only when the release requires a
   refreshed canonical snapshot, because seeding replaces structured D1 data.
3. Deploy the Worker and record the exact Wrangler deployment version from the
   command output or Cloudflare dashboard. Do not describe a source commit as
   the Worker version unless the platform read-back confirms that mapping.
4. Read `GET https://mathen.xuepoo.xyz/api/health`, then query a known reviewed
   term such as:

   ```bash
   curl -fsS 'https://mathen.xuepoo.xyz/api/retrieval?q=embedded%20execution&limit=3'
   ```

   Confirm the response is a `{ "data": ... }` envelope, the index method is
   `bounded_lexical_baseline`, `score_kind` is `lexical_overlap`, provenance is
   `bounded_lexical_baseline`, and no result contains a draft path. Record the
   HTTP status, `X-Request-ID`, index ID, result count, and warnings. A ranking
   score is only an uncalibrated discovery signal; it is not embedding
   similarity, truth, compatibility, causality, or a graph edge.

5. Open the custom domain and verify the Web retrieval panel loads the deployed
   asset and still uses same-origin `/api/retrieval` requests. Record the asset
   URL/hash or deployment version; do not change a Vite API URL.
6. Verify hosted MCP at `POST https://mathen.xuepoo.xyz/api/mcp`: without the
   exact `Authorization: Bearer <API_ACCESS_TOKEN>` header it must return 401,
   and an `Origin` outside the exact `MCP_ALLOWED_ORIGINS` list must be denied.
   With the token and an allowed origin, call `tools/list` and
   `search_semantic`; confirm the result preserves the API IDs, evidence,
   scope, warnings, and bounded lexical method. Test `OPTIONS` from an allowed
   and a disallowed origin and record status, CORS headers, and request IDs.
7. Read back the D1 migration state and one seeded reviewed record after the
   Worker deployment. Confirm the route remains read-only, D1 is the canonical
   source, and no Vectorize/index/provider resource was created.

If any read-back fails, stop and record the failure and request IDs. Do not
claim that new code is deployed based only on a successful local build or
source review. The unresolved provider/model, vector index, retention policy,
and semantic retrieval deployment choices remain outside this MVP.

## Public API protection

When `TURNSTILE_SECRET_KEY` and `TURNSTILE_SITE_KEY` are configured on the
Worker, all D1-backed API routes require a short-lived, signed
`mathen_access` HttpOnly cookie issued after a successful Cloudflare Turnstile
check. The public health and access-bootstrap routes remain available so a
browser can complete the check. API clients such as the read-only MCP backend
may use the optional `API_ACCESS_TOKEN` service token instead of a browser
cookie; keep that token outside the repository.

Configure the site key as a non-secret Worker variable and the secret as a
Worker secret. `TURNSTILE_HOSTNAME` can pin verification to one deployment
hostname (for example, `mathen.example.com`). When unset or blank, verification
requires the hostname of the incoming request URL, including for local or
preview deployments; forwarded-host headers are not used. The widget
must be restricted to the matching hostname, use the `mathen-access` action,
and use the managed mode. The application also applies a per-IP in-memory request limit
and bounded per-IP request counts. These are defense-in-depth measures;
Cloudflare's edge caching can be configured separately for explicitly public
responses, while WAF/rate-limiting rules remain the
authoritative protection against distributed floods.

The repository deployment workflow reads these values from the `production`
GitHub Actions environment:

| GitHub Environment setting               | Worker destination      | Required      | Value                                                                    |
| ---------------------------------------- | ----------------------- | ------------- | ------------------------------------------------------------------------ |
| Secret `CLOUDFLARE_ACCOUNT_ID`           | Wrangler authentication | Yes           | Cloudflare account ID containing the D1 database and Turnstile widget    |
| Secret `CLOUDFLARE_API_KEY`              | Wrangler authentication | Yes           | Cloudflare API token with Workers edit and D1 migration permissions      |
| Variable `TURNSTILE_SITE_KEY`            | Worker variable         | For Turnstile | Public site key of the Mathen widget                                     |
| Secret `TURNSTILE_SECRET_KEY`            | Worker secret           | For Turnstile | Private secret of the same Mathen widget                                 |
| Variable `TURNSTILE_HOSTNAME`            | Worker variable         | Optional      | Pinned hostname; blank uses the request URL hostname                     |
| Variable `TURNSTILE_SESSION_TTL_SECONDS` | Worker variable         | Optional      | Signed browser-session lifetime, from 300 to 86400 seconds; default 3600 |
| Variable `AUTH0_ISSUER`                  | Worker variable         | Optional      | HTTPS Auth0 issuer for hosted MCP OAuth                                  |
| Variable `AUTH0_AUDIENCE`                | Worker variable         | Optional      | Exact access-token audience for hosted MCP OAuth                         |
| Variable `AUTH0_JWKS_URI`                | Worker variable         | Optional      | HTTPS JWKS URI; otherwise derived from the issuer                        |
| Variable `AUTH0_REQUIRED_SCOPE`          | Worker variable         | Optional      | Space-separated scope/permission requirements for hosted MCP OAuth       |
| Secret `API_ACCESS_TOKEN`                | Worker secret           | Optional      | Private Bearer token for the read-only MCP/API client                    |

`MCP_ALLOWED_ORIGINS` is a checked-in Wrangler variable rather than a secret.
Set it to a comma-separated allowlist of exact browser origins before allowing
browser clients; an empty value permits requests without an `Origin` header but
rejects browser origins. `MCP_RATE_LIMIT_PER_MINUTE` and
`MCP_RATE_LIMIT_WINDOW_SECONDS` control the Worker-local defense-in-depth limit.
The limiter is per Worker instance and per client IP, not a distributed abuse
control. Configure Cloudflare WAF/rate-limiting rules for distributed or
production-scale protection.

Public defaults live in `apps/api/wrangler.jsonc` under `vars`. Non-empty
GitHub Environment variables override those defaults at deployment; unset
variables do not erase Wrangler configuration. Existing installations should
move the public Turnstile settings from GitHub Secrets to Environment variables.
Keep the account credentials, Turnstile secret, and service token in Secrets.
For a manual deployment, edit the public Wrangler vars or pass explicit
`wrangler deploy --var "TURNSTILE_HOSTNAME:mathen.example.com"` overrides.

The workflow writes `TURNSTILE_SECRET_KEY` and `API_ACCESS_TOKEN` with
`wrangler secret put`; they are never committed or passed as public Worker
variables. Rotating a secret means updating the GitHub Secret and running the
deployment workflow again. Removing a GitHub Secret does not automatically
delete an already stored Worker secret; delete that secret explicitly with
`wrangler secret delete` if it must be revoked.

Until both Turnstile variables are configured, protection stays disabled so
local development and deployments do not fail closed accidentally. Do not use
a site key or secret belonging to another application or hostname.

Reviewed cards and modeling bundles are seeded separately because seeding
replaces the structured contents of the target database:

```bash
just db-seed-remote
```

The production Worker is currently available at the custom domain
`https://mathen.xuepoo.xyz`, with the Cloudflare `workers.dev` URL
`https://mathen-api.ven3428set.workers.dev` retained as an alternate origin.
The deployment does not create or modify DNS bindings; verify the custom-domain
binding in Cloudflare before publishing a new domain.

The browser always uses same-origin `/api/*` requests, so changing the custom
domain or using a `workers.dev` preview requires no browser build-time URL.
The API prefix `/api` and hosted MCP path `/api/mcp` are stable route contracts,
not deployment-specific configuration. The Vite development proxy still targets
`http://127.0.0.1:8787` by default. Configure remote clients with their deployment
origin rather than changing these paths in source.

### Public MVP usage

Open [https://mathen.xuepoo.xyz](https://mathen.xuepoo.xyz) in a browser to
explore the reviewed atlas. The browser uses same-origin requests and the
currently implemented graph/card routes. A deployment with Turnstile enabled
may show the access check before graph and card reads; complete it in the
browser rather than copying a cookie or service token into client code.

The API and hosted MCP are read-only. They expose reviewed records seeded into
D1, not drafts, prompts, or local analysis reports. D1 is the structured source
of truth. The Worker source includes bounded lexical retrieval, while a
semantic/vector index remains planned and rebuildable; verify the deployed
route and response before claiming that a hosted site serves retrieval.

## Future graph stores

If graph traversals become the dominant workload, the repository can add a
storage adapter for Neo4j on EC2 or Amazon Neptune Serverless. The canonical
Architecture Card schema and API contracts should remain independent of that
choice. Migration should be an export/import concern rather than a rewrite of
the extraction pipeline.

## Local-first verification

Run the Worker, D1 migrations, seed script, and Vite client locally before any
remote deployment:

```bash
bun install
bun run db:reset:local
bun run dev
```

The local D1 database is disposable. Seed data is derived from
`data/systems/*.json` and the fixed-commit modeling bundles under
`data/modeling/*.json`, so a fresh local or remote database can serve both
reviewed cards and modeling context.

## MCP boundary

The local MCP server can use the canonical Hono API by setting `MATHEN_API_URL`
(for example, `http://localhost:8787/api`). When unset, it uses the repository
filesystem for offline operation. The API currently serves reviewed systems,
features, and fixed-commit modeling bundles; draft cards remain filesystem-only
until an authenticated draft-review API exists.

The hosted MCP endpoint is a remote HTTPS endpoint:

```text
https://mathen.xuepoo.xyz/api/mcp
```

The Worker exposes a stateless, reviewed-only `POST /api/mcp` endpoint. It
accepts the legacy `API_ACCESS_TOKEN` Bearer credential and optionally accepts
Auth0 access tokens when `AUTH0_ISSUER` and `AUTH0_AUDIENCE` are configured.
Auth0 acceptance is restricted to `/api/mcp`; it does not bypass Turnstile,
the signed access cookie, or service-token rules for ordinary `/api/*` routes.
It supports JSON MCP requests for `initialize`, `tools/list`, and `tools/call`.
It has no session state and never exposes filesystem-only drafts. The local
stdio server remains available for offline use. Requests with an `Origin`
header must match `MCP_ALLOWED_ORIGINS`;
the endpoint returns CORS headers only for an allowed origin. `OPTIONS` is
available for the same allowlist. An `Origin` is allowed only when it exactly
matches one of the comma-separated `MCP_ALLOWED_ORIGINS` values (the current
implementation also accepts an explicit `*` value). The endpoint returns
`Access-Control-Allow-Origin` only for an allowed origin. With an empty
allowlist, requests without `Origin` are allowed but browser origins are
rejected. `OPTIONS` follows the same origin rule. Authentication is exact
Bearer-token matching for the legacy credential. Auth0 validation is RS256-only
and checks the configured issuer, audience, expiry, not-before, required
scope/permission, and a bounded HTTPS JWKS response. The protected-resource
metadata URL is `GET /api/.well-known/oauth-protected-resource`, and the MCP
challenge uses that same `/api`-prefixed URL. Do not put tokens in source,
URLs, browser bundles, or cards. This documentation does not assert that a
particular production token or MCP verification has been completed; an
operator must provision and test the Worker configuration.

Successful and failed MCP responses include an `X-Request-ID` generated by the
Worker. Retain that ID with the HTTP status, client IP/origin class, and
Cloudflare logs when investigating a request. The repository does not claim
that production log retention, alerting, or distributed rate limiting is
configured; those are deployment/operator responsibilities.

## Static asset storage boundary

The current Worker serves the Vite build through Workers Static Assets. R2 is
bound as `ARTIFACTS` to `mathen-artifacts-production` in the default production
environment and to `mathen-artifacts-preview` in the `preview` environment. The
read-only route is `/api/artifacts/<key>`. Uploads are an operator action and
must use a release namespace:

```bash
cd apps/api
bun run artifact:put --release v0.0.2 --key experiments/g5-minimal.json \
  --file ../../data/experiments/g5-minimal.json --verify
```

The helper chooses the production bucket by default. For preview operations,
set `APP_ENV=preview` or pass `R2_ARTIFACT_BUCKET=mathen-artifacts-preview`.
`artifact:list` is read-only and lists `releases/` by default. Use
`--release RELEASE` for one release or `--prefix releases/RELEASE/` for an
explicit namespace:

```bash
R2_ARTIFACT_BUCKET=mathen-artifacts-preview bun run artifact:list --release v0.0.2
```

`artifact:prune` only considers objects in the selected release and requires an
explicit retention policy plus a safety mode. Run the dry run first:

```bash
bun run artifact:prune --release v0.0.2 --retention-days 90 --dry-run
bun run artifact:prune --release v0.0.2 --retention-days 90 --yes
```

`--verify` reads the uploaded object back through Wrangler and compares SHA-256
bytes; it requires access to the selected remote bucket. The helper rejects
traversal, encoded traversal, and keys outside the `releases/<release>/`
namespace.

R2 is a deployment artifact store, not the canonical Architecture Card
database. D1 remains the canonical structured source of truth for reviewed
systems, features, evidence, and relations. R2 objects are rebuildable
release-scoped reports or experiment objects and must not be the only copy of
canonical knowledge.

## Deployment evidence boundary

This repository contains configuration, local tests, and operator commands; it
does not create R2 buckets, invoke Cloudflare production APIs, seed a remote D1
database, attach a custom domain, or claim that a Worker has been deployed.
Before declaring a deployment complete, an operator must separately record the
account, bucket bindings, migrations, secrets, deployment URL, MCP auth/origin
checks, artifact readback, and relevant Cloudflare observability evidence.

The MCP tools call the same canonical API or a shared service layer. Its first
tools can be:

- analyze a local repository into a draft Architecture Card;
- compare a draft card with known systems and features;
- retrieve evidence-backed patterns by constraints;
- report missing evidence, unsupported mathematical claims, and trade-offs.

Unreviewed local analysis must remain separate from reviewed public cards.
