import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from core.derive import DerivativeGenerator, DerivativeProfile
from core.gate import GateError, PublicationGate
from core.ingest import IngestItem, Ingestor
from core.registry import IdRegistry


class DeriveTests(unittest.TestCase):
    def test_profile_generates_format_and_preserves_master(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incoming = root / "UPLOAD-000001.png"
            sidecar = root / "metadata.xmp"
            Image.new("RGB", (120, 80), (240, 10, 20)).save(incoming, format="PNG")
            sidecar.write_bytes(b"<xmpmeta />")
            registry = IdRegistry(root / "registry.json")
            registry.mint("SRC")
            result = Ingestor(root / "storage", registry).ingest_batch((IngestItem(incoming, sidecar, "SRC-000001"),), contributor="fixture", channel="upload")
            master_before = result.master_paths[0].read_bytes()
            derived = DerivativeGenerator(root / "storage").generate(result.manifest_paths[0], DerivativeProfile("test", "v0", 40, 40, "WEBP", 80))
            self.assertEqual(result.master_paths[0].read_bytes(), master_before)
            self.assertEqual(derived["derivative"]["format"], "WEBP")
            self.assertLessEqual(derived["derivative"]["width"], 40)
            self.assertEqual(derived["derivative"]["sha256"], hashlib.sha256(Path(root / "storage" / derived["derivative"]["path"]).read_bytes()).hexdigest())


def approved_record(claim_status="documented"):
    claim = {"value": "A documented title", "doc_status": claim_status, "sources": ["SRC-000001"]}
    if claim_status == "documented":
        claim.update({"reviewed_by": "steward", "reviewed_on": "2026-09-24"})
    else:
        claim.update({"must_label": True, "label": "label.to_verify"})
    return {"id": "TSJ-000001", "type": "Artwork", "schema_version": "v1", "workflow": "approved", "approval": {"approved_by": "steward", "approved_on": "2026-09-24", "evidence": "proof-sheet", "approved_hash": "current"}, "visibility": "public", "fixture": False, "notes_internal": "private", "legacy_refs": [], "rights_status": "unknown", "title": claim}


class GateTests(unittest.TestCase):
    def edition(self):
        return {"audience_ceiling": "public", "fixture": False, "required_claims": {"Artwork": ["title"]}}

    def test_compliant_record_projects_by_allow_list(self):
        record = approved_record()
        gate = PublicationGate(records={record["id"]: record}, edition=self.edition(), current_hashes={record["id"]: "current"})
        output = gate.project(record["id"])
        self.assertIn("title", output)
        self.assertNotIn("notes_internal", output)

    def test_public_unverified_claim_and_missing_token_reference_fail(self):
        record = approved_record("to_verify")
        gate = PublicationGate(records={record["id"]: record}, edition=self.edition(), current_hashes={record["id"]: "current"})
        with self.assertRaises(GateError):
            gate.check(record["id"])
        compliant = approved_record()
        gate = PublicationGate(records={compliant["id"]: compliant}, edition=self.edition(), current_hashes={compliant["id"]: "current"})
        with self.assertRaises(GateError):
            gate.resolve_text("See {{ref:PER-000001}}")

    def test_required_claim_and_approval_hash_are_mandatory(self):
        record = approved_record()
        record.pop("title")
        gate = PublicationGate(records={record["id"]: record}, edition=self.edition(), current_hashes={record["id"]: "current"})
        with self.assertRaises(GateError):
            gate.check(record["id"])
        record = approved_record()
        record["approval"]["approved_hash"] = "stale"
        gate = PublicationGate(records={record["id"]: record}, edition=self.edition(), current_hashes={record["id"]: "current"})
        with self.assertRaises(GateError):
            gate.check(record["id"])


if __name__ == "__main__":
    unittest.main()