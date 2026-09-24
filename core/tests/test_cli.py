import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run([sys.executable, "-m", "core.cli", *arguments], capture_output=True, text=True)

    def test_valid_ingest_derive_snapshot_and_fixity_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incoming = root / "UPLOAD-000001.png"
            sidecar = root / "metadata.xmp"
            Image.new("RGB", (30, 20), (40, 50, 60)).save(incoming, format="PNG")
            sidecar.write_bytes(b"<xmpmeta />")
            items = root / "items.json"
            items.write_text(json.dumps([{"source_path": str(incoming), "sidecar_path": str(sidecar), "copyright_notice": "Copyright TSUJI WORLD", "attribution": "TSUJI WORLD"}]))
            storage = root / "storage"
            ingest = self.run_cli("ingest", "--root", str(storage), "--registry", str(root / "registry.json"), "--items", str(items), "--contributor", "fixture", "--channel", "upload")
            self.assertEqual(ingest.returncode, 0, ingest.stderr)
            payload = json.loads(ingest.stdout)
            self.assertEqual(payload["asset_ids"], ["AST-000001"])
            derived = self.run_cli("derive", "--root", str(storage), "--manifest", payload["manifest_paths"][0], "--profile", "web-display")
            self.assertEqual(derived.returncode, 0, derived.stderr)
            snapshot = self.run_cli("snapshot", "--output", str(root / "snapshots"), "--name", "state-001", "--source", f"storage={storage}", "--source", f"registry={root / 'registry.json'}")
            self.assertEqual(snapshot.returncode, 0, snapshot.stderr)
            snapshot_payload = json.loads(snapshot.stdout)
            fixity = self.run_cli("fixity", "--snapshot", snapshot_payload["archive"], "--seal", snapshot_payload["seal"])
            self.assertEqual(fixity.returncode, 0, fixity.stderr)

    def test_invalid_arguments_and_fixity_failure_return_nonzero(self):
        missing = self.run_cli("ingest", "--root", "/tmp/nope")
        self.assertNotEqual(missing.returncode, 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = root / "tracked.bin"
            tracked.write_bytes(b"original")
            index = {"tracked.bin": {"bytes": 8, "sha256": "0" * 64}}
            index_path = root / "index.json"
            index_path.write_text(json.dumps(index))
            failed = self.run_cli("fixity", "--root", str(root), "--index", str(index_path))
            self.assertEqual(failed.returncode, 2)
            self.assertIn("command failed", failed.stderr)

    def test_gate_cli_blocks_unapproved_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "records.json"
            records.write_text(json.dumps({"TSJ-000001": {"id": "TSJ-000001", "type": "Artwork", "schema_version": "v1", "workflow": "under_review", "approval": None, "visibility": "public", "fixture": False, "notes_internal": [], "legacy_refs": [], "rights_status": "unknown"}}))
            edition = root / "edition.json"
            edition.write_text(json.dumps({"audience_ceiling": "public", "fixture": False, "required_claims": {}}))
            failed = self.run_cli("gate", "--records", str(records), "--edition", str(edition), "--record-id", "TSJ-000001")
            self.assertEqual(failed.returncode, 2)


if __name__ == "__main__":
    unittest.main()