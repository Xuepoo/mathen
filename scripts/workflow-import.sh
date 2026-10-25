#!/usr/bin/env bash
# Import only the validated redacted CarryCtx lifecycle publication.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
SNAP_REF="refs/heads/carryctx-snapshots"
REMOTE="${WORKFLOW_REMOTE:-origin}"
TIMEOUT_SECS="${WORKFLOW_GIT_TIMEOUT:-${GIT_TIMEOUT:-120}}"
DRY_RUN=0
FORCE=0
TMP=""
CONFIG_BACKUP=""
CONFIG_ACTIVE=0

usage() {
	cat <<'EOF'
Usage: scripts/workflow-import.sh [--dry-run] [--force] [--project DIR]
       [--remote NAME] [--git-timeout SECONDS]

Fetch and validate the exact commit at refs/heads/carryctx-snapshots, then
restore CarryCtx state. A non-empty or active local DB requires operator review;
--force permits replacement only after the active-state guard passes.
EOF
}

fail() {
	echo "workflow-import: FAIL: $*" >&2
	exit 1
}

log() { echo "workflow-import: $*"; }

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
	--force)
		FORCE=1
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

TMP="$(mktemp -d "${TMPDIR:-/tmp}/mathen-workflow-import.XXXXXX")"
CONFIG="$PROJECT/.carryctx/config.toml"
[[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail ".carryctx/config.toml must be a regular non-symlink file"
MAIN_BRANCH="$(python3 "$HELPER" config "$CONFIG")" || fail "invalid CarryCtx configuration"
PROJECT_ID="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["project"]["id"])' "$CONFIG")" || fail "missing CarryCtx project id"
repo_url="$(gitc remote get-url "$REMOTE" 2>/dev/null || true)"
if [[ "$(basename "$PROJECT")" != mathen && ! "$repo_url" =~ (^|[/:])mathen(\.git)?$ ]]; then
	fail "checkout basename is not mathen and remote does not prove the Mathen repository"
fi

cc version --json >"$TMP/version.json" 2>/dev/null || fail "CarryCtx version probe failed"
python3 "$HELPER" capability "$TMP/version.json" >/dev/null || fail "CarryCtx 0.12.0 capability check failed"
export_help="$(cc export --help 2>/dev/null)" || fail "CarryCtx export capability probe failed"
import_help="$(cc import --help 2>/dev/null)" || fail "CarryCtx import capability probe failed"
grep -q -- '--publication' <<<"$export_help" || fail "CarryCtx lacks publication capability"
grep -q -- '--pack-format' <<<"$export_help" || fail "CarryCtx lacks pack-format capability"
grep -q 'dir' <<<"$export_help" || fail "CarryCtx lacks the required dir pack format"
grep -q -- '--dry-run' <<<"$export_help" || fail "CarryCtx lacks export dry-run capability"
grep -q -- '--json' <<<"$export_help" || fail "CarryCtx lacks export JSON capability"
grep -q -- '--from-git' <<<"$import_help" || fail "CarryCtx lacks exact Git import capability"
grep -q -- '--dry-run' <<<"$import_help" || fail "CarryCtx lacks import dry-run capability"
grep -q -- '--mode' <<<"$import_help" || fail "CarryCtx lacks import mode capability"
grep -q -- '--json' <<<"$import_help" || fail "CarryCtx lacks import JSON capability"

DB="$(gitc rev-parse --path-format=absolute --git-common-dir)/carryctx/state.sqlite" || fail "cannot locate shared CarryCtx DB"
COMMON_DIR="$(gitc rev-parse --path-format=absolute --git-common-dir)"
read_db_state() {
	python3 "$HELPER" db "$DB" "$PROJECT_ID" "$PROJECT" "$COMMON_DIR"
}

state_before="$(read_db_state)" || fail "cannot inspect local CarryCtx DB"
data_rows="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("data_rows", 0))' <<<"$state_before")"
active_state="$(python3 -c 'import json,sys; print(";".join(json.load(sys.stdin)["active"]))' <<<"$state_before")"
if [[ -n "$active_state" ]]; then
	if ((DRY_RUN)); then
		log "active local state detected; dry-run will not replace the DB"
	else
		fail "active CarryCtx session/operation state prevents DB replacement"
	fi
fi
if ((DRY_RUN == 0 && data_rows > 0 && FORCE == 0)); then
	fail "local CarryCtx DB is non-empty; refusing overwrite without --force"
fi

remote_line=""
if ! remote_line="$(gitc ls-remote --refs "$REMOTE" "$SNAP_REF" 2>/dev/null)"; then
	fail "snapshot ref lookup failed (remote/auth/network error)"
fi
if [[ -z "$remote_line" ]]; then
	fail "snapshot ref is genuinely missing on remote"
fi
remote_sha="$(awk -v ref="$SNAP_REF" '$2 == ref {print $1}' <<<"$remote_line")"
[[ "$remote_line" == "$(printf '%s\t%s' "$remote_sha" "$SNAP_REF")" ]] || fail "snapshot ref response is malformed"
[[ "$remote_sha" =~ ^[0-9a-f]{40}$ ]] || fail "snapshot ref is not an immutable commit SHA"

# Fetch only the requested ref into Git's object store/FETCH_HEAD. No branch,
# tag, remote-tracking ref, worktree, or snapshot ref is created or replaced.
gitc fetch --no-tags --no-write-fetch-head "$REMOTE" "$SNAP_REF" >/dev/null 2>&1 || fail "snapshot fetch failed after remote lookup"
remote_after_fetch="$(gitc ls-remote --refs "$REMOTE" "$SNAP_REF" 2>/dev/null | awk -v ref="$SNAP_REF" '$2 == ref {print $1}')" || fail "snapshot read-back failed after fetch"
[[ "$remote_after_fetch" == "$remote_sha" ]] || fail "snapshot changed during fetch; refusing a moving target"
snapshot_sha="$remote_sha"
gitc cat-file -e "$snapshot_sha^{commit}" || fail "snapshot commit cannot be resolved"
gitc show "$snapshot_sha:manifest.json" >"$TMP/manifest.json" 2>/dev/null || fail "snapshot commit has no manifest.json"
export_id="$(python3 "$HELPER" manifest "$TMP/manifest.json" "$PROJECT_ID")" || fail "snapshot manifest validation failed"
gitc log -1 --format=%B "$snapshot_sha" >"$TMP/message" 2>/dev/null || fail "cannot read snapshot commit message"
source_token="$(python3 "$HELPER" provenance "$TMP/message" "$export_id")" || fail "snapshot provenance validation failed"
manifest_source="$(python3 "$HELPER" manifest-source "$TMP/manifest.json" "$PROJECT_ID")" || fail "snapshot manifest source validation failed"
main_line="$(gitc ls-remote --refs "$REMOTE" "refs/heads/$MAIN_BRANCH" 2>/dev/null)" || fail "cannot resolve configured remote main for provenance verification"
remote_main="$(awk -v ref="refs/heads/$MAIN_BRANCH" '$2 == ref {print $1}' <<<"$main_line")"
[[ "$main_line" == "$(printf '%s\trefs/heads/%s' "$remote_main" "$MAIN_BRANCH")" ]] || fail "remote main response is malformed"
[[ "$remote_main" =~ ^[0-9a-f]{40}$ ]] || fail "remote main is not an immutable commit SHA"
gitc fetch --no-tags --no-write-fetch-head "$REMOTE" "refs/heads/$MAIN_BRANCH" >/dev/null 2>&1 || fail "cannot fetch configured remote main objects"
source_sha="$(gitc rev-parse "$source_token^{commit}" 2>/dev/null || true)"
[[ "$source_sha" =~ ^[0-9a-f]{40}$ ]] || fail "snapshot source SHA does not resolve in this repository"
manifest_source_sha="$(gitc rev-parse "$manifest_source^{commit}" 2>/dev/null || true)"
[[ "$manifest_source_sha" == "$source_sha" ]] || fail "manifest source SHA does not match provenance"
gitc merge-base --is-ancestor "$source_sha" "$remote_main" || fail "snapshot source SHA is not reachable from configured main"

log "provenance: snapshot=${snapshot_sha:0:12} export_id=$export_id source=${source_sha:0:12}"

if ((DRY_RUN)); then
	cc import --from-git "$snapshot_sha" --mode replace --yes --project "$PROJECT" --dry-run --json >"$TMP/import-dry-run.json" 2>"$TMP/import-dry-run.err" || {
		cat "$TMP/import-dry-run.err" >&2
		fail "CarryCtx import --dry-run rejected the exact snapshot commit"
	}
	# The preflight is deliberately read-only. It may create Git objects, but it
	# must not replace the shared DB or the local public ref.
	state_after="$(read_db_state)" || fail "cannot re-read local DB after dry-run"
	[[ "$state_after" == "$state_before" ]] || fail "dry-run changed local CarryCtx DB state"
	log "dry-run PASS: exact snapshot validated; local DB and refs not replaced"
	exit 0
fi

# Re-read identity and active state immediately before any init/replace. This
# closes the race between the first inspection and the mutating CarryCtx call.
state_before_replace="$(read_db_state)" || fail "cannot re-read local CarryCtx DB before replacement"
active_state="$(python3 -c 'import json,sys; print(";".join(json.load(sys.stdin)["active"]))' <<<"$state_before_replace")"
[[ -z "$active_state" ]] || fail "active CarryCtx state appeared before DB replacement"
data_rows="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["data_rows"])' <<<"$state_before_replace")"
if ((data_rows > 0 && FORCE == 0)); then
	fail "local CarryCtx DB became non-empty before replacement; use --force after review"
fi

CONFIG_BACKUP="$TMP/config.toml.before"
cp --preserve=all "$CONFIG" "$CONFIG_BACKUP" || fail "cannot back up CarryCtx config"
CONFIG_ACTIVE=1
restore_config() {
	[[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail "config path became non-regular during import; refusing unsafe restore"
	if ((CONFIG_ACTIVE)) && ! cmp -s "$CONFIG_BACKUP" "$CONFIG"; then
		cp --preserve=all "$CONFIG_BACKUP" "$CONFIG" || fail "cannot restore CarryCtx config after import"
	fi
}

if ((data_rows == 0)); then
	cc init --non-interactive --project "$PROJECT" >"$TMP/init.log" 2>&1 || {
		cat "$TMP/init.log" >&2
		restore_config
		fail "CarryCtx init failed"
	}
fi

# Revalidate after init as well: initialization must not have raced an active
# shared session, and the project identity must remain the same.
state_after_init="$(read_db_state)" || {
	restore_config
	fail "cannot inspect DB after init"
}
active_state="$(python3 -c 'import json,sys; print(";".join(json.load(sys.stdin)["active"]))' <<<"$state_after_init")"
[[ -z "$active_state" ]] || {
	restore_config
	fail "active CarryCtx state appeared during initialization"
}

if ! cc import --from-git "$snapshot_sha" --mode replace --yes --project "$PROJECT" --json >"$TMP/import.json" 2>"$TMP/import.err"; then
	restore_config
	fail "CarryCtx import failed; config restore was attempted"
fi
restore_config
CONFIG_ACTIVE=0
cmp -s "$CONFIG_BACKUP" "$CONFIG" || fail "CarryCtx config was not restored byte-identically"
log "restore PASS: snapshot=${snapshot_sha:0:12}; config restored byte-identically"
