"""Deterministic repository inspection and draft Architecture Card generation."""

from __future__ import annotations

import http.client
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RepositoryAnalysisError(RuntimeError):
    """Raised when a repository cannot be inspected safely."""


@dataclass(frozen=True)
class RepositorySpec:
    """A repository and the revision selected for one analysis run."""

    id: str
    name: str
    category: str
    repository: str
    documentation: str
    ref: str
    priority: str


EXTENSION_LANGUAGES = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".go": "Go",
    ".h": "C/C++ headers",
    ".java": "Java",
    ".js": "JavaScript",
    ".kt": "Kotlin",
    ".py": "Python",
    ".rs": "Rust",
    ".sh": "Shell",
    ".sql": "SQL",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".yaml": "YAML",
    ".yml": "YAML",
}

PATH_SIGNAL_PATTERNS = {
    "storage": ("storage", "store", "database", "db", "wal", "log"),
    "networking": ("network", "net", "http", "rpc", "socket", "tcp"),
    "concurrency": ("thread", "async", "event", "scheduler", "worker"),
    "orchestration": ("controller", "operator", "scheduler", "reconcile"),
    "virtualization": ("vm", "kvm", "virtio", "hypervisor", "device"),
    "query-execution": ("query", "planner", "optimizer", "execution", "vector"),
    "compiler": ("compiler", "llvm", "ir", "parser", "ast", "codegen"),
    "media": ("codec", "filter", "mux", "demux", "avformat", "avcodec"),
}

IGNORE_DIRS = {".git", ".cache", "node_modules", "vendor", "target", "dist"}


