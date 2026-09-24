"""Closed V1 record definitions and fail-closed validation."""

from .schema import CLAIM_DOC_STATUSES, ENTITY_PREFIXES, TEXT_ORIGINS, VOICE_TYPES, SchemaError, validate_record

__all__ = ["CLAIM_DOC_STATUSES", "ENTITY_PREFIXES", "TEXT_ORIGINS", "VOICE_TYPES", "SchemaError", "validate_record"]