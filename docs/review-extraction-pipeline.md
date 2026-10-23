# MTH-0074: extraction-pipeline review

## Scope and reproducibility

This review audits the deterministic repository inspector, modeling bundle
builder, representative manifest, tests, and checked-in draft/card artifacts.
It does not change application code, schemas, or cards. All counts below were
produced from the checkout at review time with Python 3.12-compatible standard
library code:

```bash
cd /mnt/data/Workspace/Projects/mathen/.worktrees/mth-0074
python - <<'PY'
import json
from collections import Counter
from pathlib import Path

manifest = json.loads(Path("data/repositories/representative.json").read_text())
drafts = sorted(Path("data/drafts").glob("*.json"))
structural = []
for path in drafts:
    card = json.loads(path.read_text())
    if (
        card.get("version_context", "").startswith("commit ")
        and card.get("features")
        and card["features"][0].get("id") == "repository-structure"
    ):
        structural.append(card)

print("manifest", len(manifest), Counter(item["priority"] for item in manifest))
print("drafts", len(drafts))
print("structural drafts", len(structural))
print("structural feature/view counts", Counter(
    (len(card["features"]), len(card["mathematical_views"]))
    for card in structural
))
print("structural related_systems lengths", Counter(
    len(card.get("related_systems", [])) for card in structural
))
print("all draft feature counts", Counter(
    len(json.loads(path.read_text()).get("features", [])) for path in drafts
))
print("all draft mathematical-view counts", Counter(
    len(json.loads(path.read_text()).get("mathematical_views", [])) for path in drafts
))
print("all draft related_systems lengths", Counter(
    len(json.loads(path.read_text()).get("related_systems", [])) for path in drafts
))
print("modeling bundles", len(list(Path("data/modeling").glob("*.json"))))
print("analyses directory exists", Path("data/analyses").exists())
PY
```

Observed output:

```text
manifest 52 Counter({'core': 30, 'extended': 17, 'seed': 5})
drafts 45
structural drafts 39
structural feature/view counts Counter({(3, 2): 36, (2, 1): 3})
structural related_systems lengths Counter({0: 39})
all draft feature counts Counter({3: 36, 2: 3, 8: 2, 6: 2, 4: 1, 1: 1})
all draft mathematical-view counts Counter({2: 36, 1: 4, 5: 3, 3: 1, 6: 1})
all draft related_systems lengths Counter({0: 40, 3: 5})
modeling bundles 9
analyses directory exists False
```

The five non-structural, non-composition drafts are `duckdb`, `kafka`,
`postgresql`, `redis`, and `sqlite`; each has manually expanded semantic
features/views and three `related_systems` entries. The remaining 39 structural
drafts use the deterministic shape. The one additional draft,
`sqlite-duckdb-analytical-workflow`, is a candidate composition rather than a
repository-inspector output. Thus the “mostly shallow 3–4 feature drafts”
observation is reproducible for the generated structural set: 36/39 (92.3%)
have exactly three features and two candidate views, and 3/39 (7.7%) have two
features and one candidate view. There are no generated structural peer links.

The manifest has 52 repositories, while only nine modeling bundles are checked
in. `data/analyses/` is not present in this checkout, so the original analysis
reports cannot be recomputed from checked-in artifacts alone. The nine bundles
still expose their fixed-commit deterministic observations and structural draft
inputs; they are useful evidence about the contract, not evidence that all 52
manifest entries were analyzed in this tree.

## Pipeline findings

### Why the structural drafts are shallow

The result is intentional and deterministic, rather than a failure to discover
features:

1. `inspect_repository` in `src/mathen/repositories.py:296-350` extracts only
   file paths, extension/language counts, top-level entries, recognized root
   build markers, README paths, path-token counts, commit, and provenance. It
   explicitly describes these as observations without assigning runtime
   semantics.
2. `build_draft_card` in `src/mathen/repositories.py:353-500` always constructs
   the same three feature slots when a path signal exists: repository
   structure, architecture-related path signals, and build/integration surface.
   If no path signal exists, the second slot is omitted, explaining the three
   3/2 and two 2/1 cases. It always emits the finite labeled repository graph
   view and emits the evidence-prioritization view only when signals exist.
3. Both deterministic feature descriptions cite only the single
   `repository-commit` evidence record. The card also carries
   `official-documentation`, but the inspector does not read that document.
   The code therefore has no input from which to derive a supported MVCC,
   replication, scheduler, parser, or other semantic feature.
4. `modeling.py:18-110` creates a one-system bundle containing the deterministic
   report, the existing structural draft, and five questions for a later
   model/reviewer stage. It does not perform source reading, documentation
   retrieval, cross-system comparison, or semantic extraction itself.

Consequently, adding more path-token categories or inflating the structural
card would not solve the missing semantic evidence. It would only create more
navigation hypotheses. The shallow baseline is the correct safety boundary for
the current deterministic extractor.

### Why shared mathematical/relation links are absent

The absence has two separate, concrete causes:

