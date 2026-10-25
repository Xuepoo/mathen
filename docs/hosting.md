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
cards. The current Worker has no Vectorize binding or semantic retrieval route.

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
https://mathen.example.com/api/mcp
```

The Worker exposes a stateless, reviewed-only `POST /api/mcp` endpoint. It requires
the `API_ACCESS_TOKEN` Bearer credential and supports JSON MCP requests for
`initialize`, `tools/list`, and `tools/call`. It has no session state and never
exposes filesystem-only drafts. The local stdio server remains available for
offline use. Requests with an `Origin` header must match `MCP_ALLOWED_ORIGINS`;
the endpoint returns CORS headers only for an allowed origin. `OPTIONS` is
available for the same allowlist. Authentication is exact Bearer-token matching;
do not put the token in source, URLs, browser bundles, or cards.

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
