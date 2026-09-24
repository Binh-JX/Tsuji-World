"""Persistent opaque identifiers and tombstones for Core."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

PREFIXES = frozenset({"RC", "TSJ", "EXH", "EVT", "PER", "SER", "SRC", "AST", "AV", "FM", "SM", "EC", "AM", "PRM", "PRV", "ED", "WLD", "CHP", "STY"})
ID_PATTERN = re.compile(r"^(?P<prefix>[A-Z][A-Z0-9]*)-(?P<number>[0-9]{6})$")
FIXTURE_ID_PATTERN = re.compile(r"^FX-(?P<prefix>[A-Z][A-Z0-9]*)-(?P<number>[0-9]{6})$")


class RegistryError(ValueError):
    """Raised when a locked registry rule is violated."""


def _parse(identifier: str, fixture: bool) -> tuple[str, int]:
    match = (FIXTURE_ID_PATTERN if fixture else ID_PATTERN).fullmatch(identifier)
    if not match or match["prefix"] not in PREFIXES:
        raise RegistryError(f"invalid {'fixture ' if fixture else ''}identifier: {identifier!r}")
    return match["prefix"], int(match["number"])


class IdRegistry:
    """A file-backed single-writer registry for one namespace."""

    def __init__(self, path: str | os.PathLike[str], *, fixture: bool = False) -> None:
        self.path = Path(path)
        self.fixture = fixture
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "next": {}, "allocated": {}, "tombstones": {}}
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"cannot read registry: {self.path}") from exc
        if not isinstance(state, dict) or set(state) != {"version", "next", "allocated", "tombstones"}:
            raise RegistryError("registry state is not the locked format")
        return state

    def _save(self) -> None:
        handle, temporary = tempfile.mkstemp(prefix=".registry.", dir=self.path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(self._state, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def mint(self, prefix: str) -> str:
        if prefix not in PREFIXES or not re.fullmatch(r"[A-Z][A-Z0-9]*", prefix):
            raise RegistryError(f"unknown or non-ASCII prefix: {prefix!r}")
        number = int(self._state["next"].get(prefix, 1))
        while number <= 999999:
            identifier = f"{'FX-' if self.fixture else ''}{prefix}-{number:06d}"
            if identifier not in self._state["allocated"] and identifier not in self._state["tombstones"]:
                self._state["next"][prefix] = number + 1
                self._state["allocated"][identifier] = {"prefix": prefix}
                self._save()
                return identifier
            number += 1
        raise RegistryError(f"identifier space exhausted for {prefix}")

    def tombstone(self, identifier: str, *, reason: str, superseded_by: str | None = None) -> None:
        prefix, _ = _parse(identifier, self.fixture)
        if identifier not in self._state["allocated"]:
            raise RegistryError(f"identifier is not allocated in this registry: {identifier}")
        if not reason or not reason.isascii():
            raise RegistryError("tombstone reason must be non-empty ASCII")
        if superseded_by is not None:
            _parse(superseded_by, self.fixture)
        self._state["allocated"].pop(identifier)
        self._state["tombstones"][identifier] = {"prefix": prefix, "reason": reason, "superseded_by": superseded_by}
        self._save()

    def validate(self, identifier: str) -> bool:
        _parse(identifier, self.fixture)
        return identifier in self._state["allocated"]