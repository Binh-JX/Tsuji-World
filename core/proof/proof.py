"""Generate immutable JSON and Markdown proof sheets before release."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.gate import GateError, PublicationGate


class ProofError(ValueError):
    """Raised when a proof sheet cannot represent an eligible release."""


@dataclass(frozen=True)
class ProofResult:
    json_path: Path
    markdown_path: Path
    proof_hash: str
    signoff_path: Path | None = None
    signoff_hash: str = ""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def _immutable(path: Path, content: bytes) -> None:
    if path.exists():
        raise ProofError(f"proof output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ProofGenerator:
    def __init__(self, gate: PublicationGate, asset_manifests: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self.gate = gate
        self.asset_manifests = asset_manifests or {}

    def generate(self, output: str | os.PathLike[str], record_ids: Sequence[str], *, release: str, previous_ids: Sequence[str] = (), signoffs: Mapping[str, Mapping[str, Any]] | None = None, fixity_reports: Mapping[str, Any] | None = None, gate_approvals: Mapping[str, Mapping[str, Any]] | None = None) -> ProofResult:
        if not record_ids or not release:
            raise ProofError("proof requires records and a release identifier")
        summaries = []
        for record_id in record_ids:
            try:
                projected = self.gate.project(record_id)
            except GateError as exc:
                raise ProofError(f"blocked record cannot enter proof: {record_id}") from exc
            summary = {"id": record_id, "type": projected["type"], "record_sha256": hashlib.sha256(_canonical(projected)).hexdigest(), "claims": self._claims(projected), "assets": self._asset_summary(projected)}
            summaries.append(summary)
        signoff_block = self._signoffs(signoffs or {})
        fixity = self._fixity(fixity_reports or {})
        approvals = self._approvals(record_ids, gate_approvals or {})
        proof = {"schema_version": "v1", "release": release, "newly_included": [item["id"] for item in summaries if item["id"] not in previous_ids], "records": summaries, "excluded": [], "warnings": [], "fixity": fixity, "gate_approvals": approvals, "signoffs": signoff_block}
        proof_hash = hashlib.sha256(_canonical(proof)).hexdigest()
        proof["proof_sha256"] = proof_hash
        destination = Path(output)
        json_path = destination / "proof.json"
        markdown_path = destination / "proof.md"
        signoff_path = destination / "signoff.json"
        _immutable(json_path, _canonical(proof) + b"\n")
        markdown = self._markdown(proof, proof_hash)
        _immutable(markdown_path, markdown.encode("utf-8"))
        signoff = {"schema_version": "v1", "release": release, "proof_sha256": proof_hash, "gate_approvals": approvals, "fixity": fixity, "signoffs": signoff_block}
        signoff_hash = hashlib.sha256(_canonical(signoff)).hexdigest()
        signoff["signoff_sha256"] = signoff_hash
        _immutable(signoff_path, _canonical(signoff) + b"\n")
        return ProofResult(json_path, markdown_path, proof_hash, signoff_path, signoff_hash)

    def _claims(self, record: Mapping[str, Any]) -> list[dict[str, Any]]:
        claims = []
        for name, value in record.items():
            if isinstance(value, Mapping) and {"value", "doc_status", "sources"}.issubset(value):
                claims.append({"field": name, "status": value["doc_status"], "must_label": value.get("must_label", False), "label": value.get("label")})
        return claims

    def _asset_summary(self, record: Mapping[str, Any]) -> list[dict[str, Any]]:
        if record["type"] != "Asset":
            return []
        manifest = self.asset_manifests.get(record["id"], {})
        return [{"path": item.get("path"), "sha256": item.get("sha256"), "profile": item.get("profile")} for item in manifest.get("derivatives", [])]

    def _fixity(self, reports: Mapping[str, Any]) -> dict[str, Any]:
        result = {}
        for name, report in reports.items():
            failures = tuple(getattr(report, "failures", report.get("failures", ()) if isinstance(report, Mapping) else ()))
            if failures:
                raise ProofError(f"fixity failed before proof: {name}")
            result[name] = {"checked": getattr(report, "checked", report.get("checked", 0) if isinstance(report, Mapping) else 0), "failures": []}
        return result

    def _approvals(self, record_ids: Sequence[str], supplied: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        approvals = {}
        for record_id in record_ids:
            record = self.gate.records[record_id]
            approval = supplied.get(record_id, record.get("approval"))
            if not isinstance(approval, Mapping) or not approval.get("approved_by") or not approval.get("approved_on") or not approval.get("evidence") or not approval.get("approved_hash"):
                raise ProofError(f"missing gate approval for proof: {record_id}")
            approvals[record_id] = {key: approval[key] for key in ("approved_by", "approved_on", "approved_hash", "evidence")}
        return approvals

    def _signoffs(self, signoffs: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        roles = {"steward", "family_approver"}
        result = {}
        for role in roles:
            value = signoffs.get(role, {})
            if value and (not value.get("name") or not value.get("date")):
                raise ProofError(f"incomplete sign-off: {role}")
            result[role] = {"name": value.get("name"), "date": value.get("date"), "status": "signed" if value else "pending"}
        return result

    def _markdown(self, proof: Mapping[str, Any], proof_hash: str) -> str:
        lines = [f"# Proof sheet: {proof['release']}", "", f"Proof SHA-256: `{proof_hash}`", "", "## Included records", ""]
        for record in proof["records"]:
            lines.append(f"- `{record['id']}` ({record['type']}) record SHA-256 `{record['record_sha256']}`")
            for claim in record["claims"]:
                label = f" [{claim['label']}]" if claim["label"] else ""
                lines.append(f"  - claim `{claim['field']}`: {claim['status']}{label}")
            for asset in record["assets"]:
                lines.append(f"  - derivative `{asset['path']}` SHA-256 `{asset['sha256']}`")
        lines.extend(["", "## Verification", "", f"Gate approvals: {len(proof['gate_approvals'])}", f"Fixity checks: {len(proof['fixity'])}", "", "## Sign-off", "", "| Role | Name | Date | Status |", "|---|---|---|---|"])
        for role, value in proof["signoffs"].items():
            lines.append(f"| {role} | {value['name'] or ''} | {value['date'] or ''} | {value['status']} |")
        return "\n".join(lines) + "\n"


class ProofVerifier:
    """Independently verify proof and sign-off hash seals."""

    @staticmethod
    def verify(proof_path: str | os.PathLike[str], signoff_path: str | os.PathLike[str]) -> dict[str, str]:
        try:
            proof = json.loads(Path(proof_path).read_text(encoding="utf-8"))
            signoff = json.loads(Path(signoff_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProofError("proof or sign-off manifest is unreadable") from exc
        proof_hash = proof.get("proof_sha256")
        unsigned_proof = {key: value for key, value in proof.items() if key != "proof_sha256"}
        if proof_hash != hashlib.sha256(_canonical(unsigned_proof)).hexdigest():
            raise ProofError("proof hash seal mismatch")
        signoff_hash = signoff.get("signoff_sha256")
        unsigned_signoff = {key: value for key, value in signoff.items() if key != "signoff_sha256"}
        if signoff_hash != hashlib.sha256(_canonical(unsigned_signoff)).hexdigest() or signoff.get("proof_sha256") != proof_hash:
            raise ProofError("sign-off hash seal mismatch")
        return {"proof_sha256": proof_hash, "signoff_sha256": signoff_hash}