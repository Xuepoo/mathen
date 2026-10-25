#!/usr/bin/env bash
# Restore the local CarryCtx DB from the validated redacted publication ref.
set -euo pipefail

SNAP_REF="refs/heads/carryctx-snapshots"
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${WORKFLOW_REMOTE:-origin}"
GIT_TIMEOUT="${WORKFLOW_GIT_TIMEOUT:-${GIT_TIMEOUT:-120}}"
DRY_RUN=0
FORCE=0

usage() {
	cat <<'EOF'
Usage: scripts/workflow-import.sh [options]

Fetch and restore the redacted CarryCtx publication from refs/heads/carryctx-snapshots.

Options:
  --dry-run              Fetch and validate; write no DB or config.
  --force                Allow replacement of a non-empty local CarryCtx DB.
  --project DIR          Repository to restore (default: this repository).
  --remote NAME          Git remote (default: WORKFLOW_REMOTE or origin).
  --git-timeout SECONDS  Timeout for Git/CarryCtx/SQLite operations (default: 120).
  --help                 Show this help.
EOF
}

die() {
	echo "workflow-import: FAIL: $*" >&2
	exit 1
}
log() { echo "workflow-import: $*"; }
have() { command -v "$1" >/dev/null 2>&1 || die "$1 is required"; }

while (($#)); do
	case "$1" in
	--dry-run)
		DRY_RUN=1
		shift
		;;
	--force)
		FORCE=1
		shift
		;;
	--project)
		PROJECT="${2:?--project requires a directory}"
		shift 2
		;;
	--project=*)
		PROJECT="${1#*=}"
		shift
		;;
	--remote)
		REMOTE="${2:?--remote requires a name}"
		shift 2
		;;
	--remote=*)
		REMOTE="${1#*=}"
		shift
		;;
	--git-timeout)
		GIT_TIMEOUT="${2:?--git-timeout requires seconds}"
		shift 2
		;;
	--git-timeout=*)
		GIT_TIMEOUT="${1#*=}"
		shift
		;;
	--help | -h)
		usage
		exit 0
		;;
	*) die "unknown option $1 (see --help)" ;;
	esac
done

[[ "$GIT_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || die "timeout must be a positive integer"
have git
have carryctx
have timeout
have python3
PROJECT="$(cd "$PROJECT" 2>/dev/null && pwd)" || die "project directory not found"
[[ -d "$PROJECT/.git" || -f "$PROJECT/.git" ]] || die "$PROJECT is not a Git repository"
[[ -f "$PROJECT/.carryctx/config.toml" ]] || die "$PROJECT has no .carryctx/config.toml"
git_run() { timeout "$GIT_TIMEOUT" git -C "$PROJECT" "$@"; }
carryctx_run() { timeout "$GIT_TIMEOUT" carryctx "$@"; }

common_dir="$(git_run rev-parse --path-format=absolute --git-common-dir)"
db="$common_dir/carryctx/state.sqlite"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/mathen-workflow-import.XXXXXX")"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

if [[ -f "$db" ]]; then
	have sqlite3
	read -r project_rows data_rows < <(
		sqlite3 -readonly "$db" <<'SQL'
SELECT
  (SELECT COUNT(*) FROM projects),
  (SELECT COUNT(*) FROM agents) + (SELECT COUNT(*) FROM tasks) +
  (SELECT COUNT(*) FROM events) + (SELECT COUNT(*) FROM sessions) +
  (SELECT COUNT(*) FROM progress_items) + (SELECT COUNT(*) FROM checkpoints) +
  (SELECT COUNT(*) FROM decisions) + (SELECT COUNT(*) FROM worktrees);
SQL
	)
	project_rows="${project_rows:-0}"
	data_rows="${data_rows:-0}"
else
	project_rows=0
	data_rows=0
fi
log "local state: db_exists=$([[ -f "$db" ]] && echo 1 || echo 0) project_rows=$project_rows data_rows=$data_rows"
if ((project_rows > 1)); then die "local DB has multiple project rows; refusing ambiguous restore"; fi
if ((DRY_RUN == 0 && data_rows > 0 && FORCE == 0)); then
	die "local DB is non-empty ($data_rows data rows); refusing overwrite without --force"
fi

track_ref="refs/remotes/$REMOTE/carryctx-snapshots"
timeout "$GIT_TIMEOUT" git -C "$PROJECT" fetch --no-tags "$REMOTE" "$SNAP_REF:$track_ref" || die "snapshot ref fetch failed"
commit="$(git_run rev-parse -q --verify "$track_ref" 2>/dev/null || true)"
[[ -n "$commit" ]] || die "remote did not provide $SNAP_REF"
manifest="$(git_run show "$track_ref:manifest.json" 2>/dev/null)" || die "snapshot has no manifest.json"
printf '%s\n' "$manifest" >"$tmp/manifest.json"
python3 - "$tmp/manifest.json" "$PROJECT/.carryctx/config.toml" <<'PY'
import json
import sys
import tomllib

try:
    manifest = json.load(open(sys.argv[1], encoding="utf-8"))
    with open(sys.argv[2], "rb") as stream:
        config = tomllib.load(stream)
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"workflow-import: FAIL: malformed snapshot manifest: {exc}")
if manifest.get("redacted") is not True:
    raise SystemExit("workflow-import: FAIL: snapshot manifest is not redacted:true")
if manifest.get("format") != "carryctx-pack-dir" or not manifest.get("export_id"):
    raise SystemExit("workflow-import: FAIL: snapshot manifest has an unsupported or missing export identity")
project_id = config.get("project", {}).get("id")
if project_id and manifest.get("project_id") != project_id:
    raise SystemExit("workflow-import: FAIL: snapshot belongs to a different CarryCtx project")
PY

message="$(git_run log -1 --format=%B "$track_ref")"
source_line="$(sed -n 's/^CarryCtx-Source: //p' <<<"$message" | head -n1)"
export_id="$(sed -n 's/^CarryCtx-Export-Id: //p' <<<"$message" | head -n1)"
[[ -n "$source_line" && -n "$export_id" ]] || die "snapshot provenance trailers are missing"
manifest_export_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["export_id"])' "$tmp/manifest.json")"
[[ "$export_id" == "$manifest_export_id" ]] || die "snapshot export trailer does not match manifest"
log "provenance: snapshot=${commit:0:12} export_id=$export_id source=$source_line"

if ((DRY_RUN)); then
	log "dry-run PASS: snapshot fetched and validated; local DB untouched"
	exit 0
fi

config="$PROJECT/.carryctx/config.toml"
config_backup="$tmp/config.toml"
config_existed=0
if [[ -f "$config" ]]; then
	config_existed=1
	cp --preserve=all "$config" "$config_backup"
fi
if ((project_rows == 0)); then
	carryctx_run init --non-interactive --project "$PROJECT" >"$tmp/init.log" 2>&1 || {
		cat "$tmp/init.log" >&2
		die "carryctx init failed"
	}
fi
if ! carryctx_run import --from-git "$track_ref" --mode replace --yes --project "$PROJECT" >"$tmp/import.log" 2>&1; then
	cat "$tmp/import.log" >&2
	die "carryctx import failed"
fi
if ((config_existed)); then
	cmp -s "$config_backup" "$config" || cp --preserve=all "$config_backup" "$config"
fi
log "restore PASS: snapshot=${commit:0:12}; config restored byte-identically where present"
