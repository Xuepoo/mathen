"""Safe synchronization of reviewed Architecture Cards for installed users."""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
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


def sync_reviewed_cards(config: MathenConfig, source: str | None = None) -> SyncStatus:
    """Download and atomically replace only the reviewed cards directory."""

    target = config.paths.cards_dir
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
        replacement = target.with_name(f".{target.name}.new")
        if replacement.exists():
            shutil.rmtree(replacement)
        shutil.copytree(extracted, replacement)
        backup = target.with_name(f".{target.name}.old")
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.rename(backup)
        replacement.rename(target)
        if backup.exists():
            shutil.rmtree(backup)
    return status(config)


def status(config: MathenConfig) -> SyncStatus:
    """Read local reviewed-card synchronization state."""

    directory = config.paths.cards_dir
    cards = discover_cards(directory) if directory.is_dir() else []
    metadata_path = directory / SYNC_METADATA
    metadata: dict[str, object] = {}
    if metadata_path.is_file():
        try:
            parsed = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                metadata = parsed
        except (OSError, json.JSONDecodeError):
            pass
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
    )


def _download(url: str):
    request = Request(
        url, headers={"Accept": "application/gzip", "User-Agent": "mathen-cli"}
    )
    try:
        response = urlopen(request, timeout=60)
        length = int(response.headers.get("Content-Length", "0"))
        if length > MAX_ARCHIVE_BYTES:
            raise SyncError("sync archive exceeds the 100 MB limit")
        from io import BytesIO

        data = response.read(MAX_ARCHIVE_BYTES + 1)
    except HTTPError as error:
        raise SyncError(f"sync source returned HTTP {error.code}") from error
    except URLError as error:
        raise SyncError(f"sync source request failed: {error.reason}") from error
    except TimeoutError as error:
        raise SyncError("sync source request timed out") from error
    if len(data) > MAX_ARCHIVE_BYTES:
        raise SyncError("sync archive exceeds the 100 MB limit")
    return BytesIO(data)


def _safe_extract_cards(tar: tarfile.TarFile, destination: Path) -> None:
    for member in tar.getmembers():
        parts = Path(member.name).parts
        if len(parts) < 3 or parts[-2] != "systems" or not parts[-1].endswith(".json"):
            continue
        if not member.isfile() or ".." in parts:
            raise SyncError("sync archive contains an unsafe card entry")
        target = destination / parts[-1]
        with tar.extractfile(member) as source:
            if source is None:
                raise SyncError(f"sync archive entry is unreadable: {member.name}")
            target.write_bytes(source.read(MAX_ARCHIVE_BYTES))


def _cards_digest(cards: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(cards):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
