#!/usr/bin/env bash
# Publish only CarryCtx's redacted lifecycle publication.
# This command is local-only unless --push is explicitly supplied.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
PUB_REF="refs/heads/carryctx-snapshots"
REMOTE="${WORKFLOW_REMOTE:-origin}"
TIMEOUT_SECS="${WORKFLOW_GIT_TIMEOUT:-${GIT_TIMEOUT:-120}}"
DRY_RUN=0
PUSH=0
TMP=""

usage() {
	cat <<'EOF'
Usage: scripts/workflow-publish.sh [--dry-run] [--push] [--project DIR]
       [--remote NAME] [--git-timeout SECONDS]

Create the fixed, redacted refs/heads/carryctx-snapshots publication. The
local ref is never pushed unless --push is explicit.
EOF
}

fail() {
	echo "workflow-publish: FAIL: $*" >&2
	exit 1
}

log() { echo "workflow-publish: $*"; }

cleanup() {
	if [[ -n "$TMP" ]]; then
		find "$TMP" -depth -type f -delete 2>/dev/null || true
		find "$TMP" -depth -type d -empty -delete 2>/dev/null || true
	fi
}

trap cleanup EXIT

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
		PROJECT="${2:?--project requires DIR}"
		shift 2
		;;
	--project=*)
		PROJECT="${1#*=}"
		shift
		;;
	--remote)
		REMOTE="${2:?--remote requires NAME}"
		shift 2
		;;
	--remote=*)
		REMOTE="${1#*=}"
		shift
		;;
	--git-timeout)
		TIMEOUT_SECS="${2:?--git-timeout requires SECONDS}"
		shift 2
		;;
	--git-timeout=*)
		TIMEOUT_SECS="${1#*=}"
		shift
		;;
	--help | -h)
		usage
		exit 0
		;;
	*) fail "unknown option $1" ;;
	esac
done

[[ "$TIMEOUT_SECS" =~ ^[1-9][0-9]*$ ]] || fail "timeout must be a positive integer"
command -v git >/dev/null 2>&1 || fail "git is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v timeout >/dev/null 2>&1 || fail "timeout is required"
PROJECT="$(cd "$PROJECT" 2>/dev/null && pwd)" || fail "project directory not found"
[[ -d "$PROJECT/.git" || -f "$PROJECT/.git" ]] || fail "project is not a Git repository"

HELPER="$SCRIPT_DIR/workflow_snapshot.py"
[[ -f "$HELPER" ]] || fail "snapshot validation helper is missing"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

