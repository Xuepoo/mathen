# G5: SQLite transaction rollback and subsequent commit

## Question and scope

Can a connection explicitly roll back a transaction containing a duplicate-key
failure, then commit a new transaction whose rows survive close/reopen?

This is a small, local behavioral observation, recorded separately from canonical
cards. It tests application-requested rollback and subsequent connection use;
it does not test process crashes, power failure, concurrent writers, automatic
whole-transaction rollback, or performance. The constraint error itself does not
roll back the entire transaction: the runner explicitly calls `rollback()`.

## Fixed system and environment

The measured system is SQLite 3.50.4, Fossil source check-in
`4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3`.
`system_commit` is that SQLite source hash, not the Mathen repository commit.
The runner verifies the source hash before writing any evidence. The complete
`sqlite_source_id()` string and observed Python/OS versions are in the JSON
environment record. The recorded run used CPython 3.13.13 on Linux x86_64.

The script uses only Python's standard library. With the existing project
environment available, run from the Mathen checkout:

```bash
uv run --offline python scripts/g5_sqlite_transaction_experiment.py --expected-source-id 4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3 --repetitions 3 --output data/experiments/g5-sqlite-transaction-results.json
```

No repository download or network request is performed. A different SQLite build
fails the source-ID check. To observe another build, pass its actual source hash
and a different output path: that is a new experiment environment, not an exact
rerun of this evidence. Tests use the host's actual source ID to remain portable.

## Protocol and dataset

Each repetition creates a new temporary on-disk database and removes it afterward.
There are no connections shared between repetitions. Default SQLite journal and
synchronous settings are used; this experiment makes no durability-mode claim.

1. Create `records(id INTEGER PRIMARY KEY, name TEXT NOT NULL, value INTEGER NOT NULL)`.
2. Commit `(1, alpha, 10)`, `(2, beta, 20)`, `(3, gamma, 30)`, `(4, delta, 40)`.
3. Begin another transaction, insert `(5, epsilon, 50)`, then attempt
   `(1, duplicate-alpha, 999)`. Catch `IntegrityError` and explicitly roll back.
4. Read ordered rows and compare the entire state to the seeded state.
5. Begin a new transaction, insert `(5, epsilon, 50)`, and commit.
6. Check `PRAGMA integrity_check`; close and reopen; compare the complete rows.
7. Repeat three times and compare all observations, including the final row hash.

The runner exits unsuccessfully on unexpected observations, an invalid repetition
count, or a source-ID mismatch. It writes evidence only after successful checks.
For this fixed five-row dataset, work and report size grow linearly with the
repetition count: O(r) time and O(r) memory; this is not a measured speed claim.

## Recorded results and artifacts

[`data/experiments/g5-sqlite-transaction-results.json`](../data/experiments/g5-sqlite-transaction-results.json)
is a standalone G5 evidence object. Its `artifacts` contains all three raw
observation records and the runner's SHA-256; its `dataset` contains all seed rows.
The hash of the final rows uses UTF-8 JSON with compact separators and rows ordered
by primary key. Database-file bytes are not used as a reproducibility criterion.

| Observation                                              |   Result |
| -------------------------------------------------------- | -------: |
| Seeded rows / sum                                        |  4 / 100 |
| Rows / sum after explicit rollback                       |  4 / 100 |
| Rows / sum after subsequent commit                       |  5 / 150 |
| Rows after reopen                                        |        5 |
| Integrity checks returning `ok`                          |    3 / 3 |
| Caught constraint failures followed by explicit rollback |    3 / 3 |
| Identical observations across repetitions                | 1 (true) |

These results support only the concrete sequential behavior above under the
recorded runtime and dataset. They do not establish a general recovery theorem.
Environment metadata can differ across hosts; compare the fixed source hash and
observations when interpreting a rerun. No timestamps or temporary paths enter
the artifact, so an unchanged local runtime and runner produce identical bytes.

## Validation

```bash
uv run --offline python -m unittest discover -s tests -p test_experiments.py -v
uv run --offline mathen validate
uv run --offline ruff format --check scripts/g5_sqlite_transaction_experiment.py tests/test_experiments.py
uv run --offline ruff check scripts/g5_sqlite_transaction_experiment.py tests/test_experiments.py
```

The experiment tests run the actual protocol, check the recorded artifact, reject
a wrong source hash without creating output, and validate experiment evidence
through the existing cards validator using an in-memory card copy. Canonical
files are never modified by validation or by the experiment.