- `build_draft_card` returns `"related_systems": []` at line 499 on every
  generated structural card. No relation candidate or typed relation is
  computed there.
- `build_modeling_bundle` accepts one `RepositorySpec`, one analysis, and one
  draft. Its contract contains no peer-card collection, shared feature
  vocabulary, relation candidate input, or cross-system evidence. The modeling
  prompt asks which mathematical views explain *this system's* features, but
  does not ask the model to compare systems. A per-system bundle cannot
  deterministically infer shared links.

The five expanded drafts demonstrate that links appear after review/manual
modeling, not from the structural extractor. Their links and semantic views
have evidence records such as official documentation and repository commits;
they are not generated by the `related_systems=[]` branch. The legacy
`related_systems` field is also untyped. It cannot distinguish `uses`,
`extends`, `resembles`, `composes`, or historical `influenced-by`; structural
similarity must not be silently upgraded to any of those claims.

## Observation/claim boundary

The following are deterministic observations supported by the current code and
artifacts:

- a fixed requested ref resolves to a recorded commit and provenance;
- a checkout has a count of tracked/visible paths, extensions, recognized
  languages, root markers, README paths, and token-based path signals;
- a generated card contains the fixed structural slots and cites the generated
  repository-commit evidence;
- the modeling bundle preserves the analysis and structural draft and gives the
  later model a fixed-commit contract;
- the current generated structural cards have zero peer links.

The following are not established by this pipeline and must remain semantic
claims requiring source/documentation evidence and human review:

- “this system uses MVCC,” “is event-driven,” “replicates,” “is a compiler,” or
  similar runtime/architectural statements;
- that two path names or build markers identify the same architecture feature;
- that two systems share a mathematical model in a meaningful sense;
- that one system uses, extends, composes with, resembles, or influenced another;
- that a candidate mathematical view is a proof, invariant, guarantee, or
  historical explanation.

The existing code mostly enforces this boundary correctly: path signals are
called weak/non-semantic signals, mathematical views state assumptions and use
`inference`/`hypothesis`, and the LLM contract requires existing evidence IDs.
Card validation checks references and claim-type syntax, but valid JSON and a
known evidence ID do not make the semantic claim true.

## Test coverage audit

`tests/test_cards.py` currently covers manifest minimum membership, generated
card reference validity, archive provenance, interrupted downloads, fixed
revision bundle fields, and LLM evidence/output guards. It does not test:

- the no-signal branch that yields two features and one view;
- the path-signal branch's exact structural feature/view IDs and claim types;
- the invariant that generated structural cards have empty `related_systems`;
- `analyze_manifest` writing paired analysis/draft files or recording failures;
- `build_modeling_bundles` filtering/skipping behavior and one-bundle contract;
- any peer comparison, shared mathematical-view candidate, or typed relation
  generation (none exists in the implementation);
- a reproducible manifest-wide count or a stable analysis-version/report shape.

### Minimal actionable changes and tests

The smallest safe next step is to improve evidence preparation without
pretending it is semantic modeling:

1. Add focused unit tests around `build_draft_card` for a report with no path
   signals and one with signals. Assert exact feature/view IDs, claim types,
   evidence IDs, and `related_systems == []`. This locks the intentional shallow
   baseline and prevents accidental semantic inflation.
2. Add a temporary-directory test for `build_modeling_bundles` with two manifest
   entries, one missing analysis/draft pair, and one complete pair. Assert that
   only the complete pair is written and that its bundle preserves commit,
   provenance, and structural draft evidence. This covers the current
   one-system boundary.
3. Add an `analyze_manifest` test using a local archive-like checkout or mocked
   `checkout_repository`/`inspect_repository`. Assert report and draft output,
   `analysis_version`, commit/provenance propagation, and
   `continue_on_error` failure recording. Do not make this a network test.
4. For semantic expansion, add a separate reviewed-source extraction stage
   whose output cites source/documentation evidence per feature and view. Give
   it explicit `fact`/`inference`/`hypothesis`/`analogy` labels and human review;
   do not alter `build_draft_card` to guess semantics from paths.
5. For shared links, first define a cross-system candidate artifact (outside
   this deterministic inspector) containing the compared evidence IDs, shared
   question, assumptions, candidate relation type, and claim status. Only then
   consider a linker over reviewed cards. Require evidence on each generated
   relation and keep `resembles` separate from `influenced-by`; leave the legacy
   `related_systems` field empty for unreviewed structural drafts.

These changes would make the missing stage and its tests explicit without
turning structural observations into unsupported architecture or mathematical
claims.

## Verification boundary

The source-level audit is reproducible with the commands above and with the
existing test suite:

```bash
uv run python -m unittest discover -s tests -v
uv run ruff format --check src/mathen/repositories.py src/mathen/modeling.py tests/test_cards.py
uv run ruff check src/mathen/repositories.py src/mathen/modeling.py tests/test_cards.py
```

The review document itself is the only intended file change for MTH-0074.
