# Hosting and Integration Boundaries

## Current deployment target

The first production target is a single Cloudflare Worker. It serves the Vite
client and Hono API from the future `mathen.xuepoo.xyz` custom domain:

```text
Vite client
    │
    ├── Workers Static Assets
    │
    Hono Worker API (`/api/*`)
    ├── D1: canonical relational source of truth
    └── Vectorize: optional semantic retrieval index
```

The current read API includes:

- `GET /api/systems` and `GET /api/systems/:id` for reviewed cards;
- `GET /api/features` for reusable feature retrieval;
- `GET /api/modeling/:id` for fixed-commit modeling bundles.

D1 is intentionally sufficient for the first knowledge graph. Systems,
features, evidence, mathematical views, trade-offs, and explicit relations are
stored as normalized tables. Recursive SQL, join tables, and API-side graph
assembly cover the initial query surface.

Vectorize is an optimization and retrieval companion. It stores embeddings and
metadata that point back to D1 records; it is not authoritative and can be
rebuilt from reviewed cards.

The deployment workflow expects the repository secrets
`CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_KEY`. The latter must contain a
Cloudflare API token with the required D1 and Workers permissions; the secret
name is retained for compatibility with the planned repository configuration.

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
Worker secret. `TURNSTILE_HOSTNAME` defaults to `mathen.xuepoo.xyz` and should
only be changed for an explicitly configured preview deployment. The widget
must be restricted to the matching hostname, use the `mathen-access` action,
and use the managed mode. The application also applies a per-IP in-memory request limit
and a short Worker Cache TTL for successful public GET responses. These are
defense-in-depth measures; Cloudflare WAF/rate-limiting rules remain the
authoritative protection against distributed floods.

Until both Turnstile variables are configured, protection stays disabled so
local development and deployments do not fail closed accidentally. Do not use
a site key or secret belonging to another application or hostname.

Reviewed cards and modeling bundles are seeded separately because seeding
replaces the structured contents of the target database:

```bash
just db-seed-remote
```

After deployment, attach the Worker custom domain `mathen.xuepoo.xyz` in
Cloudflare. The repository does not configure the custom domain until the DNS
binding is confirmed.

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

The intended hosted MCP shape is a remote HTTPS endpoint such as:

```text
https://mathen.xuepoo.xyz/mcp
```

That endpoint is a future deployment target, not a current API contract. The
current implementation is the read-only stdio server in `apps/mcp/`, optionally
backed by the Hono API through `MATHEN_API_URL`. A future remote adapter must
preserve the same reviewed-only boundary, authentication decision, tool
schemas, error contract, and draft isolation rather than exposing the local
stdio process directly over the network.

## Static asset storage boundary

The current Worker serves the Vite build through Workers Static Assets. R2 is a
possible future storage layer for versioned static assets, large reports, or
experiment artifacts, but no R2 bucket is currently bound to the Worker. When
introduced, manage it in Wrangler configuration with an explicit binding and
production/preview bucket names, keep upload and cleanup commands in the
repository, and treat the bucket as a deployment artifact store rather than
the canonical Architecture Card database. D1 remains the structured source of
truth; R2 objects must be addressable by release or artifact IDs and remain
rebuildable from repository inputs where applicable.

The MCP tools call the same canonical API or a shared service layer. Its first
tools can be:

- analyze a local repository into a draft Architecture Card;
- compare a draft card with known systems and features;
- retrieve evidence-backed patterns by constraints;
- report missing evidence, unsupported mathematical claims, and trade-offs.

Unreviewed local analysis must remain separate from reviewed public cards.
