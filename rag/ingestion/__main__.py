"""python -m rag.ingestion --help"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET

from jsonschema import ValidationError

from .core import IngestionError
from .pipeline import ingest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Normalize a pinned offline knowledge snapshot")
    parser.add_argument("--input", required=True)
    parser.add_argument("--snapshot", required=True, help="Versioned snapshot manifest JSON")
    parser.add_argument("--notice", required=True, help="Preserved source license/notice bytes")
    parser.add_argument("--output", required=True, help="New corpus directory (must not exist)")
    parser.add_argument("--soc-policy")
    parser.add_argument("--splits")
    args = parser.parse_args(argv)
    try:
        result = ingest(args.input, args.snapshot, args.notice, args.output,
                        policy_path=args.soc_policy, splits_path=args.splits)
    except IngestionError as exc:
        print(f"Ingestion failed: {exc}. No complete corpus was published.", file=sys.stderr)
        return 1
    except (ValidationError, OSError, ET.ParseError, ValueError):
        # Public CLI intentionally omits paths, source text and parser snippets.
        print("Ingestion failed: invalid input, provenance, policy or output path. "
              "No complete corpus was published.", file=sys.stderr)
        return 1
    print(json.dumps({"accepted": result["accepted"], "excluded": result["excluded"],
                      "corpus_use": result["corpus_use"],
                      "records_sha256": result["records_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
