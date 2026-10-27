# SOC alert normalizer — S1-T06 / Issue #14

The normalizer translates one Wazuh log alert into the existing incident v1
contract. It preserves observed facts; it does not decide whether an attack
happened. No model, network connection, response execution or Wazuh installation
is needed to normalize the supplied files.

## Try it step by step

Run from the project root in the [development environment](../../docs/development.md):

```sh
docker compose build dev
docker compose run --rm -T dev python -B -m backend.normalizer infrastructure/soc-lab/evidence/lab01-run01-alert.json
```

The command reads Achraf's first saved alert, extracts its facts, builds an
incident and validates it against the unchanged [incident schema](../contracts/v1/incident.schema.json).
The result goes to stdout. View the readable [expected first incident](../../tests/normalizer/fixtures/lab01-run01-incident.json)
and [second incident](../../tests/normalizer/fixtures/lab01-run02-incident.json).

To save the result outside the source tree:

```sh
docker compose run --rm -T dev python -B -m backend.normalizer infrastructure/soc-lab/evidence/lab01-run01-alert.json > /tmp/cybersoc-incident.json
```

To send it to an already running local [backend](../README.md):

```sh
curl --fail-with-body -X POST http://127.0.0.1:8000/incidents \
  -H 'Content-Type: application/json' --data-binary @/tmp/cybersoc-incident.json
```

First delivery returns 201; repeating the same event returns 200 with
`created: false`. Changing facts under the same source/event identity returns
409. Sending an incident does not automatically investigate it or execute actions.
These HTTP behaviors are exercised in normalizer integration tests with the real
backend and an isolated temporary SQLite database; they do not establish a live
lab-to-model run.

## Input and output rules

Accept one OpenSearch document with `_source`, or one raw Wazuh alert object.
JSON arrays, JSONL streams and other detector formats are outside this initial
adapter. Required source fields: `id`, `timestamp`, `manager.name`, `agent.id`,
`agent.name`, `rule.id`, `rule.level` and `rule.description`. Missing required
facts fail; absent optional fields do not cause fabricated values. Supplied
optional fields must have the expected types and valid addresses.

| Incident field | Mapping |
|---|---|
| `schema_version` | `1.0.0` |
| `source` | Trusted deployment namespace; default `wazuh:lab` |
| `source_event_id` | Wazuh `id` inside the alert, never outer index `_id` |
| `incident_id` | Deterministic UUIDv5 over the JSON pair `[source, source_event_id]`, prefixed `INC-` |
| `timestamp` | Alert timestamp, parsed with explicit offset, converted to UTC ending in `Z` |
| `description` | Rule ID/level/description, labelled address/user/host roles, original `full_log` when supplied |
| `severity` | Explicit project mapping below |
| `entities` | Agent name, observed hostname, source/destination/management IPs, source/destination users, log program when supplied |
| `raw_event_ref` | Optional inert evidence reference; CLI defaults to the input path |
| `ingestion_kind` | CLI defaults to `replay`; saved real alerts remain replay deliveries |

Entity order is fixed and duplicate type/value pairs are removed. Entity `host`
values can include both Wazuh's agent name (`linux-01`) and observed hostname
(`linuxsoc`); they are not claims of two physical machines. Address roles remain
labelled in the description because v1 entities have no role field. The endpoint's
SSH destination IP is not inferred from the lab topology when absent in the alert.
No entity is invented from detector MITRE labels. Detector annotations and all
unmapped source fields remain available in the referenced original evidence.
`firedtimes` is not interpreted as a login-attempt count or correlation verdict.

The backend deduplicates and persists events; the normalizer does not maintain a
database or silently drop duplicates. Same identity with changed facts produces
the same incident ID, allowing backend conflict detection. Changing delivery kind
or raw-reference location does not change identity or core event content.
Use a different stable `--source` per independent Wazuh deployment. Keep it fixed
when replaying events from that deployment. Wazuh event IDs must be unique within
the configured namespace; coordinated managers need separately scoped namespaces
if they cannot guarantee that property. Changing mapping rules for an already
ingested event can cause a conflict; do not silently rewrite stored evidence.

## Severity mapping: wazuh-level-v1

This is the project's initial adapter policy, subject to Oussama's review, not a
claimed vendor mapping or an AI risk assessment. It groups the detector's numeric
range monotonically into the contract's five labels.

| Wazuh level | Incident severity |
|---|---|
| 0–3 | informational |
| 4–6 | low |
| 7–9 | medium |
| 10–12 | high |
| 13–16 | critical |

Both supplied level-5 alerts therefore become `low`. All 17 levels (0–16) and invalid
types/ranges are tested. The AI's later `risk_level` is separate. No true/false
positive label, investigation or MITRE ground truth is created here.

## Python interface and errors

```python
from backend.normalizer import normalize_alert

incident = normalize_alert(raw_alert, source='wazuh:lab',
                           ingestion_kind='replay', raw_event_ref='fixture:LAB-01/run-001')
```

Actual live ingestion callers may explicitly set `ingestion_kind='live'`; this
does not create a live collector. CLI input is a saved file or stdin (`-`), so
it only allows `replay` or `synthetic`. With stdin, supply `--raw-event-ref` when
provenance is available. References are never fetched or executed.

CLI input is bounded to 65536 bytes and 32 JSON nesting levels. Duplicate JSON
keys, non-finite numbers, invalid UTF-8 and malformed JSON are rejected. The
Python interface accepts already decoded JSON dictionaries. UTC timestamps accept
`Z`, `+HHMM` or `+HH:MM`, with up to six fractional digits; ambiguous timestamps
without an offset are rejected. Output fractions are normalized to six digits
when nonzero, so `.130000Z` and `.130Z` represent the same instant.

Output passes offline schema validation, including IP format checks, before it
is emitted. Overlong descriptions are rejected rather than silently truncated.
Errors exit 2 with sanitized messages on stderr and no incident on stdout.
Raw logs are untrusted data and may contain sensitive information; the adapter
does not promise general secret removal. Protect real inputs/outputs outside Git.
Original lab exports, their manifest and the v1 contracts are unchanged.

## Tests and completion

```sh
docker compose run --rm -T dev python -B -m unittest discover -s tests/normalizer -v
```

Tests cover both real exports, explicit expected output fixtures, raw/wrapped
equivalence, timestamp conversion, all severity levels, stable replay identity,
namespace separation, malformed fields/JSON, IPv6, CLI behavior and real API
ingestion/duplicate/conflict semantics. They use no model and generate no lab
traffic. Saved exports are development fixtures, not a frozen evaluation split.

Related: [Issue #14](https://github.com/CyberSOC-ai/cybersoc-ai/issues/14),
[Achraf's lab handoff](../../infrastructure/soc-lab/S1-T05-RESULTS.md),
[contract semantics](../contracts/README.md).
Implementation and local validation do not constitute hosted CI or reviewer
acceptance; PR workflow and assigned reviewer Oussama remain required before Done.
