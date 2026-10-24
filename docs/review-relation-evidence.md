# Relation evidence review

## Scope and decision rule

This review audits a historical relation-review snapshot, not the current
219-card collection. The current canonical tree contains 46 proposed typed
relations; this report's counts remain scoped to its recorded snapshot. It
audits the typed relations currently present in the 154 reviewed
cards and the bridge candidates recorded by the relation reports. It was run
against the integrated tree at `fb40053` (`feat(data): expand reviewed
architecture graph to 154 systems`). The audit is evidence-local: a relation's
`evidence_ids` must be defined by its source card, its target must be a reviewed
card, and its direction, relation type, claim type, status, and notes must fit
the source-card claim. Legacy `related_systems` is navigation metadata and is
not treated as typed semantic evidence.

No canonical card was changed by this review. Candidate recommendations below
remain `claim_status: proposed` and are inputs to a separate card edit/review.

## Exact audit commands and metrics

The following commands were run from the repository root:

```text
uv run mathen validate
uv run python -m unittest discover -s tests -v
python - <<'PY'
import glob,json,collections
files=sorted(glob.glob('data/systems/*.json'))
cards=[json.load(open(f)) for f in files]
ids={c['id'] for c in cards}
rels=[(c,r) for c in cards for r in c.get('relations',[])]
legacy=[(c,t) for c in cards for t in c.get('related_systems',[]) if t in ids]
missing_targets=[(c['id'],r['target']) for c,r in rels if r['target'] not in ids]
missing_evidence=[]
for c,r in rels:
    e={x['id'] for x in c['evidence']}
    for evidence_id in r['evidence_ids']:
        if evidence_id not in e: missing_evidence.append((c['id'],evidence_id))
print(f'cards={len(cards)} features={sum(len(c.get("features",[])) for c in cards)} mathematical_views={sum(len(c.get("mathematical_views",[])) for c in cards)}')
print(f'typed_relations={len(rels)} legacy_related_edges={len(legacy)} missing_targets={len(missing_targets)} missing_source_evidence_ids={len(missing_evidence)}')
print('relation_types='+repr(dict(sorted(collections.Counter(r['type'] for _,r in rels).items()))))
print('claim_types='+repr(dict(sorted(collections.Counter(r['claim_type'] for _,r in rels).items())))+' statuses='+repr(dict(sorted(collections.Counter(r['claim_status'] for _,r in rels).items()))))
PY
```

Results:

| Check                                      |                        Result |
| ------------------------------------------ | ----------------------------: |
| Reviewed cards                             |                           154 |
| Features                                   |                           553 |
| Mathematical views                         |                           416 |
| Typed relations                            |                             4 |
| Valid legacy `related_systems` edges       |                           228 |
| Missing relation targets                   |                             0 |
| Missing source-local relation evidence IDs |                             0 |
| Relation types                             | `resembles`: 3; `composes`: 1 |
| Relation claim types                       |       `analogy`: 3; `fact`: 1 |
| Relation statuses                          |                 `proposed`: 4 |

`uv run mathen validate` reported every card valid. The unittest command ran 20
tests and finished `OK`. The existing worktree change is in
`docs/user-manual.md`; this review only adds this report.

## Current typed relations

All four current relations are structurally valid and use evidence IDs local
to the source card. Their directions and types are conservative:

| Source → type → target                 | Claim / status         | Source-local evidence                            | Audit decision                                                                                                                                                                                                                    |
| -------------------------------------- | ---------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `duckdb` → `resembles` → `postgresql`  | `analogy` / `proposed` | `duckdb-why`                                     | **Accept as proposed.** The source evidence supports the embedded, vectorized analytical query-engine boundary. `resembles` is appropriate for comparison with PostgreSQL; `uses` or `composes` would overstate the source claim. |
| `sqlite` → `resembles` → `duckdb`      | `analogy` / `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | **Accept as proposed.** The source evidence supports embedded database execution and explicitly distinguishes workload/execution differences. Do not add a reverse duplicate.                                                     |
| `sqlite` → `resembles` → `postgresql`  | `analogy` / `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | **Accept as proposed.** The source evidence supports a relational/local-versus-client-server comparison, not dependency or equivalence.                                                                                           |
| `supabase` → `composes` → `postgresql` | `fact` / `proposed`    | `supabase-architecture`                          | **Accept as proposed.** The source card explicitly describes PostgreSQL as the core around which Supabase services are assembled. `composes` is directional from platform to core; the reverse is unsupported.                    |

The four relations have existing targets (`duckdb`, `postgresql`) and no
unknown evidence references. Their `proposed` status is correct: validation
checks shape and local evidence, but does not itself accept a cross-card claim.

## Candidate bridges

The candidate reports propose bridges only when the source card has a precise
local anchor. The following are safe to carry forward as proposed candidates.
They are recommendations for a future canonical-card edit; this report does
not add them.

