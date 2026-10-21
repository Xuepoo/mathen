# Roadmap

## Phase 0: Representation and evidence

- Define the Architecture Card schema.
- Add representative cards for Git, DuckDB, Supabase, and Firecracker.
- Validate every card from the command line.
- Keep all claims linked to primary sources where possible.

## Phase 1: Semantic validation

- Check that referenced features and evidence IDs exist.
- Check that mathematical views declare questions and assumptions.
- Check that every trade-off references a feature or design decision.
- Add controlled vocabularies for model types and claim types.

## Phase 2: Assisted extraction

- Write an LLM Skill that emits only the Architecture Card format.
- Prepare fixed-commit evidence bundles and portable modeling prompts.
- Require source excerpts and confidence for every extracted claim.
- Add a review queue for unresolved or conflicting claims.
- Never allow unreviewed output to overwrite reviewed data.

## Phase 3: Cloudflare application and retrieval

- Use D1 as the canonical relational knowledge graph.
- Add Hono Worker API and a minimal Vite browser client.
- Add Vectorize as a rebuildable semantic retrieval index.
- Add queries for reusable features and compatible combinations.
- Add graph export to JSON-LD or RDF only if the simpler graph model is
  insufficient.

## Phase 4: Local repository analysis and MCP

- Analyze a local repository or a catalog entry into a draft Architecture
  Card. The first catalog covers databases, logs, orchestration, isolation,
  virtualization, networking, compilers, media, and backend platforms.
- Expose comparison and retrieval through an MCP server.
- Keep draft analysis separate from reviewed canonical cards.

## Phase 5: Architecture synthesis

- Express design goals and constraints as queries.
- Generate candidate compositions with explicit conflicts and assumptions.
- Validate candidates with prototypes, benchmarks, and failure tests.

## Non-goals for the first milestone

- Automatically proving that an implementation satisfies a mathematical model.
- Building a general-purpose graph database.
- Claiming originality from structural similarity alone.
- Operating Neo4j or Neptune before D1 query patterns demonstrate the need.
