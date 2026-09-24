"""Fail-closed derivative validation for V-S, V-R, and V-G boundaries."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


class ValidationError(ValueError):
    """Raised when a generated artifact violates a Core validation rule."""


ASSET_ID = re.compile(r"^(?:FX-)?AST-[0-9]{6}$")
FORMATS = {"JPEG", "PNG", "WEBP"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_derivative(root: str | Path, manifest: Mapping[str, Any]) -> None:
    """Validate one derivative manifest and every referenced byte artifact."""
    root = Path(root)
    required = {"schema_version", "asset_id", "master_manifest", "derivatives"}
    if set(manifest) - required or not required.issubset(manifest) or manifest["schema_version"] != "v1":
        raise ValidationError("V-S: derivative manifest is not the strict v1 shape")
    asset_id = manifest["asset_id"]
    if not isinstance(asset_id, str) or not asset_id.isascii() or not ASSET_ID.fullmatch(asset_id):
        raise ValidationError("V-S: derivative asset ID is invalid")
    master_manifest_path = root / manifest["master_manifest"]
    try:
        master_manifest = json.loads(master_manifest_path.read_text(encoding="utf-8"))
        master = root / master_manifest["master_path"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise ValidationError("V-R: master manifest reference is broken") from exc
    if not master.is_file() or _sha256(master) != master_manifest.get("sha256"):
        raise ValidationError("V-R: preservation master is missing or changed")
    if not isinstance(manifest["derivatives"], list) or not manifest["derivatives"]:
        raise ValidationError("V-S: derivative list is required")
    for derivative in manifest["derivatives"]:
        _validate_one(root, asset_id, derivative)


def _validate_one(root: Path, asset_id: str, derivative: Mapping[str, Any]) -> None:
    required = {"path", "profile", "width", "height", "format", "bytes", "sha256", "master_sha256", "metadata_stripped", "watermark_applied", "copyright", "xmp_sidecar_path", "xmp_sidecar_sha256"}
    if set(derivative) - required or not required.issubset(derivative):
        raise ValidationError("V-S: derivative metadata envelope is incomplete")
    path_value = derivative["path"]
    if not isinstance(path_value, str) or not path_value.isascii() or ".." in Path(path_value).parts or any(part in {"masters", "archive"} for part in Path(path_value).parts):
        raise ValidationError("V-R: derivative path is unsafe or private")
    path = root / path_value
    if not path.is_file() or path.stat().st_size != derivative["bytes"] or _sha256(path) != derivative["sha256"]:
        raise ValidationError("V-R: derivative bytes or checksum do not match")
    if derivative["format"] not in FORMATS or not isinstance(derivative["profile"], Mapping) or not derivative["profile"].get("version"):
        raise ValidationError("V-S: derivative format/profile is invalid")
    if not isinstance(derivative["width"], int) or not isinstance(derivative["height"], int) or derivative["width"] < 1 or derivative["height"] < 1:
        raise ValidationError("V-S: derivative dimensions are invalid")
    if derivative["metadata_stripped"] is not True:
        raise ValidationError("V-G: derivative metadata was not stripped")
    profile_name = derivative["profile"].get("name")
    if profile_name == "web-display" and (derivative["watermark_applied"] is not True or not derivative["copyright"].get("notice") or not derivative["copyright"].get("attribution")):
        raise ValidationError("V-G: web-display derivative lacks copyright watermark/attribution")
    xmp_path_value = derivative["xmp_sidecar_path"]
    if not isinstance(xmp_path_value, str) or not xmp_path_value.isascii():
        raise ValidationError("V-S: XMP sidecar path is invalid")
    xmp = root / xmp_path_value
    if not xmp.is_file() or _sha256(xmp) != derivative["xmp_sidecar_sha256"]:
        raise ValidationError("V-R: derivative XMP sidecar is missing or changed")
    xmp_text = xmp.read_text(encoding="ascii")
    if asset_id not in xmp_text or str(profile_name) not in xmp_text:
        raise ValidationError("V-G: XMP sidecar does not identify asset and profile")