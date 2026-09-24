"""Fail-closed assembly of the TSUJI WORLD Core pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.dataset import DatasetEmitter
from core.derive import PROFILES, DerivativeGenerator
from core.fixity import FixityError, FixityReport, FixityVerifier
from core.gate import GateError, PublicationGate
from core.ingest import IngestItem, Ingestor
from core.proof import ProofGenerator, ProofVerifier
from core.registry import IdRegistry
from core.snapshot import SnapshotError, Snapshotter


class AuditError(ValueError):
    """Raised when any master pipeline stage fails."""


@dataclass(frozen=True)
class AuditResult:
    audit_json: Path
    audit_markdown: Path
    audit_sha256: str
    dataset: Path
    proof: Path
    snapshot: Path


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class AuditRunner:
    """Run all release stages from one explicit, reproducible configuration."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)

    def run(self, config: Mapping[str, Any]) -> AuditResult:
        self._validate_config(config)
        work = Path(tempfile.mkdtemp(prefix=".audit.", dir=self.root.parent if self.root.parent.exists() else None))
        try:
            storage = work / "storage"
            registry_path = work / "registry.json"
            registry = IdRegistry(registry_path, fixture=bool(config.get("fixture", False)))
            items = tuple(IngestItem(Path(item["source_path"]), Path(item["sidecar_path"]), item.get("source_id"), item.get("copyright_notice"), item.get("attribution")) for item in config["items"])
            ingest_result = Ingestor(storage, registry).ingest_batch(items, contributor=config["contributor"], channel=config["channel"])
            verifier = FixityVerifier()
            reports: dict[str, FixityReport] = {}
            for manifest in ingest_result.manifest_paths:
                reports[f"master:{manifest.stem}"] = verifier.verify_manifest(manifest)

            derivative_manifests: dict[str, Mapping[str, Any]] = {}
            profiles = config.get("profiles", ["web-display"])
            for manifest in ingest_result.manifest_paths:
                for profile_name in profiles:
                    profile = PROFILES.get(profile_name)
                    if profile is None:
                        raise AuditError(f"unknown derivative profile: {profile_name}")
                    generated = DerivativeGenerator(storage).generate(manifest, profile)
                    derivative_manifest = json.loads(Path(generated["manifest_path"]).read_text(encoding="utf-8"))
                    asset_id = derivative_manifest["asset_id"]
                    derivative_manifests[asset_id] = derivative_manifest
                    reports[f"derivative:{asset_id}"] = verifier.verify_manifest(generated["manifest_path"])

            records = self._materialize_records(config["records"], ingest_result.asset_ids, config.get("asset_records", {}))
            current_hashes = config["current_hashes"]
            gate = PublicationGate(records=records, edition=config["edition"], current_hashes=current_hashes)
            record_ids = list(config["record_ids"])
            for record_id in record_ids:
                gate.check(record_id)

            output = work / "release"
            output.mkdir(parents=True, exist_ok=True)
            dataset_result = DatasetEmitter(gate).emit(output / "dataset", record_ids, edition=config["edition_id"], release=config["release"], lock_hash=config["lock_hash"], languages=tuple(config.get("languages", ("ja", "en", "el"))), asset_manifests=derivative_manifests)
            snapshot_result = Snapshotter(output / "snapshots").create("state", {"registry.json": registry_path, "storage": storage, "dataset": dataset_result.root})
            reports["snapshot"] = verifier.verify_snapshot(snapshot_result.archive, snapshot_result.seal)
            proof_result = ProofGenerator(gate, derivative_manifests).generate(output / "proof", record_ids, release=config["release"], fixity_reports=reports, gate_approvals=config.get("gate_approvals", {}), signoffs=config.get("signoffs", {}))
            ProofVerifier.verify(proof_result.json_path, proof_result.signoff_path)
            audit = self._audit_payload(config, ingest_result, reports, dataset_result, snapshot_result, proof_result)
            audit_hash = hashlib.sha256(_canonical(audit)).hexdigest()
            audit["audit_sha256"] = audit_hash
            destination = Path(config["output"])
            if destination.exists():
                raise AuditError(f"audit output already exists: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.mkdir(exist_ok=False)
            audit_json = destination / "audit.json"
            audit_markdown = destination / "audit.md"
            audit_json.write_bytes(_canonical(audit) + b"\n")
            audit_markdown.write_text(self._markdown(audit, audit_hash), encoding="utf-8")
            final_release = destination / "release"
            shutil.copytree(output, final_release)
            return AuditResult(audit_json, audit_markdown, audit_hash, final_release / "dataset", final_release / "proof", final_release / "snapshots" / "state.zip")
        except (AuditError, GateError, FixityError, SnapshotError, OSError, KeyError, TypeError, ValueError) as exc:
            raise AuditError(f"pipeline aborted: {exc}") from exc
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _validate_config(self, config: Mapping[str, Any]) -> None:
        required = {"items", "records", "record_ids", "edition", "edition_id", "release", "lock_hash", "current_hashes", "contributor", "channel", "output"}
        missing = required - config.keys()
        if missing:
            raise AuditError(f"audit config missing: {', '.join(sorted(missing))}")
        if not isinstance(config["items"], list) or not isinstance(config["records"], Mapping) or not isinstance(config["record_ids"], list) or not isinstance(config["current_hashes"], Mapping) or not isinstance(config["edition"], Mapping):
            raise AuditError("audit config has invalid structural fields")
        if not config["record_ids"] or len(config["record_ids"]) != len(set(config["record_ids"])):
            raise AuditError("audit record_ids must be unique and non-empty")

    def _materialize_records(self, records: Mapping[str, Any], asset_ids: Sequence[str], asset_records: Mapping[str, Any]) -> dict[str, Any]:
        materialized = dict(records)
        for raw_index, template in asset_records.items():
            try:
                asset_id = asset_ids[int(raw_index)]
            except (ValueError, IndexError) as exc:
                raise AuditError(f"asset record index is invalid: {raw_index}") from exc
            if not isinstance(template, Mapping):
                raise AuditError("asset record templates must be objects")
            record = dict(template)
            record["id"] = asset_id
            materialized[asset_id] = record
        return materialized

    def _audit_payload(self, config: Mapping[str, Any], ingest: Any, reports: Mapping[str, FixityReport], dataset: Any, snapshot: Any, proof: Any) -> dict[str, Any]:
        return {"schema_version": "v1", "project": "TSUJI WORLD", "edition": config["edition_id"], "release": config["release"], "status": "passed", "standards": {"hash_algorithm": "SHA-256", "masters_immutable": True, "gate_required": True, "copyright_policy": "web-display watermark and attribution required", "fixture": bool(config.get("fixture", False))}, "stages": ["ingest", "derive", "gate", "dataset", "snapshot", "fixity", "proof"], "counts": {"assets": len(ingest.asset_ids), "records": len(config["record_ids"]), "fixity_checks": sum(report.checked for report in reports.values())}, "artifacts": {"receipt": "pipeline/storage/receipts", "dataset": "release/dataset", "snapshot": "release/snapshots/state.zip", "proof": "release/proof/proof.json", "signoff": "release/proof/signoff.json"}, "fixity": {name: {"checked": report.checked, "failures": list(report.failures)} for name, report in reports.items()}, "certification": "All executed stages passed their configured Core checks; human sign-off remains authoritative for release."}

    def _markdown(self, audit: Mapping[str, Any], audit_hash: str) -> str:
        lines = [f"# TSUJI WORLD audit: {audit['release']}", "", f"Status: **{audit['status']}**", f"Audit SHA-256: `{audit_hash}`", "", "## Pipeline", "", " -> ".join(audit["stages"]), "", "## Compliance", "", f"- Hash algorithm: {audit['standards']['hash_algorithm']}", f"- Masters immutable: {audit['standards']['masters_immutable']}", f"- Copyright policy: {audit['standards']['copyright_policy']}", f"- Fixity checks: {audit['counts']['fixity_checks']}", "", "## Certification", "", audit["certification"]]
        return "\n".join(lines) + "\n"