"""METRICS.md calculations, with failed outputs retained in attempted counts."""
from ipaddress import IPv4Address


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def match_actions(required, proposed):
    """Match semantic action projections one-to-one; validate full outputs upstream."""
    def matches(gold, prediction):
        try:
            args, wanted = prediction["arguments"], gold["arguments"]
            if set(args) != {"source_ip", "port", "protocol", "duration_seconds"}:
                return False
            IPv4Address(args["source_ip"])
            return (prediction["action_type"] == gold["action_type"] == "block_ip"
                    and prediction["target"] == gold["target"]
                    and args["source_ip"] == wanted["source_ip"]
                    and type(args["port"]) is int and 1 <= args["port"] <= 65535
                    and args["port"] == wanted["port"]
                    and args["protocol"] == wanted["protocol"]
                    and args["protocol"] in ("tcp", "udp")
                    and type(args["duration_seconds"]) is int
                    and 1 <= wanted["duration_seconds"]["min"]
                    <= args["duration_seconds"] <= wanted["duration_seconds"]["max"] <= 3600)
        except (KeyError, TypeError, ValueError):
            return False

    # Maximum bipartite matching avoids greedy failures for overlapping ranges.
    assigned = {}

    def augment(index, visited):
        for j, prediction in enumerate(proposed):
            if j not in visited and matches(required[index], prediction):
                visited.add(j)
                if j not in assigned or augment(assigned[j], visited):
                    assigned[j] = index
                    return True
        return False

    matched = sum(augment(i, set()) for i in range(len(required)))
    precision, recall = _ratio(matched, len(proposed)), _ratio(matched, len(required))
    return {"matched": matched, "required": len(required), "proposed": len(proposed),
            "exact_match": matched == len(required) == len(proposed),
            "precision": precision, "recall": recall,
            "null_reasons": {k: "zero_denominator" for k, v in
                             (("precision", precision), ("recall", recall)) if v is None}}


def binary_metrics(gold, predictions):
    """All rows are attempted; None/invalid/undetermined are abstentions."""
    if len(gold) != len(predictions):
        raise ValueError("binary_metrics: gold/prediction lengths differ")
    tp = fp = tn = fn = positive_abstentions = negative_abstentions = 0
    for truth, prediction in zip(gold, predictions):
        if truth not in ("true_positive", "false_positive"):
            raise ValueError(f"binary_metrics: unsupported gold verdict {truth!r}")
        if prediction not in ("true_positive", "false_positive"):
            if truth == "true_positive":
                positive_abstentions += 1
                fn += 1
            else:
                negative_abstentions += 1
        elif truth == "true_positive":
            if prediction == truth:
                tp += 1
            else:
                fn += 1
        elif prediction == truth:
            tn += 1
        else:
            fp += 1
    values = {"accuracy": _ratio(tp + tn, len(gold)), "precision": _ratio(tp, tp + fp),
              "recall": _ratio(tp, tp + fn), "f1": _ratio(2 * tp, 2 * tp + fp + fn)}
    return {**values, "attempted": len(gold), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "abstentions_true_positive": positive_abstentions,
            "abstentions_false_positive": negative_abstentions,
            "null_reasons": {k: "zero_denominator" for k, v in values.items() if v is None}}


