"""Build the renderer-facing dataset as one fail-closed atomic artifact."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.gate import GateError, PublicationGate


class DatasetError(ValueError):
    """Raised when a published dataset cannot be emitted safely."""


@dataclass(frozen=True)
class DatasetResult:
    root: Path
    manifest_path: Path
    routes_path: Path
    assets_path: Path
    record_paths: tuple[Path, ...]


COLLECTIONS = {
    "Artwork": "works", "Exhibition": "exhibitions", "Person": "people", "Source": "sources", "Asset": "assets",
    "ArtistVoice": "voices/artist", "FamilyMemory": "voices/family", "StudentMemory": "voices/student", "ExpertCommentary": "voices/expert", "AssociateMemory": "voices/associate", "Edition": "editions",
}
LANGUAGE_RE = re.compile(r"^[a-z]{2}$")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class DatasetEmitter:
    def __init__(self, gate: PublicationGate) -> None:
        self.gate = gate

    def emit(self, output: str | os.PathLike[str], record_ids: Sequence[str], *, edition: str, release: str, lock_hash: str, languages: Sequence[str] = ("ja", "en", "el"), asset_manifests: Mapping[str, Mapping[str, Any]] | None = None, strings: Mapping[str, Mapping[str, Any]] | None = None) -> DatasetResult:
        if not record_ids or not edition or not release or not lock_hash or any(not LANGUAGE_RE.fullmatch(language) for language in languages):
            raise DatasetError("dataset identity and languages are required")
        if len(set(record_ids)) != len(record_ids) or len(set(languages)) != len(languages):
            raise DatasetError("dataset record IDs and languages must be unique")
        destination = Path(output)
        if destination.exists():
            raise DatasetError(f"dataset output already exists: {destination}")
        temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
        try:
            projections: list[dict[str, Any]] = []
            for record_id in record_ids:
                try:
                    projection = self.gate.project(record_id)
                    projections.append(self._resolve_projection(projection))
                except GateError as exc:
                    raise DatasetError(f"gate blocked dataset record: {record_id}") from exc
            routes = self._routes(projections, languages)
            records_root = temporary / "records"
            record_paths: list[Path] = []
            for projection in projections:
                entity_type = projection["type"]
                collection = COLLECTIONS.get(entity_type)
                if collection is None:
                    raise DatasetError(f"no dataset collection for type: {entity_type}")
                path = records_root / collection / f"{projection['id']}.json"
                _write_json(path, projection)
                record_paths.append(path)
            public_assets = self._assets(projections, asset_manifests or {})
            _write_json(temporary / "routes.json", routes)
            _write_json(temporary / "assets.json", public_assets)
            if strings is not None:
                for language, catalog in strings.items():
                    if language not in languages:
                        raise DatasetError(f"string catalog language is not in edition: {language}")
                    _write_json(temporary / "strings" / f"{language}.json", catalog)
            manifest = {"dataset_version": "v1", "edition": edition, "release": release, "lock_hash": lock_hash, "languages": list(languages), "counts": {"records": len(projections), "assets": len(public_assets)}}
            _write_json(temporary / "manifest.json", manifest)
            self._scan(temporary)
            os.replace(temporary, destination)
            return DatasetResult(destination, destination / "manifest.json", destination / "routes.json", destination / "assets.json", tuple(destination / path.relative_to(temporary) for path in record_paths))
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    def _resolve_projection(self, value: Any) -> Any:
        if isinstance(value, str) and "{{" in value:
            return self.gate.resolve_text(value)
        if isinstance(value, dict):
            return {key: self._resolve_projection(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_projection(item) for item in value]
        return value

    def _routes(self, projections: Sequence[Mapping[str, Any]], languages: Sequence[str]) -> dict[str, dict[str, str]]:
        routes: dict[str, dict[str, str]] = {}
        occupied: set[str] = set()
        for record in projections:
            base = COLLECTIONS[record["type"]].split("/")
            canonical = "/" + "/".join(base + [record["id"].lower()])
            routes[record["id"]] = {}
            for language in languages:
                path = canonical if language == "ja" else f"/{language}{canonical}"
                if path in occupied:
                    raise DatasetError(f"duplicate canonical route: {path}")
                occupied.add(path)
                routes[record["id"]][language] = path
        return routes

    def _assets(self, projections: Sequence[Mapping[str, Any]], manifests: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        assets: dict[str, Any] = {}
        for record in projections:
            if record["type"] != "Asset":
                continue
            source = manifests.get(record["id"])
            if source is None:
                raise DatasetError(f"missing derivative manifest for asset: {record['id']}")
            derivatives = []
            for derivative in source.get("derivatives", []):
                if any(private in str(derivative.get("path", "")) for private in ("master", "archive", "..")):
                    raise DatasetError("private master/archive path entered assets output")
                derivatives.append({key: derivative[key] for key in ("path", "width", "height", "format", "bytes", "sha256", "profile") if key in derivative})
            if source.get("derivatives") and any(not item.get("watermark_applied") for item in source["derivatives"]):
                raise DatasetError(f"derivative lacks required copyright watermark: {record['id']}")
            copyright_metadata = [item["copyright"] for item in source.get("derivatives", []) if item.get("copyright")]
            assets[record["id"]] = {"derivatives": derivatives, "placeholder": source.get("placeholder"), "alt": record.get("alt_text"), "credit": source.get("credit"), "copyright": copyright_metadata}
        return assets

    def _scan(self, root: Path) -> None:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if any(secret in text for secret in ("notes_internal", "master_path", "archive_derivative_path")) or re.search(r"(?<![A-Z])(PRM|PRV|RC)-[0-9]{6}(?![0-9])", text):
                raise DatasetError(f"private field or ID leaked into dataset: {path}")