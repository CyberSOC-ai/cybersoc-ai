"""Acquire (only when requested), normalize and compose the selected S2-T01 corpus."""

import argparse
from importlib.metadata import version
import os
from pathlib import Path
import platform
import tempfile

from .acquire import acquire
from .core import IngestionError, canonical, digest, parse_json, read_bytes
from .corpus import compose
from .curated import acquire_selection, safe_path
from .nvd_bulk import acquire_year
from .pipeline import implementation_hash, ingest
from .prepare_lab import prepare

ROOT = Path(__file__).resolve().parents[2]


def check_source(name, source, plan):
    snapshot = parse_json(read_bytes(source / "snapshot-manifest.json", 1024**2))
    if name == "mitre_attack":
        expected = plan["baseline"]["mitre_attack_revision"]
    elif name == "cwe":
        expected = plan["baseline"]["cwe_version"]
    elif name.startswith("nvd-"):
        expected = "NVD-2.0:" + name.removeprefix("nvd-") + ":sha256:" + snapshot["sha256"]
    elif name == "soc":
        return
    else:
        expected = name + ":" + plan["sources"][name]["revision"]
        receipt = parse_json(read_bytes(source / "acquisition.json", 1024**2))
        if [file["path"] for file in receipt["files"]] != plan["sources"][name]["files"]:
            raise IngestionError("Cached source selection differs from the plan")
    if snapshot["upstream_version"] != expected:
        raise IngestionError("Cached source revision differs from the plan")


def build(artifacts, output, selection, *, acquire_sources=False, acquired_at=None):
    artifacts, output = Path(artifacts), Path(output)
    if output.exists():
        raise IngestionError("Use a new release directory")
    selection = Path(selection)
    plan = parse_json(read_bytes(selection, 1024**2))
    recipes = [("mitre_attack", artifacts / "attack", "snapshot.json", False),
               ("cwe", artifacts / "cwe", "snapshot.xml", False)]
    for year in plan["baseline"]["nvd_years"]:
        recipes.append((f"nvd-{year}", artifacts / f"nvd-{year}", "snapshot.json", True))
    for provider, config in plan["sources"].items():
        recipes.append((provider, artifacts / safe_path(config["artifact_subdir"]), "snapshot.json", False))
    recipes.append(("soc", artifacts / "soc-final", "snapshot.json", False))
    if acquire_sources:
        if not (artifacts / "attack").exists():
            acquire("mitre_attack", plan["baseline"]["mitre_attack_revision"], artifacts / "attack", plan["owner"])
        if not (artifacts / "cwe").exists():
            acquire("cwe", plan["baseline"]["cwe_version"], artifacts / "cwe", plan["owner"])
        for year in plan["baseline"]["nvd_years"]:
            if not (artifacts / f"nvd-{year}").exists():
                acquire_year(str(year), artifacts / f"nvd-{year}", plan["owner"])
        for provider, config in plan["sources"].items():
            path = artifacts / safe_path(config["artifact_subdir"])
            if not path.exists():
                acquire_selection(selection, provider, path)
        if not (artifacts / "soc-final").exists():
            if acquired_at is None:
                raise IngestionError("Supply the actual UTC lab snapshot preparation time")
            prepare(artifacts / "soc-final", acquired_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = implementation_hash()
    with tempfile.TemporaryDirectory(prefix=".release-", dir=output.parent) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        inputs, results = [], {}
        for name, source, filename, streaming in recipes:
            check_source(name, source, plan)
            kwargs = {}
            if name in {"soc", "otrf", "splunk"}:
                policy = "soc-policy.json" if name == "soc" else "external-policy.json"
                kwargs = {"policy_path": ROOT / "datasets/knowledge" / policy,
                          "splits_path": ROOT / "datasets/evaluation/soc-eval-v1/splits.json"}
            destination = stage / "normalized" / name
            result = ingest(source / filename, source / "snapshot-manifest.json", source / "notice.txt",
                            destination, stream_nvd=streaming, **kwargs)
            results[name] = result
            inputs.append(destination)
            print(f"Normalized {name}: accepted={result['accepted']}", flush=True)
        composed = compose(inputs, stage / "corpus")
        if implementation_hash() != fingerprint:
            raise IngestionError("Implementation changed during the build; retry with fixed source files")
        summary = {"schema_version": "1.0.0", "selection_sha256": digest(canonical(plan)),
                   "implementation_sha256": fingerprint, "sources": results, "corpus": composed,
                   "environment": {"python": platform.python_version(),
                       "dependencies": {package: version(package) for package in ("httpx", "jsonschema", "ijson", "PyYAML")}}}
        (stage / "selection.json").write_bytes(canonical(plan) + b"\n")
        (stage / "release.json").write_bytes(canonical(summary) + b"\n")
        os.rename(stage, output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--selection", default=str(ROOT / "datasets/knowledge/sources.json"))
    parser.add_argument("--acquire", action="store_true", help="Explicitly allow bounded upstream acquisition")
    parser.add_argument("--lab-acquired-at", help="Actual UTC preparation time when acquiring the lab snapshot")
    args = parser.parse_args()
    summary = build(args.artifacts, args.output, args.selection, acquire_sources=args.acquire,
                    acquired_at=args.lab_acquired_at)
    print(canonical({"accepted": summary["corpus"]["accepted"],
                     "by_source": summary["corpus"]["by_source"],
                     "graph_relationships": summary["corpus"]["graph_relationships"],
                     "records_sha256": summary["corpus"]["records_sha256"]}).decode())


if __name__ == "__main__":
    main()