| Source → type → target                  | Claim / status         | Source-local evidence                             | Recommendation and boundary                                                                                                                                                                                                                                                                                            |
| --------------------------------------- | ---------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `grpc` → `uses` → `protobuf`            | `fact` / `proposed`    | `grpc-core-concepts`, `grpc-source-cpp-generator` | **Recommend.** gRPC's source feature says Protocol Buffers are the default service/message description and the generator emits interfaces from descriptors. Keep direction `grpc` → `protobuf`; do not claim every deployment uses Protobuf, that Protobuf implements transport, or that the reverse dependency holds. |
| `firecracker` → `resembles` → `qemu`    | `analogy` / `proposed` | `firecracker-design`                              | **Recommend.** Both cards expose a VMM/guest/device boundary; Firecracker narrows the device model while QEMU is broadly configurable. Keep one directed comparison and do not imply implementation reuse, substitutability, or historical influence.                                                                  |
| `rust` → `resembles` → `llvm`           | `analogy` / `proposed` | `rustc-overview`, `rust-fixed-source`             | **Recommend only as analogy.** The source card names LLVM IR in Rust's staged compiler pipeline, but that is not sufficient for `uses` unless a future source review establishes the LLVM project dependency.                                                                                                          |
| `kafka` → `resembles` → `redis`         | `analogy` / `proposed` | `kafka-introduction`                              | **Recommend only with a narrowed note.** The shared shape is append-oriented retained/replayable event history. Kafka partitions and replicates logs; Redis Streams are a data structure with separate persistence modes. Do not claim matching durability, ordering scope, or consumer-group semantics.               |
| `kafka` → `resembles` → `elasticsearch` | `analogy` / `proposed` | `kafka-introduction`                              | **Recommend only with a narrowed note.** The comparison is partition/replica placement, not product integration: Kafka retains ordered event logs, whereas Elasticsearch stores searchable Lucene shards and performs scatter-gather search.                                                                           |

The older reports also mention Redis/SQLite, Kafka/SQLite, and CPython/Wasmtime
comparisons. They are not rejected as impossible, but they should remain
lower-priority hypotheses: their shared vocabulary (persistence, replay,
context, or scoped state) spans materially different contracts. If retained,
the source evidence and boundary notes in the originating report must be copied
exactly and the relation must stay `resembles`/`analogy`/`proposed`.

## Rejected or deferred bridges

The following are not safe edits from the current source-card evidence:

- Do not infer `protobuf` → `uses` → `grpc`; the reviewed direction is gRPC's
  documented default use of Protocol Buffers.
- Do not turn Rust's mention of LLVM IR into `rust` → `uses` → `llvm` without
  evidence that the reviewed Rust implementation uses the LLVM project. The
  conservative candidate is `resembles`.
- `kvm` and `lucene` have no reviewed target cards in this snapshot. The `etcd`
  card does exist; adding `kubernetes` → `uses` → `etcd` still requires a
  source-local citation supporting the specific integration. A related product
  or host fact outside the source card is not source-local relation evidence.
- Do not add Linux/Kubernetes, Linux/NGINX, Firecracker/Kubernetes, or
  QEMU/NGINX edges from generic scheduler, process, event, host, or isolation
  vocabulary. The cards do not state a specific cross-system contract.
- Do not add `extends` or `influenced-by`: no reviewed pair supplies a
  compatible base/derived implementation claim or historical design-lineage
  evidence.
- Do not bridge FFmpeg to gRPC, Protocol Buffers, or another card merely because
  both cards use terms such as “stream”, “graph”, or “pipeline”. Its evidence
  describes media format, codec, and filter boundaries.

## Safe edit recommendations

If the commander elects to update cards after this review, the safe sequence is:

1. Add only the highest-confidence `grpc` → `uses` → `protobuf` candidate and,
   separately, `firecracker` → `resembles` → `qemu`.
2. Use exactly the source-local evidence IDs listed above; target evidence IDs
   must not be copied into the source relation unless they are defined in that
   source card.
3. Preserve `claim_status: proposed` for every new edge. Acceptance requires a
   deliberate review rather than validator success.
4. Keep `fact` for documented integration/dependency and `analogy` for bounded
   structural comparison. Do not use shared words as evidence.
5. Re-run `uv run mathen validate`, the unittest command, and the relation-metrics
   command after any card edit. Expected post-edit metrics for adding both
   highest-confidence candidates are 6 typed relations, 1 `uses`, 4
   `resembles`, 1 `composes`, 2 `fact`, 4 `analogy`, all 6 `proposed`, with
   zero missing targets and zero missing source-local evidence IDs.

The graph should remain sparse. The current four edges pass the local evidence
audit; candidate bridges should be added only when their directional claim and
semantic boundary remain explicit.
