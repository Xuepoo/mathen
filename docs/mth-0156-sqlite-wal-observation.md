# MTH-0156: SQLite WAL reader visibility observation

MTH-0156 adds a second, non-duplicate research observation to the existing G5
SQLite transaction experiment. It uses two local SQLite connections in explicit
WAL mode rather than the prior single-connection explicit-rollback protocol.
The result is stored outside the canonical card and remains `canonical: false`.

## Protocol and boundary

The runner is
[`scripts/g5_sqlite_wal_visibility_experiment.py`](../scripts/g5_sqlite_wal_visibility_experiment.py).
It verifies SQLite source ID before writing, records the complete Python/OS/
SQLite environment, uses only the standard library, and repeats a fixed protocol
three times:

1. Create a fresh database, enable WAL and `synchronous=FULL`, and commit four
   fixed records.
2. Begin a reader transaction and record its four-row state.
3. Commit one appended row from a writer connection.
4. Read again from the still-held reader transaction, then end it and begin a
   new reader transaction.
5. Compare the held-reader, writer, refreshed-reader, integrity, and final-row
   observations across repetitions.

The observed result is bounded: the held reader remained at four rows while the
writer and refreshed reader saw five. This does not test rollback, process crash,
power loss, checkpoint starvation, busy errors, durability, performance, or
other journal modes. It does not establish a general isolation, consistency, or
snapshot theorem. Timing is deliberately not measured; the JSON uses a null
measurement with `not-measured` status rather than treating missing timing as
zero. The mathematical view separately records absence of evidence for omitted
conditions; that record is not a negative finding.

## Artifacts

- [`g5-sqlite-wal-visibility-observation.json`](../data/experiments/g5-sqlite-wal-visibility-observation.json)
  is the v1 observation contract. It is unreviewed research evidence with
  `canonical: false`, explicit scope, provenance, artifact digests, and local
  evidence closure.
- [`g5-sqlite-wal-visibility-results.json`](../data/experiments/g5-sqlite-wal-visibility-results.json)
  contains all raw per-repetition observations and the runner digest.
- [`sqlite-wal-snapshot-visibility-mth-0156.json`](../data/mathviews/sqlite-wal-snapshot-visibility-mth-0156.json)
  is a standalone finite state-machine candidate. Its deterministic classifier
  validates transition closure; its validation records report the bounded
  observation and explicitly abstain from claims about untested conditions.

The artifacts are research-only. This task does not modify production
D1/API/MCP/Web surfaces, add graph relations, promote evidence, or alter
drafts.

## Reproduction and checks

Use the exact source ID and output paths recorded in the observation:

```bash
uv run --offline python scripts/g5_sqlite_wal_visibility_experiment.py \
  --expected-source-id \
  4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3 \
  --repetitions 3 \
  --output data/experiments/g5-sqlite-wal-visibility-results.json
```

The output is compared byte-for-byte with the committed results after the
runner and environment have been checked. The focused tests validate both
observation contracts and standalone math-view records through the existing
card/math-view validators.
