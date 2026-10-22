"""METRICS.md calculations, with failed outputs retained in attempted counts."""
from collections import Counter
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
    """Score results keyed by case_id or incident_id; missing key = not attempted.

    Explicit None or schema-invalid/error result = attempted failure. This is
    synthetic-pilot plumbing, not authorization or reviewed benchmark evidence.
    """
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("score_cases: duplicate case IDs")
    incident_to_case = {}
    for case in cases:
        iid = case['input']['incident_id']
        if iid in incident_to_case:
            raise ValueError(f"{case['case_id']}: duplicate incident_id {iid}")
        incident_to_case[iid] = case['case_id']
    aliases = {cid: cid for cid in ids}
    for iid, cid in incident_to_case.items():
        if iid in aliases and aliases[iid] != cid:
            raise ValueError(f"{cid}: ambiguous incident_id/case_id key {iid}")
        aliases[iid] = cid
    # A sequence of pairs can preserve duplicates that a dict would overwrite.
    entries = predictions.items() if hasattr(predictions, 'items') else predictions
    normalized = {}
    for key, value in entries:
        if key not in aliases:
            raise ValueError(f"score_cases: unknown incident_id or case_id {key!r}")
        cid = aliases[key]
        if cid in normalized:
            raise ValueError(f"{cid}: duplicate prediction for incident_id {cases[ids.index(cid)]['input']['incident_id']}")
        normalized[cid] = value
    predictions = normalized
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


def faithfulness(claims):
    """Claims are status strings or records with status; failed judgements are unjudged."""
    counts = Counter({'supported': 0, 'unsupported': 0, 'unjudged': 0})
    for index, claim in enumerate(claims):
        status = claim.get('status') if isinstance(claim, dict) else claim
        if status not in counts:
            raise ValueError(f'faithfulness: claim {index} has invalid status {status!r}')
        counts[status] += 1
    total = sum(counts.values())
    share = counts['unjudged'] / total if total else None
    reason = ('zero_claims' if not total else
              'unjudged_share_exceeds_10_percent' if counts['unjudged'] * 10 > total else None)
    value = counts['supported'] / total if reason is None else None
    return {'faithfulness': value, 'hallucination_rate': 1 - value if value is not None else None,
            'claim_counts': {**counts, 'total': total}, 'unjudged_share': share, 'reason': reason}



def cohens_kappa(rater_a, rater_b):
    """Complete paired string categories; rows=A, columns=B, diagonal retained.

    Apply before adjudication. Missing ratings must not be silently discarded.
    """
    if len(rater_a) != len(rater_b):
        raise ValueError('cohens_kappa: rater lengths differ')
    ratings = list(rater_a) + list(rater_b)
    if any(not isinstance(v, str) or not v for v in ratings):
        raise ValueError('cohens_kappa: nonempty string categories required; no missing ratings')
    categories = sorted(set(ratings))
    n = len(rater_a)
    a, b = Counter(rater_a), Counter(rater_b)
    table = {x: {y: 0 for y in categories} for x in categories}
    for x, y in zip(rater_a, rater_b):
        table[x][y] += 1
    matches = sum(table[x][x] for x in categories)
    result = {'kappa': None, 'raw_agreement': matches/n if n else None, 'n': n,
              'agreement_count': matches, 'disagreement_count': n-matches,
              'category_counts': {'rater_a': {x:a[x] for x in categories},
                                  'rater_b': {x:b[x] for x in categories}},
              'disagreement_table': table, 'chance_agreement': None,
              'reason': 'no_paired_ratings' if not n else None}
    if n:
        expected_matches = sum(a[x]*b[x] for x in categories)
        result['chance_agreement'] = expected_matches/(n*n)
        if expected_matches == n*n:
            result['reason'] = 'chance_agreement_is_1'
        else:
            result['kappa'] = (matches*n-expected_matches)/(n*n-expected_matches)
    return result


def weighted_kappa(rater_a, rater_b):
    """Owner-selected quadratic weighted Cohen's kappa on fixed ordinal scores 1–5.

    Weights are squared distance / 16. Original paired ratings only; no imputation.
    """
    if len(rater_a) != len(rater_b):
        raise ValueError('weighted_kappa: rater lengths differ')
    if any(type(v) is not int or not 1 <= v <= 5 for v in list(rater_a) + list(rater_b)):
        raise ValueError('weighted_kappa: ratings must be integers 1–5; no missing ratings')
    n = len(rater_a)
    a, b = Counter(rater_a), Counter(rater_b)
    observed_sum = sum((x-y)**2 for x, y in zip(rater_a, rater_b))
    expected_sum = sum(a[x]*b[y]*(x-y)**2 for x in range(1, 6) for y in range(1, 6))
    reason = 'no_paired_ratings' if not n else 'zero_expected_disagreement' if not expected_sum else None
    return {'kappa': 1-observed_sum*n/expected_sum if reason is None else None,
            'raw_agreement': _ratio(sum(x == y for x, y in zip(rater_a, rater_b)), n),
            'n': n, 'weighting': 'quadratic', 'categories': [1, 2, 3, 4, 5],
            'observed_disagreement': _ratio(observed_sum, 16*n),
            'expected_disagreement': _ratio(expected_sum, 16*n*n), 'reason': reason}
