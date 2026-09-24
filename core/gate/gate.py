"""Core publication gate: eligibility, display policy, and safe projection."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping

from core.schema import SchemaError, validate_record

TOKEN = re.compile(r"\{\{(ref|fact):([^}]+)\}\}")
LEVEL = {"public": 0, "archive": 1, "family": 2, "private": 3}
FORBIDDEN_OUTPUT = {"notes_internal", "contact", "master", "master_path", "archive_derivative_path", "permissions"}
ALLOW = {
    "Artwork": {"id", "type", "schema_version", "workflow", "visibility", "fixture", "title", "title_variants", "date", "medium", "dimensions", "series", "accession_number"},
    "Exhibition": {"id", "type", "schema_version", "workflow", "visibility", "fixture", "title", "dates", "venue", "organiser", "works"},
    "Person": {"id", "type", "schema_version", "workflow", "visibility", "fixture", "kind", "names", "relationships", "age_class", "is_artist", "life_dates"},
    "Source": {"id", "type", "schema_version", "workflow", "visibility", "fixture", "kind", "title", "author", "publisher", "date", "citation", "language"},
    "Asset": {"id", "type", "schema_version", "workflow", "visibility", "fixture", "kind", "role", "depicts", "description", "alt_text"},
}


class GateError(ValueError):
    """Raised for any non-overridable publication gate failure."""


def _hash_record(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()


class PublicationGate:
    def __init__(self, *, records: Mapping[str, Mapping[str, Any]], edition: Mapping[str, Any], current_hashes: Mapping[str, str] | None = None) -> None:
        self.records = records
        self.edition = edition
        self.current_hashes = current_hashes or {}
        self._checked: set[str] = set()

    def check(self, record_id: str) -> None:
        if record_id not in self.records:
            raise GateError(f"required reference does not resolve: {record_id}")
        record = self.records[record_id]
        try:
            validate_record(record)
        except SchemaError as exc:
            raise GateError(f"schema validation failed for {record_id}") from exc
        ceiling = self.edition.get("audience_ceiling")
        if ceiling not in LEVEL or self.edition.get("fixture") not in {True, False}:
            raise GateError("edition has no valid audience ceiling or fixture scope")
        if record["fixture"] != self.edition["fixture"]:
            raise GateError("fixture and non-fixture records cannot share an edition")
        if record["workflow"] != "approved":
            raise GateError("only approved records enter a release")
        approval = record.get("approval")
        expected_hash = self.current_hashes.get(record_id, _hash_record(record))
        if not isinstance(approval, dict) or not approval.get("approved_by") or not approval.get("approved_on") or not approval.get("evidence") or approval.get("approved_hash") != expected_hash:
            raise GateError("approval is missing or does not match the current content hash")
        if LEVEL[record["visibility"]] > LEVEL[ceiling]:
            raise GateError("record visibility exceeds edition ceiling")
        if record["workflow"] == "withdrawn" or record.get("rights_status") in {"denied", "withdrawn", "expired"}:
            raise GateError("withdrawn or denied records are not eligible")
        if record["type"] == "Asset" and record.get("rights_status") != "cleared":
            raise GateError("displayed assets require cleared rights")
        if record["type"] in {"ArtistVoice", "FamilyMemory", "StudentMemory", "ExpertCommentary", "AssociateMemory"} and record.get("rights_status") != "cleared":
            raise GateError("displayed voices require cleared rights")
        self._check_claims(record, ceiling)
        required = self.edition.get("required_claims", {}).get(record["type"], [])
        for path in required:
            claim = self._path(record, path)
            if not isinstance(claim, dict):
                raise GateError(f"required claim does not resolve: {record_id}.{path}")
            self._check_claim(claim, ceiling)
        self._resolve_tokens(record)
        self._checked.add(record_id)

    def project(self, record_id: str) -> dict[str, Any]:
        self.check(record_id)
        record = self.records[record_id]
        allowed = ALLOW.get(record["type"])
        if allowed is None:
            raise GateError(f"no publication allow-list for type: {record['type']}")
        projection = {key: deepcopy(value) for key, value in record.items() if key in allowed}
        self._scan_output(projection)
        return projection

    def resolve_text(self, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            kind, target = match.groups()
            if kind == "ref":
                self.check(target)
                record = self.records[target]
                value = record.get("title") or record.get("name") or record.get("names")
                if isinstance(value, dict) and "value" in value:
                    value = value["value"]
                if not isinstance(value, str):
                    raise GateError(f"reference has no displayable name: {target}")
                return value
            record_id, _, claim_path = target.partition(".")
            if not claim_path:
                raise GateError(f"fact token has no claim path: {target}")
            self.check(record_id)
            claim = self._path(self.records[record_id], claim_path)
            if not isinstance(claim, dict) or "value" not in claim:
                raise GateError(f"fact claim does not resolve: {target}")
            self._check_claim(claim, self.edition["audience_ceiling"])
            return str(claim["value"])
        return TOKEN.sub(replace, text)

    def _check_claims(self, record: Mapping[str, Any], ceiling: str) -> None:
        for value in record.values():
            if isinstance(value, dict) and {"value", "doc_status", "sources"}.issubset(value):
                self._check_claim(value, ceiling)

    def _check_claim(self, claim: Mapping[str, Any], ceiling: str) -> None:
        status = claim.get("doc_status")
        if status not in {"documented", "partially_documented", "family_record", "to_verify", "disputed", "unknown"}:
            raise GateError("claim has invalid documentation status")
        if status == "documented" and (not claim.get("sources") or not claim.get("reviewed_by") or not claim.get("reviewed_on")):
            raise GateError("documented claim lacks source or review envelope")
        if status == "disputed" and not claim.get("alternatives"):
            raise GateError("disputed claim lacks alternatives")
        if status in {"unknown"} or (status in {"to_verify", "disputed"} and ceiling == "public"):
            raise GateError("claim is not displayable at this edition ceiling")
        if status != "documented" and (not claim.get("must_label") or not claim.get("label")):
            raise GateError("non-documented displayed claim requires must_label and label")

    def _resolve_tokens(self, record: Mapping[str, Any]) -> None:
        for value in record.values():
            if isinstance(value, str) and "{{" in value:
                self.resolve_text(value)

    def _path(self, record: Mapping[str, Any], path: str) -> Any:
        value: Any = record
        for part in path.split("."):
            if not isinstance(value, Mapping) or part not in value:
                return None
            value = value[part]
        return value

    def _scan_output(self, output: Mapping[str, Any]) -> None:
        if FORBIDDEN_OUTPUT.intersection(output):
            raise GateError("private or master fields entered the projected output")
        encoded = json.dumps(output, ensure_ascii=True)
        if re.search(r"(?<![A-Z])(PRM|PRV|RC)-[0-9]{6}(?![0-9])", encoded):
            raise GateError("prohibited private IDs entered the projected output")