"""Operational CLI for TSUJI WORLD Core.

All command inputs are explicit JSON/config paths. Commands never suppress a
Core validation error and never overwrite immutable outputs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Mapping

from core.dataset import DatasetEmitter
from core.audit import AuditRunner
from core.derive import PROFILES, DerivativeGenerator, DerivativeProfile
from core.fixity import FixityVerifier
from core.gate import PublicationGate
from core.ingest import IngestItem, Ingestor
from core.proof import ProofGenerator
from core.registry import IdRegistry
from core.snapshot import Snapshotter

LOG = logging.getLogger("tsuji.core")


class CliError(ValueError):
    pass


def _json(path: str | Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot read JSON: {path}") from exc


def _write_result(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=True, sort_keys=True))


def _records_gate(args: argparse.Namespace) -> PublicationGate:
    records = _json(args.records)
    edition = _json(args.edition)
    if not isinstance(records, dict) or not isinstance(edition, dict):
        raise CliError("records must be an ID-keyed object and edition must be an object")
    hashes = _json(args.current_hashes) if args.current_hashes else {}
    if not isinstance(hashes, dict):
        raise CliError("current hashes must be an object")
    return PublicationGate(records=records, edition=edition, current_hashes=hashes)


def _record_ids(args: argparse.Namespace) -> list[str]:
    ids = list(args.record_id or [])
    if args.record_ids:
        loaded = _json(args.record_ids)
        if not isinstance(loaded, list) or not all(isinstance(item, str) for item in loaded):
            raise CliError("record IDs JSON must be a string array")
        ids.extend(loaded)
    if not ids or len(ids) != len(set(ids)):
        raise CliError("one or more unique record IDs are required")
    return ids


def _ingest(args: argparse.Namespace) -> None:
    items_data = _json(args.items)
    if not isinstance(items_data, list):
        raise CliError("ingest items JSON must be an array")
    items = []
    for item in items_data:
        if not isinstance(item, dict) or "source_path" not in item or "sidecar_path" not in item:
            raise CliError("each ingest item requires source_path and sidecar_path")
        items.append(IngestItem(Path(item["source_path"]), Path(item["sidecar_path"]), item.get("source_id"), item.get("copyright_notice"), item.get("attribution")))
    result = Ingestor(args.root, IdRegistry(args.registry, fixture=args.fixture)).ingest_batch(items, contributor=args.contributor, channel=args.channel)
    _write_result({"receipt_id": result.receipt_id, "asset_ids": result.asset_ids, "receipt_path": str(result.receipt_path), "manifest_paths": [str(path) for path in result.manifest_paths]})


def _derive(args: argparse.Namespace) -> None:
    profile = None if args.profile_file else PROFILES.get(args.profile)
    if profile is None:
        profile_data = _json(args.profile_file) if args.profile_file else None
        if not isinstance(profile_data, dict):
            raise CliError("profile must be one of the built-in profiles or --profile-file JSON")
        profile = DerivativeProfile(**profile_data)
    result = DerivativeGenerator(args.root).generate(args.manifest, profile)
    _write_result({"manifest_path": str(result["manifest_path"]), "derivative": result["derivative"]})


def _gate(args: argparse.Namespace) -> None:
    gate = _records_gate(args)
    ids = _record_ids(args)
    for record_id in ids:
        gate.check(record_id)
    _write_result({"checked": ids, "eligible": True})


def _dataset(args: argparse.Namespace) -> None:
    gate = _records_gate(args)
    manifests = _json(args.asset_manifests) if args.asset_manifests else {}
    result = DatasetEmitter(gate).emit(args.output, _record_ids(args), edition=args.edition_id, release=args.release, lock_hash=args.lock_hash, languages=tuple(args.languages), asset_manifests=manifests)
    _write_result({"dataset": str(result.root), "manifest": str(result.manifest_path), "routes": str(result.routes_path)})


def _proof(args: argparse.Namespace) -> None:
    gate = _records_gate(args)
    manifests = _json(args.asset_manifests) if args.asset_manifests else {}
    signoffs = _json(args.signoffs) if args.signoffs else {}
    result = ProofGenerator(gate, manifests).generate(args.output, _record_ids(args), release=args.release, signoffs=signoffs)
    _write_result({"proof_json": str(result.json_path), "proof_markdown": str(result.markdown_path), "proof_sha256": result.proof_hash, "signoff_json": str(result.signoff_path), "signoff_sha256": result.signoff_hash})


def _snapshot(args: argparse.Namespace) -> None:
    sources = {}
    for source in args.source:
        label, separator, path = source.partition("=")
        if not separator or not label or not path:
            raise CliError("snapshot sources must use label=path")
        sources[label] = path
    result = Snapshotter(args.output).create(args.name, sources)
    _write_result({"archive": str(result.archive), "seal": str(result.seal), "files": result.file_count, "index_sha256": result.index_sha256})


def _fixity(args: argparse.Namespace) -> None:
    verifier = FixityVerifier()
    if args.manifest:
        report = verifier.verify_manifest(args.manifest)
    elif args.snapshot:
        report = verifier.verify_snapshot(args.snapshot, args.seal)
    else:
        if not args.root:
            raise CliError("--root is required with --index")
        index = _json(args.index)
        if not isinstance(index, dict):
            raise CliError("fixity index must be an object")
        report = verifier.verify_index(args.root, index)
    _write_result({"checked": report.checked, "failures": report.failures, "ok": not report.failures})


def _audit(args: argparse.Namespace) -> None:
    config = _json(args.config)
    if not isinstance(config, dict):
        raise CliError("audit config must be an object")
    config["output"] = args.output
    result = AuditRunner(args.workspace).run(config)
    _write_result({"audit_json": str(result.audit_json), "audit_markdown": str(result.audit_markdown), "audit_sha256": result.audit_sha256, "dataset": str(result.dataset), "proof": str(result.proof), "snapshot": str(result.snapshot)})


def _common_records(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--records", required=True, help="ID-keyed records JSON")
    parser.add_argument("--edition", required=True, help="edition policy JSON")
    parser.add_argument("--current-hashes", help="ID-keyed current content hashes JSON")
    parser.add_argument("--record-id", action="append", help="record ID; repeatable")
    parser.add_argument("--record-ids", help="JSON array of record IDs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsuji-core", description="TSUJI WORLD Core management commands")
    parser.add_argument("--verbose", action="store_true", help="enable diagnostic logging")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="preserve intake files and mint IDs")
    ingest.add_argument("--root", required=True)
    ingest.add_argument("--registry", required=True)
    ingest.add_argument("--items", required=True, help="JSON array of intake items")
    ingest.add_argument("--contributor", required=True)
    ingest.add_argument("--channel", required=True)
    ingest.add_argument("--fixture", action="store_true")
    ingest.set_defaults(handler=_ingest)

    derive = commands.add_parser("derive", help="generate a derivative from a manifest")
    derive.add_argument("--root", required=True)
    derive.add_argument("--manifest", required=True)
    derive.add_argument("--profile", choices=tuple(PROFILES), default="web-display")
    derive.add_argument("--profile-file")
    derive.set_defaults(handler=_derive)

    gate = commands.add_parser("gate", help="check publication eligibility")
    _common_records(gate)
    gate.set_defaults(handler=_gate)

    dataset = commands.add_parser("dataset", help="emit an atomic published dataset")
    _common_records(dataset)
    dataset.add_argument("--output", required=True)
    dataset.add_argument("--edition-id", required=True)
    dataset.add_argument("--release", required=True)
    dataset.add_argument("--lock-hash", required=True)
    dataset.add_argument("--languages", nargs="+", default=["ja", "en", "el"])
    dataset.add_argument("--asset-manifests")
    dataset.set_defaults(handler=_dataset)

    proof = commands.add_parser("proof", help="generate a human-reviewable proof sheet")
    _common_records(proof)
    proof.add_argument("--output", required=True)
    proof.add_argument("--release", required=True)
    proof.add_argument("--asset-manifests")
    proof.add_argument("--signoffs")
    proof.set_defaults(handler=_proof)

    snapshot = commands.add_parser("snapshot", help="seal a point-in-time archive")
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--name", required=True)
    snapshot.add_argument("--source", action="append", required=True, help="label=path; repeatable")
    snapshot.set_defaults(handler=_snapshot)

    fixity = commands.add_parser("fixity", help="verify checksums and tamper state")
    fixity_group = fixity.add_mutually_exclusive_group(required=True)
    fixity_group.add_argument("--manifest")
    fixity_group.add_argument("--snapshot")
    fixity_group.add_argument("--index")
    fixity.add_argument("--seal")
    fixity.add_argument("--root")
    fixity.set_defaults(handler=_fixity)

    audit = commands.add_parser("audit", help="run the complete fail-closed Core pipeline")
    audit.add_argument("--config", required=True, help="complete pipeline JSON config")
    audit.add_argument("--workspace", required=True, help="temporary workspace parent")
    audit.add_argument("--output", required=True, help="immutable audit report directory")
    audit.set_defaults(handler=_audit)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.ERROR, format="%(levelname)s: %(message)s")
    try:
        args.handler(args)
        return 0
    except (CliError, ValueError, OSError, KeyError, TypeError) as exc:
        LOG.error("command failed: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())