import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from core.derive import DerivativeError, DerivativeGenerator, PROFILES
from core.ingest import IngestItem, Ingestor
from core.registry import IdRegistry
from core.validate import ValidationError, validate_derivative


class M9Tests(unittest.TestCase):
    def ingest(self, root: Path):
        incoming = root / "UPLOAD-000001.png"
        sidecar = root / "metadata.xmp"
        Image.new("RGB", (48, 32), (50, 70, 90)).save(incoming, format="PNG")
        sidecar.write_bytes(b"<xmpmeta />")
        registry = IdRegistry(root / "registry.json")
        registry.mint("SRC")
        result = Ingestor(root / "storage", registry).ingest_batch((IngestItem(incoming, sidecar, "SRC-000001"),), contributor="fixture", channel="upload")
        return result

    def test_advanced_profiles_are_lossless_or_high_fidelity_with_xmp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.ingest(root)
            generator = DerivativeGenerator(root / "storage")
            lossless = generator.generate(result.manifest_paths[0], PROFILES["lossless-archive"])
            high = generator.generate(result.manifest_paths[0], PROFILES["high-fidelity"])
            for generated in (lossless, high):
                manifest = json.loads(generated["manifest_path"].read_text())
                validate_derivative(root / "storage", manifest)
                derivative = manifest["derivatives"][0]
                self.assertTrue(derivative["xmp_sidecar_path"].endswith(".xmp"))
                self.assertIn(result.asset_ids[0], (root / "storage" / derivative["xmp_sidecar_path"]).read_text())
            self.assertTrue(lossless["derivative"]["profile"]["lossless"])

    def test_malformed_derivative_metadata_is_rejected_and_batch_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.ingest(root)
            generator = DerivativeGenerator(root / "storage")
            generated = generator.generate(result.manifest_paths[0], PROFILES["high-fidelity"])
            manifest = json.loads(generated["manifest_path"].read_text())
            manifest["derivatives"][0]["sha256"] = "0" * 64
            with self.assertRaises(ValidationError):
                validate_derivative(root / "storage", manifest)
            generated["manifest_path"].unlink()
            (root / "storage" / generated["derivative"]["path"]).unlink()
            (root / "storage" / generated["derivative"]["xmp_sidecar_path"]).unlink()
            invalid_manifest = root / "invalid.json"
            invalid_manifest.write_text("{}")
            with self.assertRaises(DerivativeError):
                generator.generate_batch([result.manifest_paths[0], invalid_manifest], PROFILES["high-fidelity"])
            derivative_directory = root / "storage" / "derivatives" / result.asset_ids[0]
            self.assertFalse(derivative_directory.exists() and any(derivative_directory.iterdir()))


if __name__ == "__main__":
    unittest.main()