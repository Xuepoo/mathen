#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PUBLISH="$ROOT/scripts/workflow-publish.sh"
IMPORT="$ROOT/scripts/workflow-import.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/mathen-workflow-test.XXXXXX")"
trap 'find "$TMP" -depth -type f -delete 2>/dev/null || true; find "$TMP" -depth -type d -empty -delete 2>/dev/null || true' EXIT

export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
BIN="$TMP/bin"
mkdir -p "$BIN"

cat >"$BIN/carryctx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == version && "${2:-}" == --json ]]; then
    printf '{"data":{"contract_versions":{"cli":"%s","ctxpack_format":{"format":"carryctx-pack-dir","format_version":2},"db_schema":18}}}\n' "${FAKE_CARRYCTX_VERSION:-0.12.0}"
    exit 0
fi
if [[ "$1" == export && "${2:-}" == --help ]]; then
    printf '%s\n' '--pack-format dir' '--publication' '--dry-run' '--json'
    exit 0
fi
if [[ "$1" == import && "${2:-}" == --help ]]; then
    printf '%s\n' '--from-git REF' '--mode MODE' '--dry-run' '--json'
    exit 0
fi
project=""
dry_run=0
for ((i = 1; i <= $#; i++)); do
    case "${!i}" in
    --project) i=$((i + 1)); project="${!i}" ;;
    --dry-run) dry_run=1 ;;
    esac
done
if [[ "$1" == export ]]; then
    project_id="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["project"]["id"])' "$project/.carryctx/config.toml")"
    source="$(git -C "$project" rev-parse HEAD)"
    export_id="01ARZ3NDEKTSV4RRFFQ69G5FAV"
    redacted=true
    [[ "${FAKE_CARRYCTX_EXPORT:-}" == unredacted ]] && redacted=false
    if ((dry_run)); then
        printf '{"data":{"manifest":{"carryctx_version":"0.12.0","format":"carryctx-pack-dir","format_version":2,"schema_version":18,"project_id":"%s","export_id":"%s","source":{"git_commit":"%s"},"redacted":%s}}}\n' "$project_id" "$export_id" "$source" "$redacted"
        exit 0
    fi
    [[ "${FAKE_CARRYCTX_EXPORT:-}" == no-advance ]] && exit 0
    exit 0
fi
if [[ "$1" == import ]]; then
    if [[ "${FAKE_IMPORT_MODE:-}" == fail ]]; then
        printf 'mutated by failing importer\n' >"$project/.carryctx/config.toml"
        exit 1
    fi
    exit 0
fi
exit 0
EOF
chmod +x "$BIN/carryctx"

new_repo() {
	local name="$1"
	mkdir -p "$TMP/$name/.carryctx"
	git init -q -b main "$TMP/$name"
	git -C "$TMP/$name" config user.name test
	git -C "$TMP/$name" config user.email test@example.invalid
	cat >"$TMP/$name/.carryctx/config.toml" <<'EOF'
schema_version = 1

[project]
id = "01M5ERK3KZJES6RSFAZBRMCM0F"
name = "mathen"
task_prefix = "MTH"

[git]
main_branch = "main"
EOF
	git -C "$TMP/$name" add .
	git -C "$TMP/$name" commit -qm init
	mkdir -p "$TMP/$name.remote"
	git init -q --bare "$TMP/$name.remote/mathen.git"
	git -C "$TMP/$name" remote add origin "$TMP/$name.remote/mathen.git"
	git --git-dir="$TMP/$name.remote/mathen.git" fetch -q "$TMP/$name" HEAD:refs/heads/main
}

assert_fail() {
	if "$@" >"$TMP/out" 2>&1; then
		echo "expected failure: $*" >&2
		cat "$TMP/out" >&2
		exit 1
	fi
}

