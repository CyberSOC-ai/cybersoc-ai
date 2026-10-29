"""Compose verified corpora, joining CVE providers and KEV without duplicate docs."""

import argparse
from collections import Counter
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from .core import IngestionError, canonical, digest, parse_json, read_bytes, validate
from .nvd_bulk import file_hash
from .pipeline import implementation_hash


def corpus_records(directory):
    directory = Path(directory)
    manifest = parse_json(read_bytes(directory / "manifest.json", 4 * 1024**2))
    checksum, _ = file_hash(directory / "records.jsonl", 8 * 1024**3)
    if checksum != manifest["records_sha256"]:
        raise IngestionError("Input corpus hash mismatch")
    count = 0
    with (directory / "records.jsonl").open("rb") as source:
        while line := source.readline(8 * 1024**2 + 1):
            if len(line) > 8 * 1024**2 or not line.endswith(b"\n"):
                raise IngestionError("Invalid or oversized corpus line")
            record = parse_json(line)
            validate("record", record)
            if record["source"] != manifest["snapshot"]["source"]:
                raise IngestionError("Corpus source differs from manifest")
            if record["provenance"] != manifest["snapshot"]:
                raise IngestionError("Corpus record provenance differs from manifest")
            if digest(record["content"].encode()) != record["content_sha256"]:
                raise IngestionError("Corpus content hash mismatch")
            if record["record_id"] != "DOC-" + digest(canonical([record["source"], record["source_record_id"]])):
                raise IngestionError("Corpus identity hash mismatch")
            count += 1
            yield record
    if count != manifest["accepted"]:
        raise IngestionError("Corpus record count mismatch")


def join_cve(existing, incoming):
    left, right = existing["metadata"], incoming["metadata"]
    providers = {left.get("provider", "nvd"), right.get("provider", "nvd")}
    if providers != {"nvd", "cve_program"}:
        raise IngestionError("Duplicate CVE provider/identity; choose one pinned snapshot per provider")
    nvd, official = (existing, incoming) if left.get("provider", "nvd") == "nvd" else (incoming, existing)
    nvd["metadata"]["provider"] = "joined"
    nvd["metadata"]["cve_program"] = official["metadata"]["cve_program"]
    nvd["metadata"]["provenance_chain"] = [nvd["provenance"], official["provenance"]]
    if nvd["content"] != official["content"]:
        nvd["metadata"]["alternate_descriptions"] = [official["content"]]
    return nvd


