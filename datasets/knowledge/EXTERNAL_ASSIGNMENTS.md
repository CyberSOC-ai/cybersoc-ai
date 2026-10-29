# External public lab excerpts — S2-T01 development assignments

Owner Ahmed; proposed assignments for Soulaiman's review. These selections extend
our two existing Wazuh observations; they are not production telemetry or new
lab experiments. No analyst verdict, automatic response or benchmark result is
claimed. Source revisions/files are pinned in [the selection](sources.json).

| Provider | Selected data | Assignment and purpose |
|---|---|---|
| OTRF Security Datasets | Linux ARP-cache discovery audit log, extracted from the selected ZIP | `G-NETWORK-DISCOVERY`; 12 audit-record excerpts, preserving observed command/audit identifiers |
| Splunk Attack Data | Linux network-tool audit log and its dataset description | `G-NETWORK-DISCOVERY`; first 20 observed audit records; documentation retained with acquisition, excluded from event retrieval |
| Splunk Attack Data | Linux Sysmon SSH scenario | `G-SSH`; one XML event excerpt; linked to the existing SSH pilot family |

These are record excerpts, not 33 independent incidents. Several audit records may
belong to one process/event. Grouping by source run/family is mandatory; individual
record lines are never independently randomized into development/test splits.
Do not infer malicious intent from a command such as `arp`, `route` or `ssh`.

[external-policy.json](external-policy.json) pins each source file's SHA-256,
run/family assignment, related pilot case IDs, explicit development use and an
upper selection limit of 20 excerpts per file. Unknown files are quarantined.
Changed source bytes or split bytes invalidate the assignment. If a run/family or
related case becomes held out, its related excerpts are excluded together.
Current evaluation splits are unfrozen; outputs are **development only**.

The selected event files are public lab observations. They retain the original
published lab account, hostname, command and address observations; no new
private identifiers are acquired. They do not contain new project credentials.
Review was limited to these selected small files and source descriptions; it is
not a claim of independent privacy certification for entire upstream collections.
Input checks reject explicit evaluator-label keys and unsupported formats.
Manual review remains necessary for sensitive prose, implicit labels and
near-duplicate/template relationships before adding any new source file.

Each excerpt preserves its provider, original file digest, file path and line
index as lineage metadata. Do not include technique-bearing paths, split/group
membership or dataset labels in embedding/prompt content. The original event
text is represented as a typed observation; no missing severity, timestamp,
backend incident identity or verdict is invented. Recorded snippets and source
links are data and are never executed or visited during normalization.

The OTRF archive/license and Splunk source files/license remain in ignored local
artifact storage, and notices are copied into derived corpora. OTRF's root LICENSE
and README have differing license labels; retain the pinned notice and resolve
any redistribution ambiguity before publishing raw or derived datasets. This
work does not grant new redistribution rights or publish source logs.
