# Hosting and Integration Boundaries

## Current deployment target

The first production target is Cloudflare:

```text
Vite client
    │
    ├── static deployment target (Cloudflare Pages or a future Worker asset binding)
    │
Hono Worker API
    ├── D1: canonical relational source of truth
    └── Vectorize: optional semantic retrieval index
```

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
`data/systems/*.json`, so the same reviewed cards can populate a fresh remote
database later.

## MCP boundary

A future MCP server should call the same canonical API or a shared service
layer. Its first tools can be:

- analyze a local repository into a draft Architecture Card;
- compare a draft card with known systems and features;
- retrieve evidence-backed patterns by constraints;
- report missing evidence, unsupported mathematical claims, and trade-offs.

Unreviewed local analysis must remain separate from reviewed public cards.
