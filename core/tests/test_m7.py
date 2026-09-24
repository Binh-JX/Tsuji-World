import json
import tempfile
import unittest
from pathlib import Path

from core.fixity import FixityReport
from core.gate import PublicationGate
from core.proof import ProofError, ProofGenerator, ProofVerifier


def approved_record():
    return {"id": "TSJ-000001", "type": "Artwork", "schema_version": "v1", "workflow": "approved", "approval": {"approved_by": "steward", "approved_on": "2026-09-24", "evidence": "proof-sheet", "approved_hash": "current"}, "visibility": "public", "fixture": False, "notes_internal": "private", "legacy_refs": [], "rights_status": "unknown", "title": {"value": "A title", "doc_status": "documented", "sources": ["SRC-000001"], "reviewed_by": "steward", "reviewed_on": "2026-09-24"}}


class M7Tests(unittest.TestCase):
    def gate(self, current="current"):
        record = approved_record()
        return PublicationGate(records={record["id"]: record}, edition={"audience_ceiling": "public", "fixture": False, "required_claims": {"Artwork": ["title"]}}, current_hashes={record["id"]: current})

    def test_proof_compiles_fixity_gate_and_independent_seals(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ProofGenerator(self.gate()).generate(Path(directory) / "proof", ["TSJ-000001"], release="r1", fixity_reports={"masters": FixityReport(4, ())}, gate_approvals={"TSJ-000001": approved_record()["approval"]}, signoffs={"steward": {"name": "Steward", "date": "2026-09-24"}})
            proof = json.loads(result.json_path.read_text())
            self.assertEqual(proof["fixity"]["masters"]["checked"], 4)
            self.assertIn("TSJ-000001", proof["gate_approvals"])
            seals = ProofVerifier.verify(result.json_path, result.signoff_path)
            self.assertEqual(seals["proof_sha256"], result.proof_hash)
            self.assertEqual(seals["signoff_sha256"], result.signoff_hash)

    def test_tampered_proof_or_signoff_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ProofGenerator(self.gate()).generate(Path(directory) / "proof", ["TSJ-000001"], release="r1")
            result.json_path.write_text(result.json_path.read_text().replace("TSJ-000001", "TSJ-000002"))
            with self.assertRaises(ProofError):
                ProofVerifier.verify(result.json_path, result.signoff_path)

    def test_broken_fixity_and_stale_record_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ProofError):
                ProofGenerator(self.gate()).generate(Path(directory) / "broken", ["TSJ-000001"], release="r1", fixity_reports={"masters": {"checked": 1, "failures": ["checksum mismatch"]}})
            with self.assertRaises(ProofError):
                ProofGenerator(self.gate("stale")).generate(Path(directory) / "stale", ["TSJ-000001"], release="r1")


if __name__ == "__main__":
    unittest.main()