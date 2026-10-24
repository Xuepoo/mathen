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
| Foundational languages | CPython, Rust, Lua, Go, Ruby | How do language implementations represent syntax, values, memory, and execution? |
| JavaScript and WebAssembly runtimes | Node.js, Deno, V8, Wasmtime | How do embeddable engines and host runtimes expose execution, modules, and capabilities? |
| Operating-system foundations | FreeBSD, systemd, xv6, GNU Coreutils | How do kernels, initialization, educational systems, and Unix tools expose process and resource boundaries? |
| Compiler and parser infrastructure | GCC, tree-sitter | How do front ends, syntax trees, intermediate representations, and code-generation pipelines differ? |
| Systems and networking libraries | Boost, libuv, curl, OpenSSL | How do reusable libraries package concurrency, transport, protocol, and cryptographic primitives? |
| Protocol and messaging infrastructure | Protocol Buffers, gRPC, Eclipse Mosquitto | How are schemas, RPC boundaries, and publish/subscribe delivery represented? |
| Mail and collaboration services | Stalwart Mail Server | How do SMTP transport/submission, IMAP mailbox sessions, and JMAP synchronization expose one shared mail state? |
| Model serving and vector infrastructure | llama.cpp, vLLM, Milvus, Pinecone | How do model artifacts, inference schedulers, vector indexes, and client/control interfaces expose retrieval and serving state? |
| Database engines | MySQL Server, RocksDB | How do server-oriented relational storage and embedded key-value storage organize state and durability? |
| Graphics and multimedia libraries | Three.js, Blender, SDL, Unity, Chafa | How do scene graphs, content tools, terminal/image conversion, windows, input, and rendering abstractions compose? |
| Generative AI applications and local model services | ComfyUI, Ollama | How do executable workflow graphs, node extensions, model lifecycles, API services, and backend runners compose? |

## Analysis policy

- Clone only a shallow checkout into the ignored local cache.
- Record the requested ref and resolved commit before extracting facts.
- Keep source repositories out of the Mathen Git history.
- Generate draft cards under `data/drafts/`; only reviewed cards belong under
  `data/systems/`.
- Use the `priority` field to process the core set before the extended set.
- Treat repository metrics as evidence for further analysis, not as semantic
  proof of architecture.
- The catalog deliberately combines older foundational systems with current
  runtimes and libraries: xv6, Coreutils, GCC, Lua, and FreeBSD provide
  historical and systems-oriented anchors, while Rust, Wasmtime, gRPC, and
  Three.js cover modern language, runtime, protocol, and graphics boundaries.
- Categories are comparative lenses rather than mutually exclusive taxonomy.
  A repository is included where its source structure and official
  documentation make a useful architectural boundary visible; it is not a
  claim that the project is representative of every implementation in its
  category.

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
