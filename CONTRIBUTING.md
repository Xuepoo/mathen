# Contributing to Mathen

## Process

All non-trivial changes follow this sequence:

```text
Issue → Branch → Commit → Pull Request → Review → Merge
```

Use an existing issue label or add a clear label before implementation. Start
branches from `main` using a descriptive name such as:

```text
feature/S2M-0001-d1-api
fix/S2M-0002-card-validation
docs/S2M-0003-hosting-guide
```

CarryCtx task references use the configured `carryctx/{task_id}-{slug}` branch
template when worktrees are used.

## Commit messages

Commits must follow Conventional Commits, for example:

```text
feat(api): add feature search endpoint
fix(cards): reject unknown evidence references
docs(hosting): describe the D1 and Vectorize boundary
```

Lefthook runs local checks before commits and pushes. The same checks run in
GitHub Actions.

## Pull requests

- Link an issue and state the acceptance criteria.
- Explain schema, migration, API, or deployment impact.
- Include evidence for new architecture claims.
- Keep unreviewed LLM-generated cards out of the canonical dataset.
- Wait for CI and human review before merging.
