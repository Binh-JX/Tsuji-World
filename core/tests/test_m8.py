import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from core.audit import AuditError, AuditRunner


def config(root: Path, *, workflow="approved"):
    incoming = root / "UPLOAD-000001.png"
    sidecar = root / "metadata.xmp"
    Image.new("RGB", (32, 24), (12, 24, 36)).save(incoming, format="PNG")
    sidecar.write_bytes(b"<xmpmeta />")
    record = {"id": "TSJ-000001", "type": "Artwork", "schema_version": "v1", "workflow": workflow, "approval": {"approved_by": "steward", "approved_on": "2026-09-24", "evidence": "proof-sheet", "approved_hash": "current"} if workflow == "approved" else None, "visibility": "public", "fixture": False, "notes_internal": "private", "legacy_refs": [], "rights_status": "unknown", "title": {"value": "Audit title", "doc_status": "documented", "sources": ["SRC-000001"], "reviewed_by": "steward", "reviewed_on": "2026-09-24"}}
    return {"items": [{"source_path": str(incoming), "sidecar_path": str(sidecar), "copyright_notice": "Copyright TSUJI WORLD", "attribution": "TSUJI WORLD"}], "records": {"TSJ-000001": record}, "record_ids": ["TSJ-000001"], "current_hashes": {"TSJ-000001": "current"}, "edition": {"audience_ceiling": "public", "fixture": False, "required_claims": {"Artwork": ["title"]}}, "edition_id": "ED-000001", "release": "r1", "lock_hash": "lock", "contributor": "fixture", "channel": "upload", "signoffs": {"steward": {"name": "Steward", "date": "2026-09-24"}}}


class M8Tests(unittest.TestCase):
    def test_full_pipeline_generates_auditable_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = config(root)
            settings["output"] = str(root / "audit")
            result = AuditRunner(root / "workspace").run(settings)
            report = json.loads(result.audit_json.read_text())
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["stages"], ["ingest", "derive", "gate", "dataset", "snapshot", "fixity", "proof"])
            self.assertEqual(report["standards"]["hash_algorithm"], "SHA-256")
            self.assertTrue(result.dataset.joinpath("routes.json").exists())
            self.assertTrue(result.proof.joinpath("signoff.json").exists())
            self.assertTrue(result.snapshot.exists())
            self.assertEqual(len(report["audit_sha256"]), 64)

    def test_gate_anomaly_aborts_without_audit_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = config(root, workflow="under_review")
            settings["output"] = str(root / "audit")
            with self.assertRaises(AuditError):
                AuditRunner(root / "workspace").run(settings)
            self.assertFalse(Path(settings["output"]).exists())

    def test_missing_required_config_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AuditError):
                AuditRunner(Path(directory) / "workspace").run({"release": "r1"})

    def test_cli_audit_runs_master_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = config(root)
            config_path = root / "audit-config.json"
            config_path.write_text(json.dumps(settings))
            completed = subprocess.run([sys.executable, "-m", "core.cli", "audit", "--config", str(config_path), "--workspace", str(root / "workspace"), "--output", str(root / "audit")], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((root / "audit" / "audit.json").exists())


if __name__ == "__main__":
    unittest.main()