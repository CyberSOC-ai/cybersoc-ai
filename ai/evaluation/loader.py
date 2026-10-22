"""Separate input-only and evaluator APIs; model callers never load labels."""
from pathlib import Path
import re

from .hashing import read_json, verify


def _case_ids(dataset, split):
    if split not in ("development", "test"):
        raise ValueError(f"splits.json: unknown split {split!r}")
    ids = [entry["case_id"] for entry in read_json(Path(dataset) / "splits.json")[split]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"splits.json: duplicate case IDs in {split}")
    for cid in ids:
        if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", cid):
            raise ValueError(f"{cid!r}: invalid case ID in splits.json")
    return ids


def load_model_inputs(dataset, split="development"):
    """Return fresh incident objects only; no labels, context or gold metadata.

    Evaluator preflight must validate/verify the dataset before handing this API
    to a model runner. This boundary is an API separation, not an OS sandbox.
    """
    root = Path(dataset)
    result = []
    for cid in _case_ids(root, split):
        path = root / "inputs" / f"{cid}.json"
        if path.is_symlink() or not path.resolve().is_relative_to((root / "inputs").resolve()):
            raise ValueError(f"{cid}: unsafe input path")
        result.append(read_json(path))
    return result


def load_evaluator_cases(dataset, split="development"):
    """Evaluator-only bundles; never pass this return value to model code."""
    root = Path(dataset)
    verify(root)
    return [{"case_id": cid,
             "input": read_json(root / "inputs" / f"{cid}.json"),
             "labels": read_json(root / "labels" / f"{cid}.json"),
             "context": read_json(root / "context" / f"{cid}.json")}
            for cid in _case_ids(root, split)]
