"""File/stdin CLI: JSON goes to stdout, sanitized failures to stderr."""
import argparse
import json
import math
from pathlib import Path
import sys

from .wazuh import MAX_BYTES, NormalizationError, normalize_alert


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON member')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Non-finite JSON number')


def parse_alert(raw):
    if len(raw) > MAX_BYTES:
        raise NormalizationError('Input exceeds 65536 bytes.')
    try:
        record = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                            parse_constant=invalid_constant)
        pending = [(record, 0)]
        while pending:
            value, depth = pending.pop()
            if depth > 32 or (isinstance(value, float) and not math.isfinite(value)):
                raise ValueError('JSON nesting or numeric limit')
            if isinstance(value, str):
                value.encode('utf-8')
            if isinstance(value, dict):
                for key, item in value.items():
                    key.encode('utf-8')
                    pending.append((item, depth + 1))
            elif isinstance(value, list):
                pending.extend((item, depth + 1) for item in value)
        return record
    except (ValueError, UnicodeError, RecursionError):
        raise NormalizationError('Input must be one valid UTF-8 JSON alert.') from None


def main():
    parser = argparse.ArgumentParser(description='Normalize one saved Wazuh alert into incident v1.')
    parser.add_argument('input', help='JSON file path, or - for stdin')
    parser.add_argument('--source', default='wazuh:lab', help='Stable deployment namespace')
    parser.add_argument('--raw-event-ref', help='Inert evidence reference; never fetched')
    parser.add_argument('--ingestion-kind', choices=('replay', 'synthetic'), default='replay')
    args = parser.parse_args()
    try:
        if args.input == '-':
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.input).open('rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
        reference = args.raw_event_ref
        if reference is None and args.input != '-':
            reference = args.input
        incident = normalize_alert(parse_alert(raw), source=args.source,
                                   ingestion_kind=args.ingestion_kind,
                                   raw_event_ref=reference)
        # Compact output stays within the API's checked serialized body limit.
        print(json.dumps(incident, ensure_ascii=False, allow_nan=False))
    except NormalizationError as error:
        print(f'Normalization failed: {error}', file=sys.stderr)
        return 2
    except OSError:
        print('Normalization failed: cannot read input or write output.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