def compose(inputs, output):
    output = Path(output)
    if output.exists():
        raise IngestionError("Use a new composed corpus directory")
    if len(inputs) != len(set(map(str, inputs))):
        raise IngestionError("Duplicate corpus input")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".compose-", dir=output.parent) as temp:
        stage = Path(temp) / "corpus"
        stage.mkdir()
        manifests, joins, enrichment = [], 0, 0
        with sqlite3.connect(stage / "facts.sqlite") as database:
            database.execute("CREATE TABLE records (id TEXT PRIMARY KEY, source TEXT, source_id TEXT, document BLOB)")
            database.execute("CREATE UNIQUE INDEX source_identity ON records(source, source_id)")
            database.execute("CREATE TABLE kev (cve_id TEXT PRIMARY KEY, document BLOB)")
            database.execute("CREATE TABLE relationships (id TEXT PRIMARY KEY, document BLOB)")
            for index, directory in enumerate(inputs):
                directory = Path(directory)
                manifest = parse_json(read_bytes(directory / "manifest.json", 4 * 1024**2))
                snapshot = manifest["snapshot"]
                notice = read_bytes(directory / "source-notice.txt", 4 * 1024**2)
                if digest(notice) != snapshot["notice_sha256"]:
                    raise IngestionError("Input corpus source notice hash mismatch")
                (stage / f"notice-{index:02d}.txt").write_bytes(notice)
                manifests.append(manifest)
                for value in corpus_records(directory):
                    if value["collection"] == "relationships":
                        try:
                            database.execute("INSERT INTO relationships VALUES (?, ?)", (value["record_id"], canonical(value)))
                        except sqlite3.IntegrityError as exc:
                            raise IngestionError("Duplicate relationship identity") from exc
                        continue
                    if value["source"] == "kev":
                        try:
                            database.execute("INSERT INTO kev VALUES (?, ?)",
                                             (value["source_record_id"], canonical(value)))
                        except sqlite3.IntegrityError as exc:
                            raise IngestionError("Duplicate KEV catalog record") from exc
                        continue
                    previous = database.execute("SELECT document FROM records WHERE id=?", (value["record_id"],)).fetchone()
                    if previous:
                        if value["source"] != "cve":
                            raise IngestionError("Duplicate corpus record identity")
                        value = join_cve(parse_json(previous[0]), value)
                        joins += 1
                        database.execute("DELETE FROM records WHERE id=?", (value["record_id"],))
                    validate("record", value)
                    database.execute("INSERT INTO records VALUES (?, ?, ?, ?)",
                                     (value["record_id"], value["source"], value["source_record_id"], canonical(value)))
            # Exact CVE-ID join; no inference from description similarity.
            for cve_id, kev_document in database.execute("SELECT cve_id, document FROM kev").fetchall():
                previous = database.execute("SELECT document FROM records WHERE source='cve' AND source_id=?", (cve_id,)).fetchone()
                if previous is None:
                    continue
                value, kev_value = parse_json(previous[0]), parse_json(kev_document)
                value["metadata"]["kev"] = kev_value["metadata"]["kev"]
                chain = value["metadata"].setdefault("provenance_chain", [value["provenance"]])
                chain.append(kev_value["provenance"])
                validate("record", value)
                database.execute("UPDATE records SET document=? WHERE id=?", (canonical(value), value["record_id"]))
                enrichment += 1
            checksum, counts = hashlib.sha256(), Counter()
            with (stage / "records.jsonl").open("xb") as target:
                for source, document in database.execute("SELECT source, document FROM records ORDER BY id"):
                    line = document + b"\n"
                    target.write(line)
                    checksum.update(line)
                    counts[source] += 1
            kev_count = database.execute("SELECT count(*) FROM kev").fetchone()[0]
            relationship_count, relationship_hash = 0, hashlib.sha256()
            with (stage / "relationships.jsonl").open("xb") as target:
                for (document,) in database.execute("SELECT document FROM relationships ORDER BY id"):
                    line = document + b"\n"
                    target.write(line)
                    relationship_hash.update(line)
                    relationship_count += 1
        report = {"schema_version": "1.0.0", "implementation_sha256": implementation_hash(),
                  "inputs": manifests, "accepted": sum(counts.values()), "by_source": dict(sorted(counts.items())),
                  "joined_cve_records": joins, "kev_enriched_cves": enrichment,
                  "kev_catalog_records": kev_count, "kev_without_indexed_cve": kev_count - enrichment,
                  "graph_relationships": relationship_count, "relationships_sha256": relationship_hash.hexdigest(),
                  "records_sha256": checksum.hexdigest(), "corpus_use": "development_only" if
                  any(m["corpus_use"] == "development_only" for m in manifests) else "retrieval"}
        (stage / "manifest.json").write_bytes(canonical(report) + b"\n")
        os.rename(stage, output)
    return report


def lookup(directory, identity):
    if not re.fullmatch(r"CVE-\d{4}-\d{4,}", identity):
        raise IngestionError("Expected a CVE ID")
    path = Path(directory).resolve() / "facts.sqlite"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as database:
        value = database.execute("SELECT document FROM records WHERE source='cve' AND source_id=?", (identity,)).fetchone()
        kev = database.execute("SELECT document FROM kev WHERE cve_id=?", (identity,)).fetchone()
    return {"cve": parse_json(value[0]) if value else None, "kev": parse_json(kev[0]) if kev else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--input", action="append", required=True)
    build.add_argument("--output", required=True)
    query = sub.add_parser("lookup")
    query.add_argument("--corpus", required=True)
    query.add_argument("--cve", required=True)
    args = parser.parse_args()
    result = compose(args.input, args.output) if args.command == "build" else lookup(args.corpus, args.cve)
    print(canonical(result).decode())


if __name__ == "__main__":
    main()
