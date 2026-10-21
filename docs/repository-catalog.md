# Repository Catalog

Mathen uses a representative repository catalog to build comparable analysis
evidence across architecture families. The catalog is not a ranking of the
projects and does not claim that structural similarity proves influence or
originality.

## Families

| Family | Repositories | Questions |
| --- | --- | --- |
| Version control | Git | How do immutable objects and mutable references interact? |
| Databases | SQLite, PostgreSQL, DuckDB | How do deployment and execution models change storage and query behavior? |
| Data services | Redis, Elasticsearch | How do memory-oriented and inverted-index state models serve queries? |
| Distributed systems | Kafka, Hadoop | How are logs, partitions, storage, and computation coordinated? |
| Control and isolation | Kubernetes, Docker, Linux | How are desired state, containers, and host resources modeled? |
| Virtualization | QEMU, Firecracker | Which isolation and device-model boundaries are retained or removed? |
| Network services | NGINX | How does event-driven I/O organize high-concurrency connections? |
| Compilation | LLVM | How are language-independent intermediate representations composed with passes? |
| Media processing | FFmpeg | How are codecs, filters, and streaming pipelines composed? |
| Backend platforms | Supabase | How are mature database and service primitives assembled into a product boundary? |

## Analysis policy

- Clone only a shallow checkout into the ignored local cache.
- Record the requested ref and resolved commit before extracting facts.
- Keep source repositories out of the Mathen Git history.
- Generate draft cards under `data/drafts/`; only reviewed cards belong under
  `data/systems/`.
- Use the `priority` field to process the core set before the extended set.
- Treat repository metrics as evidence for further analysis, not as semantic
  proof of architecture.

## Command

Run a bounded batch first, then expand by removing `--limit` after the cache
and network path have been verified:

```bash
uv run mathen analyze data/repositories/representative.json \
  --cache-dir /tmp/mathen/repos \
  --output-dir data/drafts \
  --priority core \
  --transport archive \
  --continue-on-error \
  --limit 5
```

Use `--refresh` explicitly to update an existing checkout. If a remote clone
fails in `auto` mode, the analyzer tries the GitHub source archive. The
`--continue-on-error` option records failures in `data/analyses/failures.json`
and continues the batch. Retrying with the same cache is safe once the network
is available.

Archive mode resolves the requested branch through the GitHub API, downloads a
tarball at the resolved commit, and records `github-archive` provenance in the
analysis report. It is a source-tree inspection fallback; it does not preserve
Git history or replace a full Git checkout for history-sensitive analysis.
Interrupted HTTP transfers are retried a bounded number of times. A repository
that still fails is recorded in `data/analyses/failures.json` when
`--continue-on-error` is enabled, so later successful repositories are not
discarded.

The generated cards are intentionally conservative. They currently establish
reproducible repository evidence and prioritize paths for the next semantic
stage; they are not final claims about the system's runtime architecture.