def macro_f1(gold, predictions, universe):
    """Sets per row (singleton severity, multi-label MITRE); None is failed output.

    Zero-denominator per-label F1 is 0, as METRICS requires. Out-of-universe
    predictions are disclosed, never silently added to the frozen universe.
    """
    if len(gold) != len(predictions):
        raise ValueError("macro_f1: gold/prediction lengths differ")
    if len(universe) != len(set(universe)):
        raise ValueError("macro_f1: label universe contains duplicates")
    allowed = set(universe)
    if any(not set(row) <= allowed for row in gold):
        raise ValueError("macro_f1: gold label outside frozen universe")
    predicted = [set(row) if row is not None else set() for row in predictions]
    per_label = {}
    for label in universe:
        tp = sum(label in truth and label in pred for truth, pred in zip(gold, predicted))
        fp = sum(label not in truth and label in pred for truth, pred in zip(gold, predicted))
        fn = sum(label in truth and label not in pred for truth, pred in zip(gold, predicted))
        precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
        per_label[label] = {"tp": tp, "fp": fp, "fn": fn, "support": tp + fn,
                            "precision": precision, "recall": recall,
                            "f1": _ratio(2 * tp, 2 * tp + fp + fn) or 0.0,
                            "null_reasons": {k: "zero_denominator" for k, v in
                                             (("precision", precision), ("recall", recall))
                                             if v is None}}
    return {"macro_f1": _ratio(sum(row["f1"] for row in per_label.values()), len(universe)),
            "null_reason": "empty_label_universe" if not universe else None,
            "per_label": per_label, "failed": sum(row is None for row in predictions),
            "out_of_universe_predictions": sorted(set().union(*predicted) - allowed)}


def score_cases(cases, predictions, severity_universe, mitre_universe, result_validator):
    """Score full investigation-result objects; missing key = not attempted.

    Explicit None or schema-invalid/error result = attempted failure. This is
    synthetic-pilot plumbing, not authorization or reviewed benchmark evidence.
    """
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("score_cases: duplicate case IDs")
    if set(predictions) - set(ids):
        raise ValueError(f"score_cases: unknown case IDs {sorted(set(predictions) - set(ids))}")
    counts = {"intended": len(cases), "attempted": 0, "valid": 0, "failed": 0,
              "not_attempted": 0, "not_attempted_reasons": {}}
    gold_verdict, predicted_verdict, gold_severity, predicted_severity = [], [], [], []
    gold_mitre, predicted_mitre, per_case = [], [], {}
    for case in cases:
        cid, labels = case["case_id"], case["labels"]
        if cid not in predictions:
            counts["not_attempted"] += 1
            counts["not_attempted_reasons"][cid] = "no_prediction_supplied"
            per_case[cid] = {"status": "not_attempted", "reason": "no_prediction_supplied"}
            continue
        counts["attempted"] += 1
        result = predictions[cid]
        errors = list(result_validator.iter_errors(result))
        reason = None
        if errors:
            reason = "invalid_output: " + errors[0].message
        elif result["status"] != "ok":
            reason = "error_output"
        elif result["incident_id"] != labels["incident_id"]:
            reason = "incident_id does not match case"
        elif any(a["incident_id"] != labels["incident_id"] for a in result["recommended_actions"]):
            reason = "action incident_id does not match case"
        valid = reason is None
        counts["valid" if valid else "failed"] += 1
        gold_verdict.append(labels["verdict"])
        predicted_verdict.append(result["triage_verdict"] if valid else None)
        gold_severity.append({labels["gold_severity"]})
        predicted_severity.append({result["risk_level"]} if valid else None)
        gold_mitre.append(set(labels["mitre_techniques"]))
        predicted_mitre.append(set(result["mitre_techniques"]) if valid else None)
        actions = match_actions(labels["required_actions"], result["recommended_actions"]) if valid else None
        per_case[cid] = {"status": "valid" if valid else "failed", "reason": reason,
                         "action_exact_match": actions["exact_match"] if valid else False,
                         "actions": actions}
    return {"counts": counts, "per_case": per_case,
            "binary": binary_metrics(gold_verdict, predicted_verdict),
            "severity": macro_f1(gold_severity, predicted_severity, severity_universe),
            "mitre": macro_f1(gold_mitre, predicted_mitre, mitre_universe),
            "action_exact_match": _ratio(sum(r.get("action_exact_match", False)
                                             for r in per_case.values()), counts["attempted"]),
            "action_null_reason": "zero_denominator" if not counts["attempted"] else None}
