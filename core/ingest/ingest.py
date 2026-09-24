"""Fail-closed intake and preservation of source files.

Masters are copied as bytes and never rewritten. Generated names contain only
Core IDs; descriptive or date-bearing filenames are not accepted at intake.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.registry import IdRegistry, RegistryError
from core.schema import SchemaError, validate_record

SAFE_INTAKE_NAME = re.compile(r"^[A-Z][A-Z0-9]{1,7}-[0-9]{6}\.[a-z0-9]{1,8}$")
ASCII_ID = re.compile(r"^(?:FX-)?[A-Z][A-Z0-9]*-[0-9]{6}$")


class IngestError(ValueError):
    """Raised when an intake batch cannot be preserved safely."""


@dataclass(frozen=True)
class IngestItem:
    source_path: Path
    sidecar_path: Path
    source_id: str | None = None
    copyright_notice: str | None = None
    attribution: str | None = None


@dataclass(frozen=True)
class IngestResult:
    receipt_id: str
    asset_ids: tuple[str, ...]
    receipt_path: Path
    manifest_paths: tuple[Path, ...]
    master_paths: tuple[Path, ...]
    sidecar_paths: tuple[Path, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def _atomic_write(path: Path, content: bytes) -> None:
    if path.exists():
        raise IngestError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _copy_immutable(source: Path, destination: Path) -> None:
    if destination.exists():
        raise IngestError(f"immutable master already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.incoming")
    try:
        with source.open("rb") as input_stream, temporary.open("wb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        if _sha256(source) != _sha256(temporary):
            raise IngestError(f"master copy checksum mismatch: {source}")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


class Ingestor:
    """Preserve one intake batch using the supplied real or fixture registry."""

    def __init__(self, root: str | os.PathLike[str], registry: IdRegistry) -> None:
        self.root = Path(root)
        self.registry = registry
        self.receipts = self.root / "receipts"
        self.masters = self.root / "masters"
        self.sidecars = self.root / "sidecars"
        self.manifests = self.root / "manifests"

    def ingest_batch(self, items: Iterable[IngestItem], *, contributor: str, channel: str) -> IngestResult:
        batch = tuple(items)
        if not batch:
            raise IngestError("an intake batch must contain at least one item")
        if not contributor.isascii() or not contributor or not channel.isascii() or not channel:
            raise IngestError("receipt contributor and channel must be non-empty ASCII")
        self._preflight(batch)
        try:
            receipt_id = self.registry.mint("RC")
            asset_ids = tuple(self.registry.mint("AST") for _ in batch)
        except RegistryError as exc:
            raise IngestError("cannot assign receipt or asset IDs") from exc

        entries: list[dict[str, Any]] = []
        master_paths: list[Path] = []
        sidecar_paths: list[Path] = []
        manifest_paths: list[Path] = []
        for item, asset_id in zip(batch, asset_ids):
            extension = item.source_path.suffix[1:].lower()
            master = self.masters / asset_id / f"{asset_id}.master.{extension}"
            sidecar = self.sidecars / asset_id / f"{asset_id}.master.{extension}.xmp"
            manifest = self.manifests / f"{asset_id}.json"
            _copy_immutable(item.source_path, master)
            sidecar_bytes = item.sidecar_path.read_bytes()
            if item.copyright_notice is not None or item.attribution is not None:
                metadata = {"notice": item.copyright_notice, "attribution": item.attribution, "source_sha256": _sha256(item.sidecar_path)}
                sidecar_bytes += b"\n<!-- tsuji-copyright:" + _canonical_bytes(metadata) + b" -->\n"
            _atomic_write(sidecar, sidecar_bytes)
            source_checksum = _sha256(item.source_path)
            sidecar_checksum = _sha256(sidecar)
            manifest_value = {
                "schema_version": "v1",
                "asset_id": asset_id,
                "original_filename": item.source_path.name,
                "master_filename": master.name,
                "master_path": str(master.relative_to(self.root)),
                "sidecar_path": str(sidecar.relative_to(self.root)),
                "bytes": item.source_path.stat().st_size,
                "sha256": source_checksum,
                "sidecar_sha256": sidecar_checksum,
                "copyright": {"notice": item.copyright_notice, "attribution": item.attribution} if item.copyright_notice is not None else None,
                "source_id": item.source_id,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            _atomic_write(manifest, _canonical_bytes(manifest_value) + b"\n")
            entries.append({"asset_id": asset_id, "source_id": item.source_id, "filename": item.source_path.name, "bytes": manifest_value["bytes"], "sha256": source_checksum, "sidecar_sha256": sidecar_checksum})
            master_paths.append(master)
            sidecar_paths.append(sidecar)
            manifest_paths.append(manifest)

            asset_record = {"id": asset_id, "type": "Asset", "schema_version": "v1", "workflow": "draft", "approval": None, "visibility": "private", "fixture": self.registry.fixture, "notes_internal": [], "legacy_refs": [], "rights_status": "unknown", "master": str(manifest.relative_to(self.root))}
            try:
                validate_record(asset_record)
            except SchemaError as exc:
                raise IngestError(f"generated Asset record failed M1 schema: {asset_id}") from exc

        receipt = {"id": receipt_id, "type": "Receipt", "schema_version": "v1", "contributor": contributor, "channel": channel, "received_at": datetime.now(timezone.utc).isoformat(), "items": entries}
        receipt["sha256"] = hashlib.sha256(_canonical_bytes(receipt)).hexdigest()
        receipt_path = self.receipts / receipt_id / "record.yaml"
        _atomic_write(receipt_path, _canonical_bytes(receipt) + b"\n")
        return IngestResult(receipt_id, asset_ids, receipt_path, tuple(manifest_paths), tuple(master_paths), tuple(sidecar_paths))

    def _preflight(self, items: tuple[IngestItem, ...]) -> None:
        for item in items:
            if not item.source_path.is_file() or not item.sidecar_path.is_file():
                raise IngestError("each intake item requires an existing master candidate and sidecar")
            if not item.source_path.name.isascii() or not SAFE_INTAKE_NAME.fullmatch(item.source_path.name):
                raise IngestError("intake filename must be ASCII and opaque; mutable meanings are forbidden")
            if item.sidecar_path.suffix.lower() != ".xmp" or not item.sidecar_path.name.isascii():
                raise IngestError("required sidecar must be an ASCII .xmp file")
            if item.source_id is not None and not ASCII_ID.fullmatch(item.source_id):
                raise IngestError("source_id must be a canonical ASCII ID")
            if (item.copyright_notice is None) != (item.attribution is None) or any(value is not None and (not value or not value.isascii()) for value in (item.copyright_notice, item.attribution)):
                raise IngestError("copyright notice and attribution must be supplied together as ASCII")
            if item.source_id is not None:
                try:
                    registered = self.registry.validate(item.source_id)
                except RegistryError as exc:
                    raise IngestError("source_id is outside the registry namespace") from exc
                if not registered:
                    raise IngestError("source_id is not allocated in the registry")
            if item.source_path.resolve() == item.sidecar_path.resolve():
                raise IngestError("master candidate and sidecar must be distinct files")

    def verify_manifest(self, manifest_path: str | os.PathLike[str]) -> None:
        """Verify master and sidecar fixity against one generated manifest."""
        path = Path(manifest_path)
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            master = self.root / manifest["master_path"]
            sidecar = self.root / manifest["sidecar_path"]
            if master.stat().st_size != manifest["bytes"] or _sha256(master) != manifest["sha256"]:
                raise IngestError(f"master checksum mismatch: {master}")
            if _sha256(sidecar) != manifest["sidecar_sha256"]:
                raise IngestError(f"sidecar checksum mismatch: {sidecar}")
        except (KeyError, OSError, json.JSONDecodeError) as exc:
            raise IngestError(f"invalid or unreadable manifest: {path}") from exc