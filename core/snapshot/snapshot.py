"""Create immutable, self-describing point-in-time snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class SnapshotError(ValueError):
    """Raised when a snapshot cannot be sealed completely."""


@dataclass(frozen=True)
class SnapshotResult:
    archive: Path
    seal: Path
    file_count: int
    index_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Snapshotter:
    def __init__(self, output_dir: str | os.PathLike[str]) -> None:
        self.output_dir = Path(output_dir)

    def create(self, name: str, sources: Mapping[str, str | os.PathLike[str]]) -> SnapshotResult:
        if not name.isascii() or not name or "/" in name or "\\" in name or not sources:
            raise SnapshotError("snapshot name and sources must be non-empty and safe")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        archive = self.output_dir / f"{name}.zip"
        seal = self.output_dir / f"{name}.sha256"
        if archive.exists() or seal.exists():
            raise SnapshotError("snapshots are immutable and cannot be overwritten")
        staging = Path(tempfile.mkdtemp(prefix=f".{name}.", dir=self.output_dir))
        try:
            index: dict[str, dict[str, Any]] = {}
            for label, source_value in sorted(sources.items()):
                if not label.isascii() or not label or Path(label).name != label:
                    raise SnapshotError("snapshot source labels must be simple ASCII names")
                source = Path(source_value)
                if not source.exists():
                    raise SnapshotError(f"snapshot source does not exist: {source}")
                if source.is_file():
                    self._stage_file(source, staging / label, label, index)
                else:
                    for path in sorted(item for item in source.rglob("*") if item.is_file()):
                        relative = Path(label) / path.relative_to(source)
                        if not relative.as_posix().isascii():
                            raise SnapshotError("snapshot paths must be ASCII")
                        self._stage_file(path, staging / relative, relative.as_posix(), index)
            index_bytes = json.dumps(index, ensure_ascii=True, sort_keys=True, indent=2).encode("ascii") + b"\n"
            (staging / "checksums.json").write_bytes(index_bytes)
            index_hash = hashlib.sha256(index_bytes).hexdigest()
            snapshot_manifest = {"schema_version": "v1", "created_at": datetime.now(timezone.utc).isoformat(), "index_sha256": index_hash, "files": len(index)}
            (staging / "snapshot.json").write_text(json.dumps(snapshot_manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            self._zip(staging, archive)
            seal.write_text(f"{_sha256(archive)}  {archive.name}\n{index_hash}  checksums.json\n", encoding="ascii")
            return SnapshotResult(archive, seal, len(index), index_hash)
        except Exception:
            if archive.exists():
                archive.unlink()
            if seal.exists():
                seal.unlink()
            raise
        finally:
            for path in sorted(staging.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            staging.rmdir()

    def _stage_file(self, source: Path, destination: Path, name: str, index: dict[str, dict[str, Any]]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        index[name] = {"bytes": destination.stat().st_size, "sha256": _sha256(destination)}

    def _zip(self, staging: Path, archive: Path) -> None:
        temporary = archive.with_name(f".{archive.name}.incoming")
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(item for item in staging.rglob("*") if item.is_file()):
                info = zipfile.ZipInfo(path.relative_to(staging).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, path.read_bytes())
        os.replace(temporary, archive)