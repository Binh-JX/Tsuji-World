import tempfile
import unittest
from pathlib import Path

from core.registry import IdRegistry, RegistryError
from core.schema import SchemaError, validate_record


class RegistryTests(unittest.TestCase):
    def test_minted_ids_are_exact_and_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            real = IdRegistry(Path(directory) / "real.json")
            fixture = IdRegistry(Path(directory) / "fixtures.json", fixture=True)
            self.assertEqual(real.mint("TSJ"), "TSJ-000001")
            self.assertEqual(real.mint("PER"), "PER-000001")
            self.assertEqual(fixture.mint("TSJ"), "FX-TSJ-000001")
            with self.assertRaises(RegistryError):
                real.validate("FX-TSJ-000001")
            with self.assertRaises(RegistryError):
                real.tombstone("FX-TSJ-000001", reason="wrong scope")

    def test_tombstones_are_never_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = IdRegistry(Path(directory) / "real.json")
            identifier = registry.mint("AST")
            registry.tombstone(identifier, reason="superseded")
            self.assertEqual(registry.mint("AST"), "AST-000002")


class SchemaTests(unittest.TestCase):
    def test_claim_envelope_and_independent_axes(self):
        record = {"id": "TSJ-000001", "type": "Artwork", "schema_version": "v1", "workflow": "draft", "approval": None, "visibility": "private", "fixture": False, "notes_internal": [], "legacy_refs": [], "rights_status": "unknown", "title": {"value": "Untitled", "doc_status": "unknown", "sources": []}}
        validate_record(record)
        record["title"] = {"value": "x", "doc_status": "to_verify", "sources": []}
        record["visibility"] = "family"
        validate_record(record)

    def test_schema_fails_closed_and_voice_types_are_closed(self):
        record = {"id": "TSJ-000001", "type": "Artwork", "schema_version": "v1", "workflow": "draft", "approval": None, "visibility": "private", "fixture": True, "notes_internal": [], "legacy_refs": [], "rights_status": "unknown", "unknown": 1}
        with self.assertRaises(SchemaError):
            validate_record(record)
        record.pop("unknown")
        record["type"] = "NarratorVoice"
        with self.assertRaises(SchemaError):
            validate_record(record)

    def test_fixture_id_matches_fixture_flag(self):
        record = {"id": "FX-TSJ-000001", "type": "Artwork", "schema_version": "v1", "workflow": "draft", "approval": None, "visibility": "private", "fixture": True, "notes_internal": [], "legacy_refs": [], "rights_status": "unknown"}
        validate_record(record)
        record["fixture"] = False
        with self.assertRaises(SchemaError):
            validate_record(record)


if __name__ == "__main__":
    unittest.main()