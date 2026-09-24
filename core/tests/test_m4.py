import json
import tempfile
import unittest
from pathlib import Path

from core.dataset import DatasetEmitter, DatasetError
from core.gate import GateError, PublicationGate
from core.proof import ProofError, ProofGenerator


def record(identifier, entity_type, *, rights="unknown", title=True, workflow="approved"):
    value = {"id": identifier, "type": entity_type, "schema_version": "v1", "workflow": workflow, "approval": {"approved_by": "steward", "approved_on": "2026-09-24", "evidence": "proof-sheet", "approved_hash": "current"} if workflow == "approved" else None, "visibility": "public", "fixture": False, "notes_internal": "never projected", "legacy_refs": [], "rights_status": rights}
    if title:
        value["title"] = {"value": "A title", "doc_status": "documented", "sources": ["SRC-000001"], "reviewed_by": "steward", "reviewed_on": "2026-09-24"}
    return value


class M4Tests(unittest.TestCase):
    def setUp(self):
        self.artwork = record("TSJ-000001", "Artwork")
        self.asset = record("AST-000001", "Asset", rights="cleared", title=False)
        self.edition = {"audience_ceiling": "public", "fixture": False, "required_claims": {"Artwork": ["title"]}}
        self.gate = PublicationGate(records={"TSJ-000001": self.artwork, "AST-000001": self.asset}, edition=self.edition, current_hashes={"TSJ-000001": "current", "AST-000001": "current"})

    def test_dataset_routes_and_assets_are_emitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = DatasetEmitter(self.gate).emit(root / "dataset", ["TSJ-000001", "AST-000001"], edition="ED-000001", release="r1", lock_hash="lock", asset_manifests={"AST-000001": {"derivatives": [{"path": "derivatives/AST-000001/web.webp", "width": 800, "height": 600, "format": "WEBP", "bytes": 123, "sha256": "a" * 64, "profile": {"name": "web-display", "version": "v0"}, "watermark_applied": True, "copyright": {"notice": "Copyright TSUJI WORLD", "attribution": "TSUJI WORLD"}}]}})
            routes = json.loads(result.routes_path.read_text())
            self.assertEqual(routes["TSJ-000001"]["ja"], "/works/tsj-000001")
            self.assertEqual(routes["TSJ-000001"]["en"], "/en/works/tsj-000001")
            assets = json.loads(result.assets_path.read_text())
            self.assertEqual(assets["AST-000001"]["derivatives"][0]["format"], "WEBP")
            emitted = result.root / "records" / "works" / "TSJ-000001.json"
            self.assertNotIn("notes_internal", emitted.read_text())

    def test_proof_contains_hashes_and_signoffs(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ProofGenerator(self.gate, {"AST-000001": {"derivatives": [{"path": "derivatives/AST-000001/web.webp", "sha256": "b" * 64, "profile": {"version": "v0"}}]}}).generate(Path(directory) / "proof", ["TSJ-000001", "AST-000001"], release="r1", signoffs={"steward": {"name": "Steward", "date": "2026-09-24"}})
            proof = json.loads(result.json_path.read_text())
            self.assertEqual(proof["proof_sha256"], result.proof_hash)
            self.assertEqual(proof["signoffs"]["steward"]["status"], "signed")
            self.assertEqual(proof["signoffs"]["family_approver"]["status"], "pending")
            self.assertIn("AST-000001", result.markdown_path.read_text())

    def test_unapproved_record_blocks_dataset_and_proof(self):
        blocked = record("TSJ-000001", "Artwork", workflow="under_review")
        gate = PublicationGate(records={"TSJ-000001": blocked}, edition=self.edition, current_hashes={"TSJ-000001": "current"})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dataset"
            with self.assertRaises(DatasetError):
                DatasetEmitter(gate).emit(output, ["TSJ-000001"], edition="ED-000001", release="r1", lock_hash="lock")
            self.assertFalse(output.exists())
            with self.assertRaises(ProofError):
                ProofGenerator(gate).generate(Path(directory) / "proof", ["TSJ-000001"], release="r1")


if __name__ == "__main__":
    unittest.main()