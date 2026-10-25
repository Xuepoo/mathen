#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PUBLISH="$ROOT/scripts/workflow-publish.sh"
IMPORT="$ROOT/scripts/workflow-import.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/mathen-workflow-test.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
BIN="$TMP/bin"
mkdir -p "$BIN"
cat >"$BIN/carryctx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == export ]]; then
  project=""; output=""; dry_run=0
  while (($#)); do
    case "$1" in
      --project) project="$2"; shift 2;;
      --output) output="$2"; shift 2;;
      --dry-run) dry_run=1; shift;;
      *) shift;;
    esac
  done
  [[ -n "$output" ]] && mkdir -p "$output"
  if [[ "${CARRYCTX_EXPORT_MODE:-}" == no-advance ]]; then exit 0; fi
  id="export-test"
  if ((dry_run)); then
    printf '{"data":{"manifest":{"redacted":true,"format":"carryctx-pack-dir","export_id":"%s"}}}\n' "$id"
    exit 0
  fi
  printf '{"redacted":true,"format":"carryctx-pack-dir","export_id":"%s"}\n' "$id" >"$project/manifest.json"
  git -C "$project" add manifest.json
  git -C "$project" commit -q -m snapshot -m "CarryCtx-Export-Id: $id" -m "CarryCtx-Source: mathen@$(git -C "$project" rev-parse HEAD) (main)"
  git -C "$project" update-ref refs/heads/carryctx-snapshots HEAD
elif [[ "$1" == import ]]; then
  exit 0
elif [[ "$1" == init ]]; then
  exit 0
fi
EOF
chmod +x "$BIN/carryctx"

new_repo() {
	local name="$1"
	mkdir -p "$TMP/$name"
	git init -q -b main "$TMP/$name"
	git -C "$TMP/$name" config user.name test
	git -C "$TMP/$name" config user.email test@example.invalid
	mkdir -p "$TMP/$name/.carryctx"
	printf 'schema_version = 1\n' >"$TMP/$name/.carryctx/config.toml"
	git -C "$TMP/$name" add .
	git -C "$TMP/$name" commit -qm init
	git init -q --bare "$TMP/$name-remote.git"
	git -C "$TMP/$name" remote add origin "$TMP/$name-remote.git"
	git -C "$TMP/$name" push -q origin main
	git -C "$TMP/$name" fetch -q origin main
}

assert_fail() {
	if "$@" >"$TMP/out" 2>&1; then
		echo "expected failure: $*" >&2
		cat "$TMP/out" >&2
		exit 1
	fi
}

new_repo publish
PATH="$BIN:$PATH" "$PUBLISH" --project "$TMP/publish" --dry-run >"$TMP/out"
grep -q 'dry-run PASS' "$TMP/out"
if git -C "$TMP/publish" rev-parse refs/heads/carryctx-snapshots >/dev/null 2>&1; then
	echo 'dry-run wrote publication ref' >&2
	exit 1
fi
printf 'local change\n' >"$TMP/publish/local.txt"
git -C "$TMP/publish" add local.txt
git -C "$TMP/publish" commit -qm ahead
git -C "$TMP/publish" checkout -q -b feature
assert_fail env PATH="$BIN:$PATH" "$PUBLISH" --project "$TMP/publish" --dry-run
git -C "$TMP/publish" checkout -q main
assert_fail env PATH="$BIN:$PATH" "$PUBLISH" --project "$TMP/publish" --dry-run

new_repo noadvance
git -C "$TMP/noadvance" update-ref refs/heads/carryctx-snapshots HEAD
assert_fail env CARRYCTX_EXPORT_MODE=no-advance PATH="$BIN:$PATH" "$PUBLISH" --project "$TMP/noadvance"

new_repo import
git -C "$TMP/import" checkout -q -b snapshot
printf '{"redacted":false,"format":"carryctx-pack-dir","export_id":"bad"}\n' >"$TMP/import/manifest.json"
git -C "$TMP/import" add manifest.json
git -C "$TMP/import" commit -qm malformed
git -C "$TMP/import" push -q origin HEAD:refs/heads/carryctx-snapshots
assert_fail env PATH="$BIN:$PATH" "$IMPORT" --project "$TMP/import" --dry-run

new_repo nonempty
mkdir -p "$TMP/nonempty/.git/carryctx"
sqlite3 "$TMP/nonempty/.git/carryctx/state.sqlite" \
	"CREATE TABLE projects (id TEXT); CREATE TABLE tasks (id TEXT); INSERT INTO projects VALUES ('p'); INSERT INTO tasks VALUES ('t');"
config_before="$(cat "$TMP/nonempty/.carryctx/config.toml")"
assert_fail env PATH="$BIN:$PATH" "$IMPORT" --project "$TMP/nonempty"
[[ "$(cat "$TMP/nonempty/.carryctx/config.toml")" == "$config_before" ]]

echo 'workflow-snapshot.test.sh: OK'
