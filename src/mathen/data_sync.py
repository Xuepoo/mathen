"""Safe synchronization of reviewed Architecture Cards for installed users."""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .cards import (
    CardValidationError,
    discover_cards,
    load_card,
    validate_card_collection,
)
from .config import MathenConfig

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
SYNC_METADATA = ".mathen-sync.json"


class SyncError(RuntimeError):
    """Raised when reviewed-card synchronization fails safely."""


@dataclass(frozen=True)
class SyncStatus:
    directory: Path
    card_count: int
    source: str | None
    ref: str | None
    digest: str | None
    valid: bool = True
    error: str | None = None


def sync_reviewed_cards(config: MathenConfig, source: str | None = None) -> SyncStatus:
    """Download and atomically replace only the reviewed cards directory."""

    target = config.paths.cards_dir
    canonical_cards = (Path(__file__).parents[2] / "data" / "systems").resolve()
    try:
        target_resolved = target.resolve()
    except OSError as error:
        raise SyncError(f"cannot resolve reviewed-card target: {error}") from error
    if target_resolved == canonical_cards:
        raise SyncError(
            "refusing to replace the repository's canonical cards; configure a "
            "user data directory first"
        )
    url = source or config.sync.source
    archive = _download(url)
    with tempfile.TemporaryDirectory(prefix="mathen-sync-") as temporary:
        extracted = Path(temporary) / "extracted"
        extracted.mkdir()
        try:
            with tarfile.open(fileobj=archive, mode="r:gz") as tar:
                _safe_extract_cards(tar, extracted)
        except (tarfile.TarError, OSError) as error:
            raise SyncError(f"could not extract reviewed cards: {error}") from error
        cards = discover_cards(extracted)
        if not cards:
            raise SyncError("sync archive contained no reviewed Architecture Cards")
        try:
            loaded = [load_card(path) for path in cards]
            validate_card_collection(loaded)
        except CardValidationError as error:
            raise SyncError(f"synced cards failed validation: {error}") from error
        digest = _cards_digest(cards)
        metadata = {
            "source": url,
            "ref": config.sync.ref,
            "digest": digest,
            "card_count": len(cards),
        }
        (extracted / SYNC_METADATA).write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not target.is_dir():
            raise SyncError(f"reviewed-card target is not a directory: {target}")
        replacement = target.with_name(f".{target.name}.new")
        if replacement.exists():
            shutil.rmtree(replacement)
        shutil.copytree(extracted, replacement)
        backup = target.with_name(f".{target.name}.old")
        if backup.exists():
            shutil.rmtree(backup)
        moved_target = False
        try:
            if target.exists():
                target.rename(backup)
                moved_target = True
            replacement.rename(target)
        except OSError as error:
            if moved_target and target.exists() and target.is_dir():
                shutil.rmtree(target)
            if moved_target and backup.exists() and not target.exists():
                backup.rename(target)
            raise SyncError(f"could not replace reviewed cards: {error}") from error
        if backup.exists():
            shutil.rmtree(backup)
    return status(config)


def status(config: MathenConfig) -> SyncStatus:
    """Read local reviewed-card synchronization state."""

    directory = config.paths.cards_dir
    cards = discover_cards(directory) if directory.is_dir() else []
    metadata_path = directory / SYNC_METADATA
    metadata: dict[str, object] = {}
    error: str | None = None
    if metadata_path.is_file():
        try:
            parsed = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                metadata = parsed
            else:
                error = "synchronization metadata is not an object"
        except (OSError, json.JSONDecodeError):
            error = "synchronization metadata is unreadable"
    valid = bool(cards)
    if error:
        valid = False
    if not cards:
        error = "no reviewed Architecture Cards found"
    if cards:
        try:
            actual_digest = _cards_digest(cards)
            loaded = [load_card(path) for path in cards]
            validate_card_collection(loaded)
        except (CardValidationError, OSError) as validation_error:
            valid = False
            error = str(validation_error)
            actual_digest = None
    else:
        actual_digest = None
    if metadata:
        expected_count = metadata.get("card_count")
        expected_digest = metadata.get("digest")
        if isinstance(expected_count, int) and expected_count != len(cards):
            valid = False
            error = "card count differs from synchronization metadata"
        if isinstance(expected_digest, str) and expected_digest != actual_digest:
            valid = False
            error = "card digest differs from synchronization metadata"
    return SyncStatus(
        directory=directory,
        card_count=len(cards),
        source=metadata.get("source")
        if isinstance(metadata.get("source"), str)
        else None,
        ref=metadata.get("ref") if isinstance(metadata.get("ref"), str) else None,
        digest=metadata.get("digest")
        if isinstance(metadata.get("digest"), str)
        else None,
        valid=valid,
        error=error,
    )


def _download(url: str):
    request = Request(
        url, headers={"Accept": "application/gzip", "User-Agent": "mathen-cli"}
    )
    try:
        with urlopen(request, timeout=60) as response:
            try:
                length = int(response.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise SyncError(
                    "sync source returned an invalid content length"
                ) from error
            if length > MAX_ARCHIVE_BYTES:
                raise SyncError("sync archive exceeds the 100 MB limit")
            from io import BytesIO

            data = BytesIO()
            while True:
                chunk = response.read(
                    min(1024 * 1024, MAX_ARCHIVE_BYTES + 1 - data.tell())
                )
                if not chunk:
                    break
                data.write(chunk)
                if data.tell() > MAX_ARCHIVE_BYTES:
                    raise SyncError("sync archive exceeds the 100 MB limit")
            data.seek(0)
    except HTTPError as error:
        raise SyncError(f"sync source returned HTTP {error.code}") from error
    except URLError as error:
        raise SyncError(f"sync source request failed: {error.reason}") from error
    except TimeoutError as error:
        raise SyncError("sync source request timed out") from error
    except OSError as error:
        raise SyncError(f"sync source request failed: {error}") from error
    return data


def _safe_extract_cards(tar: tarfile.TarFile, destination: Path) -> None:
    names: set[str] = set()
    total_size = 0
    for member in tar.getmembers():
        parts = PurePosixPath(member.name).parts
        if not parts or parts[0] == "/" or ".." in parts or "\\" in member.name:
            raise SyncError("sync archive contains an unsafe path")
        if len(parts) < 3 or parts[-2] != "systems" or not parts[-1].endswith(".json"):
            continue
        if not member.isfile() or ".." in parts:
            raise SyncError("sync archive contains an unsafe card entry")
        if member.size < 0 or member.size > MAX_ARCHIVE_BYTES:
            raise SyncError("sync archive card entry exceeds the 100 MB limit")
        name = parts[-1]
        if name in names:
            raise SyncError(f"sync archive contains duplicate card: {name}")
        names.add(name)
        total_size += member.size
        if total_size > MAX_ARCHIVE_BYTES:
            raise SyncError("sync archive cards exceed the 100 MB limit")
        target = destination / name
        with tar.extractfile(member) as source:
            if source is None:
                raise SyncError(f"sync archive entry is unreadable: {member.name}")
            content = source.read(member.size + 1)
            if len(content) > member.size:
                raise SyncError(f"sync archive entry is unreadable: {member.name}")
            target.write_bytes(content)


def _cards_digest(cards: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(cards):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
