#!/usr/bin/env bash
# Publish the repository-owned, redacted CarryCtx lifecycle snapshot.
# CarryCtx owns redaction; this wrapper owns source, freshness, manifest,
# provenance, and explicit network-boundary checks. It never pushes by default.
set -euo pipefail

PUB_REF="refs/heads/carryctx-snapshots"
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${WORKFLOW_REMOTE:-origin}"
GIT_TIMEOUT="${WORKFLOW_GIT_TIMEOUT:-${GIT_TIMEOUT:-120}}"
DRY_RUN=0
PUSH=0

usage() {
	cat <<'EOF'
Usage: scripts/workflow-publish.sh [options]

Create a redacted CarryCtx publication at refs/heads/carryctx-snapshots.
The command is local-only unless --push is explicitly supplied.

Options:
  --dry-run              Validate export and source gates; write no ref or remote.
  --push                 Push the validated local publication ref to --remote.
  --project DIR          Repository to publish (default: this repository).
  --remote NAME          Git remote (default: WORKFLOW_REMOTE or origin).
  --git-timeout SECONDS  Timeout for Git/CarryCtx operations (default: 120).
  --help                 Show this help.
EOF
}

die() {
	echo "workflow-publish: FAIL: $*" >&2
	exit 1
}
log() { echo "workflow-publish: $*"; }
have() { command -v "$1" >/dev/null 2>&1 || die "$1 is required"; }

while (($#)); do
	case "$1" in
	--dry-run)
		DRY_RUN=1
		shift
		;;
	--push)
		PUSH=1
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

branch="$(git_run branch --show-current)"
[[ "$branch" == main ]] || die "source must be on main (found '${branch:-detached}')"
head_sha="$(git_run rev-parse HEAD)"
remote_main="$(git_run rev-parse -q --verify "refs/remotes/$REMOTE/main" 2>/dev/null || true)"
[[ -n "$remote_main" ]] || die "missing $REMOTE/main; fetch it before publishing"
[[ "$head_sha" == "$remote_main" ]] || die "source main is stale: HEAD $head_sha != $REMOTE/main $remote_main"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/mathen-workflow-publish.XXXXXX")"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

before="$(git_run rev-parse -q --verify "$PUB_REF" 2>/dev/null || true)"
args=(export --pack-format dir --publication --project "$PROJECT" --output "$tmp/pack")
if ((DRY_RUN)); then args+=(--dry-run); fi
log "exporting redacted CarryCtx publication"
if ! carryctx_run "${args[@]}" >"$tmp/export.json" 2>"$tmp/export.err"; then
	cat "$tmp/export.err" >&2
	die "carryctx export --publication failed"
fi

if ((DRY_RUN)); then
	python3 - "$tmp/export.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
manifest = payload.get("data", {}).get("manifest", {})
if manifest.get("redacted") is not True:
    raise SystemExit("workflow-publish: FAIL: dry-run export is not redacted:true")
PY
	dry_after="$(git_run rev-parse -q --verify "$PUB_REF" 2>/dev/null || true)"
	[[ "$dry_after" == "$before" ]] || die "dry-run changed $PUB_REF"
	log "dry-run PASS: redacted export validated; no ref written, nothing pushed"
	exit 0
fi

after="$(git_run rev-parse -q --verify "$PUB_REF" 2>/dev/null || true)"
[[ -n "$after" ]] || die "$PUB_REF was not created by carryctx export --publication"
[[ -n "$before" && "$before" == "$after" ]] && die "$PUB_REF did not advance after export"

manifest="$(git_run show "$PUB_REF:manifest.json" 2>/dev/null)" || die "cannot read $PUB_REF:manifest.json"
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
    raise SystemExit(f"workflow-publish: FAIL: malformed publication manifest: {exc}")
if manifest.get("redacted") is not True:
    raise SystemExit("workflow-publish: FAIL: publication manifest is not redacted:true; refusing to push")
if manifest.get("format") != "carryctx-pack-dir":
    raise SystemExit("workflow-publish: FAIL: unexpected publication format")
if not manifest.get("export_id"):
    raise SystemExit("workflow-publish: FAIL: publication manifest has no export_id")
project_id = config.get("project", {}).get("id")
if project_id and manifest.get("project_id") != project_id:
    raise SystemExit("workflow-publish: FAIL: publication manifest belongs to a different CarryCtx project")
PY

message="$(git_run log -1 --format=%B "$PUB_REF")"
source_line="$(sed -n 's/^CarryCtx-Source: //p' <<<"$message" | head -n1)"
export_id="$(sed -n 's/^CarryCtx-Export-Id: //p' <<<"$message" | head -n1)"
[[ -n "$source_line" ]] || die "publication commit has no CarryCtx-Source trailer"
[[ -n "$export_id" ]] || die "publication commit has no CarryCtx-Export-Id trailer"
[[ "$source_line" == *"$head_sha"* ]] || die "CarryCtx-Source trailer does not name source HEAD $head_sha"
manifest_export_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["export_id"])' "$tmp/manifest.json")"
[[ "$export_id" == "$manifest_export_id" ]] || die "CarryCtx-Export-Id trailer does not match manifest"

log "provenance: snapshot=${after:0:12} export_id=$export_id source=$source_line"
if ((PUSH)); then
	log "pushing $PUB_REF to $REMOTE"
	timeout "$GIT_TIMEOUT" git -C "$PROJECT" push "$REMOTE" "$PUB_REF:$PUB_REF" || die "git push failed; local publication remains available"
	remote_tip="$(git_run ls-remote --refs "$REMOTE" "$PUB_REF" | awk 'NR==1 {print $1}')"
	[[ "$remote_tip" == "$after" ]] || die "remote read-back did not confirm $PUB_REF at $after"
	log "push PASS: $REMOTE/$PUB_REF=${after:0:12}"
else
	log "local publication PASS: $PUB_REF=${after:0:12}; not pushed (use --push explicitly)"
fi
