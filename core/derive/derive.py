"""Generate private, deterministic derivatives from preservation masters."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
from PIL import ImageDraw

from core.ingest.ingest import IngestError, _sha256


class DerivativeError(ValueError):
    """Raised when a derivative cannot be generated without violating M3."""


@dataclass(frozen=True)
class DerivativeProfile:
    name: str
    version: str
    max_width: int
    max_height: int
    format: str
    quality: int
    max_bytes: int | None = None
    watermark: bool = False
    copyright_notice: str = ""
    attribution: str = ""
    lossless: bool = False
    optimize: bool = True
    embed_xmp: bool = True

    def __post_init__(self) -> None:
        if not self.name.isascii() or not self.version.isascii() or self.format not in {"JPEG", "PNG", "WEBP"}:
            raise DerivativeError("profile names and formats must use the locked ASCII/open format set")
        if self.max_width < 1 or self.max_height < 1 or not 1 <= self.quality <= 100:
            raise DerivativeError("profile dimensions and quality are invalid")
        if self.max_bytes is not None and self.max_bytes < 1:
            raise DerivativeError("profile max_bytes must be positive")
        if self.name == "web-display" and not self.watermark:
            raise DerivativeError("web-display requires the copyright watermark policy")
        if self.watermark and (not self.copyright_notice.isascii() or not self.copyright_notice):
            raise DerivativeError("watermarked profiles require an ASCII copyright notice")
        if not self.attribution.isascii():
            raise DerivativeError("attribution must be ASCII")


PROFILES = {
    "thumbnail": DerivativeProfile("thumbnail", "v0", 320, 320, "JPEG", 75, 150_000),
    "preview": DerivativeProfile("preview", "v0", 800, 800, "JPEG", 82, 500_000),
    "web-display": DerivativeProfile("web-display", "v0", 1600, 1600, "WEBP", 85, 1_500_000, True, "Copyright TSUJI WORLD", "TSUJI WORLD"),
    "high-fidelity": DerivativeProfile("high-fidelity", "v1", 3200, 3200, "WEBP", 96, 5_000_000, False, "Copyright TSUJI WORLD", "TSUJI WORLD"),
    "lossless-archive": DerivativeProfile("lossless-archive", "v1", 5000, 5000, "PNG", 100, 20_000_000, False, "Copyright TSUJI WORLD", "TSUJI WORLD", True),
}


def _atomic_write(path: Path, data: bytes) -> None:
    if path.exists():
        raise DerivativeError(f"immutable derivative output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class DerivativeGenerator:
    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        self.derivatives = self.root / "derivatives"
        self.manifests = self.root / "derivative_manifests"

    def generate(self, manifest_path: str | os.PathLike[str], profile: DerivativeProfile) -> dict[str, Any]:
        manifest_path = Path(manifest_path)
        try:
            source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            master = self.root / source_manifest["master_path"]
            asset_id = source_manifest["asset_id"]
            if _sha256(master) != source_manifest["sha256"]:
                raise DerivativeError("master does not match its preservation manifest")
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            raise DerivativeError("invalid preservation manifest") from exc
        try:
            with Image.open(master) as opened:
                image = ImageOps.exif_transpose(opened)
                image.thumbnail((profile.max_width, profile.max_height), Image.Resampling.LANCZOS)
                if profile.format == "JPEG" and image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                if profile.watermark:
                    draw = ImageDraw.Draw(image)
                    draw.text((8, max(8, image.height - 24)), profile.copyright_notice, fill=(255, 255, 255))
                output = io.BytesIO()
                save_options: dict[str, Any] = {"format": profile.format, "quality": profile.quality, "optimize": profile.optimize}
                if profile.format == "PNG":
                    save_options = {"format": "PNG", "optimize": profile.optimize}
                if profile.format == "WEBP" and profile.lossless:
                    save_options["lossless"] = True
                image.save(output, **save_options)
                data = output.getvalue()
                width, height = image.size
        except Exception as exc:
            raise DerivativeError(f"master is not a supported image: {master}") from exc
        if profile.max_bytes is not None and len(data) > profile.max_bytes:
            raise DerivativeError(f"derivative exceeds profile byte budget: {profile.name}")
        extension = profile.format.lower().replace("jpeg", "jpg")
        output_path = self.derivatives / asset_id / f"{asset_id}.{profile.name}.{extension}"
        _atomic_write(output_path, data)
        xmp_path = output_path.with_suffix(output_path.suffix + ".xmp")
        xmp = f"<xmpmeta><asset>{asset_id}</asset><profile>{profile.name}</profile><version>{profile.version}</version><copyright>{profile.copyright_notice}</copyright><attribution>{profile.attribution}</attribution></xmpmeta>\n".encode("ascii")
        if not profile.embed_xmp:
            raise DerivativeError("M9 requires XMP sidecar embedding for every derivative")
        _atomic_write(xmp_path, xmp)
        derivative = {"path": str(output_path.relative_to(self.root)), "profile": asdict(profile), "width": width, "height": height, "format": profile.format, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "master_sha256": source_manifest["sha256"], "metadata_stripped": True, "watermark_applied": profile.watermark, "copyright": {"notice": profile.copyright_notice, "attribution": profile.attribution, "metadata_sha256": hashlib.sha256(f"{profile.copyright_notice}|{profile.attribution}".encode("ascii")).hexdigest()}, "xmp_sidecar_path": str(xmp_path.relative_to(self.root)), "xmp_sidecar_sha256": hashlib.sha256(xmp).hexdigest()}
        derivative_manifest = {"schema_version": "v1", "asset_id": asset_id, "master_manifest": str(manifest_path.relative_to(self.root)), "derivatives": [derivative]}
        derivative_manifest_path = self.manifests / f"{asset_id}.{profile.name}.json"
        _atomic_write(derivative_manifest_path, json.dumps(derivative_manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n")
        from core.validate import ValidationError, validate_derivative
        try:
            validate_derivative(self.root, derivative_manifest)
        except ValidationError as exc:
            output_path.unlink(missing_ok=True)
            xmp_path.unlink(missing_ok=True)
            derivative_manifest_path.unlink(missing_ok=True)
            raise DerivativeError(f"derivative validation failed: {exc}") from exc
        return {"manifest_path": derivative_manifest_path, "derivative": derivative}

    def generate_batch(self, manifest_paths: list[str | os.PathLike[str]], profile: DerivativeProfile) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        created: list[Path] = []
        try:
            for manifest_path in manifest_paths:
                result = self.generate(manifest_path, profile)
                created.extend([result["manifest_path"], self.root / result["derivative"]["path"], self.root / result["derivative"]["xmp_sidecar_path"]])
                results.append(result)
            return results
        except DerivativeError:
            for path in created:
                path.unlink(missing_ok=True)
            raise