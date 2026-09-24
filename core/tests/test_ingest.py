import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from core.ingest import IngestError, IngestItem, Ingestor
from core.registry import IdRegistry


class IngestTests(unittest.TestCase):
    def make_batch(self, root: Path, name: str = "UPLOAD-000001.jpg") -> IngestItem:
        source = root / name
        sidecar = root / "metadata.xmp"
        source.write_bytes(b"preservation bytes\x00\xff")
        sidecar.write_bytes(b"<xmpmeta>synthetic sidecar</xmpmeta>")
        return IngestItem(source, sidecar, "SRC-000001")

    def test_valid_batch_preserves_bytes_and_links_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = IdRegistry(root / "registry.json")
            registry.mint("SRC")
            result = Ingestor(root / "storage", registry).ingest_batch((self.make_batch(root),), contributor="fixture", channel="upload")
            master = result.master_paths[0]
            manifest = json.loads(result.manifest_paths[0].read_text())
            self.assertEqual(master.read_bytes(), b"preservation bytes\x00\xff")
            self.assertEqual(manifest["asset_id"], result.asset_ids[0])
            self.assertEqual(manifest["sha256"], hashlib.sha256(master.read_bytes()).hexdigest())
            self.assertTrue(result.sidecar_paths[0].name.endswith(".xmp"))
            receipt = json.loads(result.receipt_path.read_text())
            self.assertEqual(receipt["id"], result.receipt_id)
            self.assertEqual(receipt["sha256"], hashlib.sha256(json.dumps({key: value for key, value in receipt.items() if key != "sha256"}, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest())

    def test_missing_sidecar_checksum_or_illegal_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = IdRegistry(root / "registry.json")
            registry.mint("SRC")
            ingestor = Ingestor(root / "storage", registry)
            item = self.make_batch(root)
            item.sidecar_path.unlink()
            with self.assertRaises(IngestError):
                ingestor.ingest_batch((item,), contributor="fixture", channel="upload")
            illegal = self.make_batch(root, "artwork-2001-title.jpg")
            with self.assertRaises(IngestError):
                ingestor.ingest_batch((illegal,), contributor="fixture", channel="upload")

    def test_source_id_boundary_and_immutable_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = IdRegistry(root / "registry.json")
            registry.mint("SRC")
            ingestor = Ingestor(root / "storage", registry)
            invalid = self.make_batch(root)
            invalid = IngestItem(invalid.source_path, invalid.sidecar_path, "TSJ-2001-001")
            with self.assertRaises(IngestError):
                ingestor.ingest_batch((invalid,), contributor="fixture", channel="upload")
            unknown = self.make_batch(root, "UPLOAD-000002.jpg")
            unknown = IngestItem(unknown.source_path, unknown.sidecar_path, "SRC-000999")
            with self.assertRaises(IngestError):
                ingestor.ingest_batch((unknown,), contributor="fixture", channel="upload")
            result = ingestor.ingest_batch((self.make_batch(root),), contributor="fixture", channel="upload")
            ingestor.verify_manifest(result.manifest_paths[0])
            result.master_paths[0].write_bytes(b"changed")
            with self.assertRaises(IngestError):
                ingestor.verify_manifest(result.manifest_paths[0])


if __name__ == "__main__":
    unittest.main()