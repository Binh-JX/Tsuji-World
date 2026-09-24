"""Framework-independent V1 schema checks."""

from __future__ import annotations

import re
from typing import Any

ENTITY_PREFIXES = {"Artwork": "TSJ", "Exhibition": "EXH", "Person": "PER", "Source": "SRC", "Asset": "AST", "Permission": "PRM", "Edition": "ED", "ArtistVoice": "AV", "FamilyMemory": "FM", "StudentMemory": "SM", "ExpertCommentary": "EC", "AssociateMemory": "AM"}
VOICE_TYPES = frozenset({"ArtistVoice", "FamilyMemory", "StudentMemory", "ExpertCommentary", "AssociateMemory"})
CLAIM_DOC_STATUSES = frozenset({"documented", "partially_documented", "family_record", "to_verify", "disputed", "unknown"})
WORKFLOWS = frozenset({"draft", "under_review", "approved", "withdrawn"})
VISIBILITIES = frozenset({"public", "archive", "family", "private"})
RIGHTS_STATUSES = frozenset({"cleared", "pending", "denied", "unknown", "withdrawn", "expired"})
TEXT_ORIGINS = frozenset({"human_written", "human_reviewed", "ai_draft"})
ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{6}$")

COMMON = {"id", "type", "schema_version", "workflow", "approval", "visibility", "fixture", "notes_internal", "legacy_refs", "rights_status"}
VOICE_FIELDS = {"author", "author_display", "relationship", "language_original", "form", "medium", "body", "transcript", "translations", "recorded_by", "recorded_on", "occasion", "subjects", "sources", "excerpts", "sensitivity", "reports_words_of", "classification_note"}
FIELDS = {
    "Artwork": COMMON | {"title", "title_variants", "date", "medium", "dimensions", "series", "accession_number"},
    "Exhibition": COMMON | {"title", "dates", "venue", "organiser", "works"},
    "Person": COMMON | {"kind", "names", "relationships", "age_class", "is_artist", "life_dates", "contact"},
    "Source": COMMON | {"kind", "title", "author", "publisher", "date", "url", "archive_location", "citation", "language", "third_party_rights_holder"},
    "Asset": COMMON | {"kind", "role", "depicts", "detail_of", "region", "photographer", "captured_on", "description", "alt_text", "identifiable_persons", "source_ref", "receipt_ref", "permissions", "master"},
    "Permission": COMMON | {"basis", "grantor", "subjects", "scope", "conditions", "evidence", "state", "granted_on", "expires_on", "recorded_by", "reviewed_by"},
    "Edition": COMMON | {"name", "audience_ceiling", "documentation_policy", "language_policy", "structure", "outputs", "clearance_review", "dates", "derived_from", "status"},
    **{voice: COMMON | VOICE_FIELDS for voice in VOICE_TYPES},
}
FIELDS["ArtistVoice"] |= {"attribution_mode", "confirmed_by_artist", "direct_source"}
FIELDS["FamilyMemory"] |= {"relationship_detail", "household_context"}
FIELDS["StudentMemory"] |= {"teaching_context"}
FIELDS["ExpertCommentary"] |= {"affiliation_as_stated", "publication_ref", "quotation_limit"}
FIELDS["AssociateMemory"] |= {"association_context"}


class SchemaError(ValueError):
    pass


def _required(record: dict[str, Any], fields: set[str]) -> None:
    missing = fields - record.keys()
    if missing:
        raise SchemaError(f"missing required fields: {', '.join(sorted(missing))}")


def validate_claim(claim: Any) -> None:
    if not isinstance(claim, dict):
        raise SchemaError("claim must be an object")
    _required(claim, {"value", "doc_status", "sources"})
    if claim["doc_status"] not in CLAIM_DOC_STATUSES or not isinstance(claim["sources"], list):
        raise SchemaError("invalid claim documentation status or sources")
    if claim["doc_status"] == "disputed" and not claim.get("alternatives"):
        raise SchemaError("disputed claims require alternatives")
    if claim["doc_status"] == "documented" and (not claim["sources"] or not claim.get("reviewed_by") or not claim.get("reviewed_on")):
        raise SchemaError("documented claims require sources, reviewer and review date")


def validate_text(value: Any) -> None:
    if not isinstance(value, dict) or set(value) - {"text", "origin", "review"} or "text" not in value or "origin" not in value:
        raise SchemaError("text requires only text, origin and optional review")
    if value["origin"] not in TEXT_ORIGINS:
        raise SchemaError("invalid text origin")


def validate_record(record: Any) -> None:
    """Validate one record; unknown structure is rejected."""
    if not isinstance(record, dict):
        raise SchemaError("record must be an object")
    _required(record, COMMON | {"type"})
    entity_type = record["type"]
    if entity_type not in ENTITY_PREFIXES:
        raise SchemaError("unknown or closed entity type")
    unknown = set(record) - FIELDS[entity_type]
    if unknown:
        raise SchemaError(f"unknown fields: {', '.join(sorted(unknown))}")
    identifier = record["id"]
    fixture_prefix = "FX-" if record["fixture"] else ""
    if not isinstance(identifier, str) or not identifier.isascii() or not re.fullmatch(r"(?:FX-)?[A-Z][A-Z0-9]*-[0-9]{6}", identifier) or not identifier.startswith(fixture_prefix + ENTITY_PREFIXES[entity_type] + "-"):
        raise SchemaError("id is not ASCII, opaque, six-digit, or type-matching")
    if not isinstance(record["schema_version"], str) or not record["schema_version"].isascii() or not record["schema_version"]:
        raise SchemaError("schema_version must be a non-empty ASCII name")
    if record["workflow"] not in WORKFLOWS or record["visibility"] not in VISIBILITIES or not isinstance(record["fixture"], bool) or record["rights_status"] not in RIGHTS_STATUSES:
        raise SchemaError("invalid independent envelope axis")
    if entity_type == "Permission" and record.get("basis") not in {"copyright_licence", "reproduction_permission", "likeness_consent", "statement_publication_consent", "contributor_agreement", "third_party_publication_permission"}:
        raise SchemaError("invalid immutable Permission basis")
    if entity_type in VOICE_TYPES:
        _required(record, {"author", "relationship", "language_original", "form", "medium", "body", "sources"})
        if entity_type == "ArtistVoice" and not record.get("direct_source"):
            raise SchemaError("Artist Voice requires a direct source")
    for key, value in record.items():
        if isinstance(value, dict) and {"value", "doc_status", "sources"}.issubset(value):
            validate_claim(value)
        if key in {"body", "transcript"}:
            validate_text(value)