new_repo gates
assert_fail env CARRYCTX_BIN="$BIN/carryctx" FAKE_CARRYCTX_VERSION=0.11.6 "$PUBLISH" --project "$TMP/gates" --dry-run
git -C "$TMP/gates" checkout -q --detach HEAD
assert_fail env CARRYCTX_BIN="$BIN/carryctx" "$PUBLISH" --project "$TMP/gates" --dry-run
git -C "$TMP/gates" checkout -q main
cp -a "$TMP/gates" "$TMP/renamed"
git -C "$TMP/renamed" remote set-url origin "$TMP/gates.remote/not-mathen.git"
assert_fail env CARRYCTX_BIN="$BIN/carryctx" "$PUBLISH" --project "$TMP/renamed" --dry-run
git -C "$TMP/renamed" remote set-url origin "$TMP/gates.remote/mathen.git"
PATH="$BIN:$PATH" CARRYCTX_BIN="$BIN/carryctx" "$PUBLISH" --project "$TMP/renamed" --dry-run >/dev/null

new_repo publish
refs_before="$(git -C "$TMP/publish" show-ref)"
PATH="$BIN:$PATH" CARRYCTX_BIN="$BIN/carryctx" "$PUBLISH" --project "$TMP/publish" --dry-run >"$TMP/out"
grep -q 'dry-run PASS' "$TMP/out"
[[ "$(git -C "$TMP/publish" show-ref)" == "$refs_before" ]]
assert_fail env CARRYCTX_BIN="$BIN/carryctx" FAKE_CARRYCTX_EXPORT=unredacted "$PUBLISH" --project "$TMP/publish" --dry-run
grep -q 'did not advance' "$PUBLISH"

new_repo state
DB="$TMP/state/.git/carryctx/state.sqlite"
mkdir -p "$(dirname "$DB")"
python3 - "$DB" "$TMP/state" <<'PY'
import sqlite3
import sys
from pathlib import Path

db = sqlite3.connect(sys.argv[1])
root = Path(sys.argv[2]).resolve()
common = root / ".git"
db.executescript("""
CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, task_prefix TEXT, repository_root TEXT, git_common_dir TEXT, main_branch TEXT, schema_version INTEGER, created_at TEXT, updated_at TEXT);
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT, checksum TEXT, applied_at TEXT);
CREATE TABLE sessions (id TEXT, state TEXT);
CREATE TABLE operations (id TEXT, state TEXT);
""")
for name in "agents checkpoint_corrections checkpoints decisions events graph_edges graph_nodes handoffs progress_items scopes sequences snapshot_state task_dependencies team_members teams tombstones worktree_cleanup_requests worktrees tasks".split():
    db.execute(f'CREATE TABLE "{name}" (id INTEGER)')
for version in range(1, 19):
    db.execute("INSERT INTO schema_migrations VALUES (?, ?, ?, ?)", (version, str(version), "x", "now"))
db.execute("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ("01M5ERK3KZJES6RSFAZBRMCM0F", "mathen", "MTH", str(root), str(common), "main", 4, "now", "now"))
db.execute("INSERT INTO sequences VALUES (1)")
db.commit()
PY
state_before="$(sha256sum "$DB")"
assert_fail env CARRYCTX_BIN="$BIN/carryctx" "$IMPORT" --project "$TMP/state"
[[ "$(sha256sum "$DB")" == "$state_before" ]]
sqlite3 "$DB" "INSERT INTO sessions VALUES ('active-session','active')"
assert_fail env CARRYCTX_BIN="$BIN/carryctx" "$IMPORT" --project "$TMP/state" --force
state_active="$(sha256sum "$DB")"
[[ "$state_active" != "$state_before" ]]

# Import remains read-only when the remote publication is unavailable; malformed
# manifests, config safety, and provenance are covered by helper unit tests.
assert_fail env CARRYCTX_BIN="$BIN/carryctx" "$IMPORT" --project "$TMP/state"

echo 'workflow-snapshot.test.sh: OK'
