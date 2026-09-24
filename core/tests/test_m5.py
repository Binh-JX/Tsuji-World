import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from core.dataset import DatasetEmitter
from core.derive import DerivativeGenerator, PROFILES
from core.fixity import FixityError, FixityVerifier
from core.gate import PublicationGate
from core.ingest import IngestItem, Ingestor
from core.registry import IdRegistry
from core.snapshot import Snapshotter


class M5Tests(unittest.TestCase):
    def preserved_store(self, root: Path):
        incoming = root / "UPLOAD-000001.png"
        sidecar = root / "metadata.xmp"
        Image.new("RGB", (24, 16), (20, 30, 40)).save(incoming, format="PNG")
        sidecar.write_bytes(b"<xmpmeta />")
        registry = IdRegistry(root / "registry.json")
        registry.mint("SRC")
        result = Ingestor(root / "store", registry).ingest_batch((IngestItem(incoming, sidecar, "SRC-000001", "Copyright TSUJI WORLD", "TSUJI WORLD"),), contributor="fixture", channel="upload")
        derived = DerivativeGenerator(root / "store").generate(result.manifest_paths[0], PROFILES["web-display"])
        return registry, result, derived

    def test_snapshot_archives_state_and_fixity_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, result, derived = self.preserved_store(root)
            snapshot = Snapshotter(root / "snapshots").create("state-001", {"registry.json": root / "registry.json", "store": root / "store"})
            verifier = FixityVerifier()
            self.assertEqual(verifier.verify_snapshot(snapshot.archive, snapshot.seal).checked, snapshot.file_count)
            result.master_paths[0].write_bytes(b"bit rot")
            with self.assertRaises(FixityError):
                verifier.verify_manifest(result.manifest_paths[0])
            snapshot.archive.write_bytes(snapshot.archive.read_bytes() + b"tampered")
            with self.assertRaises(FixityError):
                verifier.verify_snapshot(snapshot.archive, snapshot.seal)

    def test_recursive_index_rejects_modified_and_unindexed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            store.mkdir()
            tracked = store / "tracked.bin"
            tracked.write_bytes(b"stable")
            index = {"tracked.bin": {"bytes": 6, "sha256": ""}}
            import hashlib
            index["tracked.bin"]["sha256"] = hashlib.sha256(b"stable").hexdigest()
            verifier = FixityVerifier()
            self.assertEqual(verifier.verify_index(store, index).checked, 1)
            tracked.write_bytes(b"changed")
            with self.assertRaises(FixityError):
                verifier.verify_index(store, index)
            tracked.write_bytes(b"stable")
            (store / "untracked.bin").write_bytes(b"unexpected")
            with self.assertRaises(FixityError):
                verifier.verify_index(store, index)

    def test_web_derivative_contains_watermark_and_public_copyright_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, result, derived = self.preserved_store(root)
            metadata = derived["derivative"]
            self.assertTrue(metadata["watermark_applied"])
            self.assertEqual(metadata["copyright"]["attribution"], "TSUJI WORLD")
            self.assertIn(b"tsuji-copyright", result.sidecar_paths[0].read_bytes())
            asset = {"id": result.asset_ids[0], "type": "Asset", "schema_version": "v1", "workflow": "approved", "approval": {"approved_by": "steward", "approved_on": "2026-09-24", "evidence": "proof", "approved_hash": "current"}, "visibility": "public", "fixture": False, "notes_internal": [], "legacy_refs": [], "rights_status": "cleared"}
            gate = PublicationGate(records={asset["id"]: asset}, edition={"audience_ceiling": "public", "fixture": False, "required_claims": {}}, current_hashes={asset["id"]: "current"})
            output = DatasetEmitter(gate).emit(root / "dataset", [asset["id"]], edition="ED-000001", release="r1", lock_hash="lock", asset_manifests={asset["id"]: {"derivatives": [metadata]}})
            assets = json.loads(output.assets_path.read_text())
            self.assertEqual(assets[asset["id"]]["copyright"][0]["notice"], "Copyright TSUJI WORLD")


if __name__ == "__main__":
    unittest.main()