"""Fail-closed fixity checks for preservation and release artifacts."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class FixityError(ValueError):
    """Raised when a referenced byte or checksum index is inconsistent."""


@dataclass(frozen=True)
class FixityReport:
    checked: int
    failures: tuple[str, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class FixityVerifier:
    def verify_index(self, root: str | Path, index: Mapping[str, Mapping[str, Any]], *, reject_unindexed: bool = True) -> FixityReport:
        root = Path(root)
        failures: list[str] = []
        expected = set(index)
        actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
        if reject_unindexed:
            for extra in sorted(actual - expected):
                failures.append(f"unindexed file: {extra}")
        for name, entry in sorted(index.items()):
            path = root / name
            if not path.is_file():
                failures.append(f"missing file: {name}")
                continue
            if path.stat().st_size != entry.get("bytes") or _sha256(path) != entry.get("sha256"):
                failures.append(f"checksum mismatch: {name}")
        report = FixityReport(len(index), tuple(failures))
        if failures:
            raise FixityError("; ".join(failures))
        return report

    def verify_manifest(self, manifest_path: str | Path) -> FixityReport:
        path = Path(manifest_path)
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FixityError(f"invalid manifest: {path}") from exc
        root = path.parent.parent
        index: dict[str, dict[str, Any]] = {}
        if "master_path" in manifest:
            index[manifest["master_path"]] = {"bytes": manifest["bytes"], "sha256": manifest["sha256"]}
            index[manifest["sidecar_path"]] = {"bytes": (root / manifest["sidecar_path"]).stat().st_size, "sha256": manifest["sidecar_sha256"]}
        for derivative in manifest.get("derivatives", []):
            index[derivative["path"]] = {"bytes": derivative["bytes"], "sha256": derivative["sha256"]}
            if "xmp_sidecar_path" in derivative:
                sidecar = root / derivative["xmp_sidecar_path"]
                index[derivative["xmp_sidecar_path"]] = {"bytes": sidecar.stat().st_size if sidecar.exists() else -1, "sha256": derivative.get("xmp_sidecar_sha256")}
        return self.verify_index(root, index, reject_unindexed=False)

    def verify_snapshot(self, archive: str | Path, seal: str | Path | None = None) -> FixityReport:
        archive = Path(archive)
        if seal is not None:
            lines = Path(seal).read_text(encoding="ascii").splitlines()
            if not lines or lines[0].split()[0] != _sha256(archive):
                raise FixityError("snapshot archive seal mismatch")
        try:
            with zipfile.ZipFile(archive) as bundle:
                index = json.loads(bundle.read("checksums.json"))
                for name, entry in index.items():
                    data = bundle.read(name)
                    if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                        raise FixityError(f"snapshot checksum mismatch: {name}")
                return FixityReport(len(index), ())
        except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            raise FixityError("invalid snapshot archive") from exc