resolve_carryctx() {
	local candidate cargo_home
	if [[ -z "${CARRYCTX_BIN:-}" ]]; then
		CARRYCTX_BIN="/home/fuyu/.local/share/cargo/bin/carryctx"
	fi
	if [[ -n "${CARRYCTX_BIN:-}" ]]; then
		candidate="$CARRYCTX_BIN"
		if [[ "$candidate" != */* ]]; then
			candidate="$(command -v "$candidate" 2>/dev/null || true)"
		fi
		[[ -x "$candidate" ]] || fail "CARRYCTX_BIN is not executable or resolvable"
		printf '%s\n' "$candidate"
		return
	fi
	cargo_home="${CARGO_HOME:-$HOME/.cargo}"
	for candidate in "$cargo_home/bin/carryctx" "$HOME/.local/share/cargo/bin/carryctx"; do
		if [[ -x "$candidate" ]]; then
			printf '%s\n' "$candidate"
			return
		fi
	done
	fail "Cargo-managed carryctx 0.12.0 not found; set CARRYCTX_BIN explicitly"
}

CARRYCTX_BIN="$(resolve_carryctx)"
cc() { timeout "$TIMEOUT_SECS" "$CARRYCTX_BIN" "$@"; }
gitc() { timeout "$TIMEOUT_SECS" git -C "$PROJECT" "$@"; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/mathen-workflow-publish.XXXXXX")"

cc version --json >"$TMP/version.json" 2>/dev/null || fail "CarryCtx version probe failed"
python3 "$HELPER" capability "$TMP/version.json" >/dev/null || fail "CarryCtx 0.12.0 capability check failed"
export_help="$(cc export --help 2>/dev/null)" || fail "CarryCtx export capability probe failed"
import_help="$(cc import --help 2>/dev/null)" || fail "CarryCtx import capability probe failed"
grep -q -- '--publication' <<<"$export_help" || fail "CarryCtx lacks export --publication"
grep -q -- '--pack-format' <<<"$export_help" || fail "CarryCtx lacks pack-format capability"
grep -q 'dir' <<<"$export_help" || fail "CarryCtx lacks the required dir pack format"
grep -q -- '--dry-run' <<<"$export_help" || fail "CarryCtx lacks export --dry-run"
grep -q -- '--json' <<<"$export_help" || fail "CarryCtx lacks export JSON output"
grep -q -- '--dry-run' <<<"$import_help" || fail "CarryCtx lacks import --dry-run"
grep -q -- '--json' <<<"$import_help" || fail "CarryCtx lacks import JSON output"

CONFIG="$PROJECT/.carryctx/config.toml"
[[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail ".carryctx/config.toml must be a regular non-symlink file"
MAIN_BRANCH="$(python3 "$HELPER" config "$CONFIG")" || fail "invalid CarryCtx configuration"
PROJECT_ID="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["project"]["id"])' "$CONFIG")" || fail "missing CarryCtx project id"
repo_url="$(gitc remote get-url "$REMOTE" 2>/dev/null || true)"
if [[ "$(basename "$PROJECT")" != mathen && ! "$repo_url" =~ (^|[/:])mathen(\.git)?$ ]]; then
	fail "checkout basename is not mathen and remote does not prove the Mathen repository"
fi

branch="$(gitc branch --show-current)"
[[ "$branch" == "$MAIN_BRANCH" ]] || fail "source must be on configured main branch"
head_sha="$(gitc rev-parse HEAD)" || fail "cannot resolve source HEAD"
main_line="$(gitc ls-remote --refs "$REMOTE" "refs/heads/$MAIN_BRANCH" 2>/dev/null)" || fail "cannot resolve configured remote main"
remote_main="$(awk -v ref="refs/heads/$MAIN_BRANCH" '$2 == ref {print $1}' <<<"$main_line")"
[[ "$main_line" == "$(printf '%s\trefs/heads/%s' "$remote_main" "$MAIN_BRANCH")" ]] || fail "remote main response is malformed"
[[ "$remote_main" =~ ^[0-9a-f]{40}$ ]] || fail "remote main is not an immutable commit SHA"
[[ "$head_sha" == "$remote_main" ]] || fail "source main is stale relative to remote main"

remote_line=""
if ! remote_line="$(gitc ls-remote --refs "$REMOTE" "$PUB_REF" 2>/dev/null)"; then
	fail "snapshot ref lookup failed (remote/auth/network error)"
fi
remote_sha=""
if [[ -n "$remote_line" ]]; then
	remote_sha="$(awk -v ref="$PUB_REF" '$2 == ref {print $1}' <<<"$remote_line")"
	[[ "$remote_line" == "$(printf '%s\t%s' "$remote_sha" "$PUB_REF")" ]] || fail "remote snapshot ref response is malformed"
	[[ "$remote_sha" =~ ^[0-9a-f]{40}$ ]] || fail "remote snapshot ref is not an immutable commit SHA"
fi

before="$(gitc rev-parse -q --verify "$PUB_REF" 2>/dev/null || true)"
if [[ -n "$remote_sha" && -n "$before" && "$before" != "$remote_sha" ]]; then
	fail "local public snapshot ref diverges from remote; refusing to overwrite unpublished state"
fi
if [[ -z "$remote_sha" && -n "$before" ]]; then
	fail "local public snapshot ref exists but remote snapshot ref is missing; refusing unpublished local state"
fi
if [[ -n "$remote_sha" && -z "$before" && "$DRY_RUN" == 0 ]]; then
	gitc fetch --no-tags "$REMOTE" "$PUB_REF:$PUB_REF" >/dev/null 2>&1 || fail "cannot fast-forward local snapshot ref to remote"
	before="$(gitc rev-parse -q --verify "$PUB_REF" 2>/dev/null || true)"
	[[ "$before" == "$remote_sha" ]] || fail "local snapshot ref did not match remote after fetch"
fi

export_args=(export --pack-format dir --publication --project "$PROJECT" --output "$TMP/pack" --json)
((DRY_RUN)) && export_args+=(--dry-run)
cc "${export_args[@]}" >"$TMP/export.json" 2>/dev/null || fail "CarryCtx redacted publication export failed"

if ((DRY_RUN)); then
	python3 - "$TMP/export.json" "$TMP/dry-manifest.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
manifest = payload.get("data", {}).get("manifest")
if not isinstance(manifest, dict):
    raise SystemExit("missing export manifest")
json.dump(manifest, open(sys.argv[2], "w", encoding="utf-8"))
PY
	python3 "$HELPER" manifest "$TMP/dry-manifest.json" "$PROJECT_ID" >/dev/null || fail "dry-run publication manifest validation failed"
	after="$(gitc rev-parse -q --verify "$PUB_REF" 2>/dev/null || true)"
	[[ "$after" == "$before" ]] || fail "dry-run changed the local publication ref"
	log "dry-run PASS: redacted publication capability and source validated; no ref or remote mutation"
	exit 0
fi

after="$(gitc rev-parse -q --verify "$PUB_REF" 2>/dev/null || true)"
[[ "$after" =~ ^[0-9a-f]{40}$ ]] || fail "publication did not create an immutable commit SHA"
[[ -z "$before" || "$before" != "$after" ]] || fail "publication ref did not advance after export"
[[ -z "$remote_sha" || "$after" != "$remote_sha" ]] || fail "publication ref did not advance beyond remote tip"

gitc show "$after:manifest.json" >"$TMP/manifest.json" 2>/dev/null || fail "publication commit has no manifest.json"
export_id="$(python3 "$HELPER" manifest "$TMP/manifest.json" "$PROJECT_ID")" || fail "publication manifest validation failed"
gitc log -1 --format=%B "$after" >"$TMP/message" 2>/dev/null || fail "cannot read publication commit message"
source_token="$(python3 "$HELPER" provenance "$TMP/message" "$export_id")" || fail "publication provenance validation failed"
source_sha="$(gitc rev-parse "$source_token^{commit}" 2>/dev/null || true)"
[[ "$source_sha" == "$head_sha" ]] || fail "publication source SHA does not resolve to source HEAD"
manifest_source="$(python3 "$HELPER" manifest-source "$TMP/manifest.json" "$PROJECT_ID")" || fail "publication manifest source validation failed"
manifest_source_sha="$(gitc rev-parse "$manifest_source^{commit}" 2>/dev/null || true)"
[[ "$manifest_source_sha" == "$source_sha" ]] || fail "manifest source SHA does not match provenance"

log "local publication PASS: snapshot=${after:0:12} export_id=$export_id source=${source_sha:0:12}"
if ((PUSH)); then
	timeout "$TIMEOUT_SECS" git -C "$PROJECT" push "$REMOTE" "$after:$PUB_REF" >/dev/null 2>&1 || fail "snapshot push failed"
	pushed="$(gitc ls-remote --refs "$REMOTE" "$PUB_REF" 2>/dev/null | awk -v ref="$PUB_REF" '$2 == ref {print $1}')" || fail "snapshot push read-back failed"
	[[ "$pushed" == "$after" ]] || fail "remote snapshot SHA did not match validated immutable SHA"
	log "push PASS: snapshot=${after:0:12}"
else
	log "not pushed; use --push explicitly"
fi