def load_manifest(path: Path) -> list[RepositorySpec]:
    """Load and validate a deterministic repository manifest."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RepositoryAnalysisError(
            f"Cannot read manifest {path}: {error}"
        ) from error
    if not isinstance(raw, list):
        raise RepositoryAnalysisError(f"{path}: manifest must be a JSON array")

    specs: list[RepositorySpec] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise RepositoryAnalysisError(f"{path}: every repository must be an object")
        required = {
            "id",
            "name",
            "category",
            "repository",
            "documentation",
            "ref",
            "priority",
        }
        missing = required - item.keys()
        if missing:
            raise RepositoryAnalysisError(f"{path}: missing fields: {sorted(missing)}")
        spec = RepositorySpec(
            id=str(item["id"]),
            name=str(item["name"]),
            category=str(item["category"]),
            repository=str(item["repository"]),
            documentation=str(item["documentation"]),
            ref=str(item["ref"]),
            priority=str(item["priority"]),
        )
        if spec.id in seen or not spec.id.islower():
            raise RepositoryAnalysisError(f"{path}: duplicate or invalid id: {spec.id}")
        seen.add(spec.id)
        specs.append(spec)
    return specs


def analyze_manifest(
    manifest: Path,
    cache_dir: Path,
    output_dir: Path,
    limit: int | None = None,
    refresh: bool = False,
    priorities: set[str] | None = None,
    transport: str = "auto",
    continue_on_error: bool = False,
) -> list[Path]:
    """Clone repositories, inspect them, and write reports and draft cards."""

    specs = load_manifest(manifest)
    cache_dir = cache_dir.resolve()
    output_dir = output_dir.resolve()
    if priorities:
        specs = [spec for spec in specs if spec.priority in priorities]
    if limit is not None:
        specs = specs[:limit]
    if transport not in {"auto", "git", "archive"}:
        raise RepositoryAnalysisError(f"unsupported transport: {transport}")
    output_dir.mkdir(parents=True, exist_ok=True)
    analyses_dir = output_dir.parent / "analyses"
    analyses_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    failures: list[dict[str, str]] = []
    for spec in specs:
        try:
            checkout = checkout_repository(
                spec, cache_dir, refresh=refresh, transport=transport
            )
            report = inspect_repository(spec, checkout)
            (analyses_dir / f"{spec.id}.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            card_path = output_dir / f"{spec.id}.json"
            card_path.write_text(
                json.dumps(build_draft_card(spec, report), indent=2, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
            written.append(card_path)
        except RepositoryAnalysisError as error:
            if not continue_on_error:
                raise
            failures.append({"id": spec.id, "error": str(error)})
    failure_path = analyses_dir / "failures.json"
    if failures:
        failure_path.write_text(
            json.dumps(failures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    elif failure_path.exists():
        failure_path.unlink()
    return written


def checkout_repository(
    spec: RepositorySpec,
    cache_dir: Path,
    *,
    refresh: bool = False,
    transport: str = "auto",
) -> Path:
    """Clone or refresh one shallow checkout and return its working tree."""

    cache_dir = cache_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    checkout = cache_dir / spec.id
    if transport == "archive":
        if not refresh and _archive_cache_matches(checkout, spec):
            return checkout
        return checkout_archive(spec, cache_dir)
    try:
        if (checkout / ".git").exists() and not refresh:
            _run_git(checkout, "rev-parse", "HEAD")
        elif (checkout / ".git").exists():
            _run_git(
                checkout,
                "fetch",
                "--depth=1",
                "--filter=blob:none",
                "--no-tags",
                "origin",
                spec.ref,
            )
            _run_git(checkout, "update-ref", "refs/heads/mathen-analysis", "FETCH_HEAD")
            _run_git(checkout, "symbolic-ref", "HEAD", "refs/heads/mathen-analysis")
        else:
            if checkout.exists():
                raise RepositoryAnalysisError(
                    f"Refusing to use non-Git cache directory: {checkout}"
                )
            _run_git(
                cache_dir,
                "clone",
                "--depth=1",
                "--filter=blob:none",
                "--no-tags",
                "--no-checkout",
                "--branch",
                spec.ref,
                spec.repository,
                str(checkout),
            )
        return checkout
    except RepositoryAnalysisError as git_error:
        if transport == "git" or not _is_github_repository(spec.repository):
            raise
        if not refresh and _archive_cache_matches(checkout, spec):
            return checkout
        if checkout.exists() and not (checkout / ".git").exists():
            shutil.rmtree(checkout)
        try:
            return checkout_archive(spec, cache_dir)
        except RepositoryAnalysisError as archive_error:
            raise RepositoryAnalysisError(
                f"Git transport failed: {git_error}; archive fallback failed: "
                f"{archive_error}"
            ) from archive_error


def checkout_archive(spec: RepositorySpec, cache_dir: Path) -> Path:
    """Download a GitHub source archive and record its resolved commit."""

    parsed = urllib.parse.urlparse(spec.repository)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if parsed.netloc != "github.com" or len(parts) != 2:
        raise RepositoryAnalysisError(
            f"Archive fallback supports github.com repositories only: {spec.repository}"
        )
    owner, repository = parts[0], parts[1].removesuffix(".git")
    encoded_ref = urllib.parse.quote(spec.ref, safe="")
    api_url = f"https://api.github.com/repos/{owner}/{repository}/commits/{encoded_ref}"
    try:
        commit_data = _read_json_url(api_url)
        commit = str(commit_data["sha"])
    except (KeyError, TypeError, RepositoryAnalysisError) as error:
        raise RepositoryAnalysisError(f"cannot resolve {spec.ref}: {error}") from error

    archive_url = (
        f"https://codeload.github.com/{owner}/{repository}/tar.gz/"
        f"{urllib.parse.quote(commit, safe='')}"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    checkout = cache_dir / spec.id
    with tempfile.TemporaryDirectory(dir=cache_dir, prefix=f".{spec.id}-") as temporary:
        archive_path = Path(temporary) / "source.tar.gz"
        try:
            _download_url(archive_url, archive_path)
            extract_dir = Path(temporary) / "extracted"
            extract_dir.mkdir()
            with tarfile.open(archive_path, mode="r:gz") as archive:
                _safe_extract(archive, extract_dir)
            roots = [path for path in extract_dir.iterdir() if path.is_dir()]
            if len(roots) != 1:
                raise RepositoryAnalysisError(
                    "archive has an unexpected top-level layout"
                )
            metadata = {
                "commit": commit,
                "repository": spec.repository,
                "requested_ref": spec.ref,
                "source": "github-archive",
            }
            (roots[0] / ".mathen-repository.json").write_text(
                json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
            )
            if checkout.exists():
                shutil.rmtree(checkout)
            roots[0].rename(checkout)
        except (OSError, tarfile.TarError, urllib.error.URLError) as error:
            raise RepositoryAnalysisError(
                f"archive download/extraction failed: {error}"
            ) from error
    return checkout


def inspect_repository(spec: RepositorySpec, checkout: Path) -> dict[str, Any]:
    """Extract reproducible observations without assigning semantic meaning."""

    paths = _repository_paths(checkout)
    extensions = Counter(
        Path(path).suffix.lower() for path in paths if Path(path).suffix
    )
    languages = Counter(
        EXTENSION_LANGUAGES[Path(path).suffix.lower()]
        for path in paths
        if Path(path).suffix.lower() in EXTENSION_LANGUAGES
    )
    top_level = sorted({path.split("/", maxsplit=1)[0] for path in paths if path})
    markers = sorted(
        marker
        for marker in (
            "CMakeLists.txt",
            "Cargo.toml",
            "Dockerfile",
            "Makefile",
            "WORKSPACE",
            "go.mod",
            "pom.xml",
            "pyproject.toml",
            "setup.py",
        )
        if marker in paths
    )
    readme_paths = [
        path for path in paths if Path(path).name.lower().startswith("readme")
    ]
    path_signals = _path_signals(paths)
    commit = _repository_commit(checkout)
    provenance = _repository_provenance(checkout)
    return {
        "analysis_version": 2,
        "system_id": spec.id,
        "system_name": spec.name,
        "category": spec.category,
        "priority": spec.priority,
        "repository": spec.repository,
        "documentation": spec.documentation,
        "requested_ref": spec.ref,
        "commit": commit,
        "provenance": provenance,
        "commit_url": f"{spec.repository.removesuffix('.git')}/commit/{commit}",
        "analyzed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "file_count": len(paths),
        "top_level_entries": top_level,
        "language_counts": dict(sorted(languages.items())),
        "extension_counts": dict(sorted(extensions.items())),
        "build_markers": markers,
        "readme_paths": readme_paths[:10],
        "path_signals": path_signals,
    }


def build_draft_card(spec: RepositorySpec, report: dict[str, Any]) -> dict[str, Any]:
    """Turn observations into conservative, evidence-backed draft hypotheses."""

    source_url = report["commit_url"]
    provenance = report.get("provenance", "unknown")
    evidence = [
        {
            "id": "repository-commit",
            "kind": "source-code",
            "title": f"{spec.name} source at {report['commit'][:12]}",
            "uri": source_url,
            "accessed": report["analyzed_at"],
            "notes": (
                "Generated from a "
                f"{provenance} checkout by the deterministic inspector."
            ),
        },
        {
            "id": "official-documentation",
            "kind": "official-doc",
            "title": f"{spec.name} official documentation",
            "uri": spec.documentation,
            "accessed": report["analyzed_at"],
        },
    ]
    languages = ", ".join(report["language_counts"].keys()) or "unknown languages"
    signals = ", ".join(report.get("path_signals", {}).keys()) or "none detected"
    features = [
        {
            "id": "repository-structure",
            "name": "Observable repository structure",
            "category": "repository-model",
            "claim_type": "fact",
            "description": (
                f"The inspected revision contains {report['file_count']} files, "
                f"top-level entries "
                f"{', '.join(report['top_level_entries'][:12]) or 'none'}, "
                f"and source languages including {languages}."
            ),
            "benefits": ["Provides a reproducible baseline for later modeling."],
            "costs": [
                "Repository metrics do not by themselves explain runtime behavior."
            ],
            "evidence_ids": ["repository-commit"],
        },
        {
            "id": "architecture-path-signals",
            "name": "Architecture-related path signals",
            "category": "architecture-evidence",
            "claim_type": "inference",
            "description": (
                "Path names contain these weak, non-semantic signals: "
                f"{signals}. They identify targets for source review, not proof "
                "of runtime architecture."
            ),
            "benefits": ["Prioritizes files for evidence-backed semantic analysis."],
            "costs": ["Names can be historical, incidental, or misleading."],
            "evidence_ids": ["repository-commit"],
        },
        {
            "id": "build-and-integration-surface",
            "name": "Build and integration surface",
            "category": "tooling-model",
            "claim_type": "fact",
            "description": (
                "The revision exposes these root build markers: "
                f"{', '.join(report['build_markers']) or 'no recognized markers'}."
            ),
            "benefits": [
                "Identifies the first deterministic entry points for deeper analysis."
            ],
            "costs": [
                "A marker is evidence of a tool, not proof of the complete "
                "build architecture."
            ],
            "evidence_ids": ["repository-commit"],
        },
    ]
    return {
        "id": spec.id,
        "name": spec.name,
        "version_context": f"commit {report['commit']}",
        "summary": (
            f"Draft architecture card generated from {spec.name} at commit "
            f"{report['commit'][:12]} via {provenance}. "
            "Semantic features require review."
        ),
        "scope": [
            spec.category,
            "repository structure",
            "build surface",
            "path-level architecture signals",
            "initial evidence",
        ],
        "features": features,
        "mathematical_views": [
            {
                "model": "Finite labeled repository graph",
                "question": (
                    "What observable source and build entities are present at "
                    "this revision?"
                ),
                "assumptions": [
                    "The checkout is complete enough for structural inspection.",
                    "File paths and recognized markers are useful but incomplete "
                    "proxies for architecture.",
                ],
                "claim_type": "inference",
                "evidence_ids": ["repository-commit"],
            },
            {
                "model": "Evidence-prioritization signal model",
                "question": (
                    "Which source paths should be inspected first for "
                    "architecture evidence?"
                ),
                "assumptions": [
                    "Path names are weak indicators and require source or "
                    "documentation review.",
                    "Signal counts are useful for prioritization, not "
                    "semantic classification.",
                ],
                "claim_type": "hypothesis",
                "evidence_ids": ["repository-commit"],
            },
        ],
        "trade_offs": [
            {
                "feature_id": "repository-structure",
                "benefits": ["Makes later analysis reproducible and comparable."],
                "costs": ["Static counts cannot establish semantic guarantees."],
            },
            {
                "feature_id": "build-and-integration-surface",
                "benefits": ["Provides concrete next locations for source analysis."],
                "costs": ["Build metadata can vary by platform and configuration."],
            },
            {
                "feature_id": "architecture-path-signals",
                "benefits": ["Reduces the search space for later LLM-assisted review."],
                "costs": [
                    "Heuristic signals can create false positives and false negatives."
                ],
            },
        ],
        "evidence": evidence,
        "related_systems": [],
    }


def _repository_paths(checkout: Path) -> list[str]:
    """Read tracked paths without materializing the repository worktree."""

    if (checkout / ".git").exists():
        output = _run_git(checkout, "ls-tree", "-r", "--name-only", "HEAD")
        return sorted(path for path in output.splitlines() if path)
    paths: list[str] = []
    for root, directories, filenames in os.walk(checkout):
        directories[:] = sorted(
            directory for directory in directories if directory not in IGNORE_DIRS
        )
        for filename in sorted(filenames):
            relative = Path(root, filename).relative_to(checkout)
            if relative.name == ".mathen-repository.json":
                continue
            paths.append(relative.as_posix())
    return sorted(paths)


def _path_signals(paths: list[str]) -> dict[str, int]:
    """Count conservative architecture-related tokens in tracked paths."""

    signals: dict[str, int] = {}
    for category, tokens in PATH_SIGNAL_PATTERNS.items():
        count = sum(
            1
            for path in paths
            if any(token in path.lower().split("/") for token in tokens)
        )
        if count:
            signals[category] = count
    return dict(sorted(signals.items()))


def _repository_commit(checkout: Path) -> str:
    if (checkout / ".git").exists():
        return _run_git(checkout, "rev-parse", "HEAD")
    try:
        metadata = json.loads(
            (checkout / ".mathen-repository.json").read_text(encoding="utf-8")
        )
        return str(metadata["commit"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise RepositoryAnalysisError(
            f"missing repository commit metadata: {error}"
        ) from error


def _repository_provenance(checkout: Path) -> str:
    """Return the acquisition method used for a cached repository."""

    if (checkout / ".git").exists():
        return "git"
    try:
        metadata = json.loads(
            (checkout / ".mathen-repository.json").read_text(encoding="utf-8")
        )
        return str(metadata["source"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise RepositoryAnalysisError(
            f"missing repository provenance metadata: {error}"
        ) from error


def _archive_cache_matches(checkout: Path, spec: RepositorySpec) -> bool:
    """Check whether an archive cache was created for the requested ref."""

    metadata_path = checkout / ".mathen-repository.json"
    if not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        isinstance(metadata, dict)
        and metadata.get("repository") == spec.repository
        and metadata.get("requested_ref") == spec.ref
        and isinstance(metadata.get("commit"), str)
    )


def _is_github_repository(repository: str) -> bool:
    return urllib.parse.urlparse(repository).netloc == "github.com"


def _read_json_url(url: str) -> dict[str, Any]:
    try:
        payload = _read_url_bytes(url, timeout=30)
    except RepositoryAnalysisError as error:
        raise RepositoryAnalysisError(str(error)) from error
    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise RepositoryAnalysisError(f"invalid JSON response: {error}") from error
    if not isinstance(data, dict):
        raise RepositoryAnalysisError("JSON response must be an object")
    return data


def _download_url(url: str, destination: Path) -> None:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with (
                _open_url(url, timeout=120) as response,
                destination.open("wb") as output,
            ):
                shutil.copyfileobj(response, output)
            return
        except (
            OSError,
            TimeoutError,
            http.client.HTTPException,
            urllib.error.URLError,
        ) as error:
            last_error = error
            if attempt + 1 < 3:
                time.sleep(1)
    raise RepositoryAnalysisError(
        f"download failed after 3 attempts: {last_error}"
    ) from last_error


def _read_url_bytes(url: str, *, timeout: int, attempts: int = 3) -> bytes:
    """Read an HTTP response with bounded retries for interrupted transfers."""

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with _open_url(url, timeout=timeout) as response:
                return response.read()
        except (
            OSError,
            TimeoutError,
            http.client.HTTPException,
            urllib.error.URLError,
        ) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(1)
    raise RepositoryAnalysisError(
        f"download failed after {attempts} attempts: {last_error}"
    ) from last_error


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if target != root and root not in target.parents:
            raise RepositoryAnalysisError(f"unsafe archive path: {member.name}")
    archive.extractall(destination, filter="data")


def _open_url(url: str, *, timeout: int) -> Any:
    """Open a URL using NETWORK_PROXY when the environment provides one."""

    proxy = os.environ.get("NETWORK_PROXY")
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
        return opener.open(url, timeout=timeout)
    return urllib.request.urlopen(url, timeout=timeout)


def _run_git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired as error:
        raise RepositoryAnalysisError(
            f"git {' '.join(args)} timed out after 90 seconds"
        ) from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RepositoryAnalysisError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()
