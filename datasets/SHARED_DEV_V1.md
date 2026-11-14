# Shared development data — shared-dev-v1

Frozen on 11 November 2026 for the initial B0 development work. This release
provides common source data for No-RAG, Vector RAG and later Graph RAG. It is a
development snapshot, not a final benchmark or evidence of completed B0 delivery.

## Download and identify the release

[Google Drive release folder](https://drive.google.com/drive/folders/1mHw5ayPQxfuqL26lSgOwTgrK8BtH8bl1)

Download both files without renaming them:

- [shared-dev-v1.zip](https://drive.google.com/file/d/11ARM0dCW5Yt07gk2eoe90GWyI904DbUp/view)
- [shared-dev-v1.zip.sha256](https://drive.google.com/file/d/11H4EL29kK20Pw297xnH1Ys5vnwhV7KIw/view)

| Identity | Expected value |
|---|---|
| Release ID | `shared-dev-v1` |
| ZIP size | 885088 bytes |
| ZIP SHA-256 | `071794c3cd0c098af9962ea1f96f6f84b50ddd5f9f55f1484d93561a4fe735b5` |
| Extracted manifest SHA-256 | `8376256e0d5bfa6733fc6d045ffa42f23be779fe51a1d23a8fae0a79315ef88e` |
| Payload | 81 files, including 80 entries checked by the bundled `SHA256SUMS` |

Check the ZIP against this Git-tracked hash as well as the downloaded checksum
file. Checksums detect changed bytes; they are not digital signatures or proof
that the contents or expected answers are correct.

Drive metadata checked on 11 November 2026 shows anyone-with-link **Editor** access
on the folder. Use Viewer access for a frozen release and reserve editing for
maintainers. Sharing permissions were not changed by this documentation update.
Archive size and the uploaded checksum file match the local package; a fresh
teammate/cloud download and restore has not yet been demonstrated.

## Contents and boundaries

| Release path | Contents | Use |
|---|---|---|
| `incidents/inputs/` | Seven synthetic normalized incident-v1 JSON inputs | Same incidents for every investigation mode |
| `knowledge/records.jsonl` | 21 reference documents with IDs, titles, source URLs and text | Explicit input for Vector preparation and future Graph work; no reference context for No-RAG |
| `knowledge/sources.json` | Publisher snapshots, acquisition times, source versions where available and hashes | Traceability and preparation checks |
| `knowledge/snapshots/`, `knowledge/text/`, `knowledge/notices/` | Original source bytes, readable text and preserved notices | Reproduction and source usage review |
| `evaluation/cases.json`, `evaluation/case-reviews/` | Case inventory and draft expected behavior | Evaluator-only; never reference-index or model input |
| `evaluation/queries.json`, `evaluation/judgments.json` | 21 retrieval questions and draft relevance expectations | Submit question text to retrieval; keep judgments separate |
| `AGREEMENT.md`, `VERSIONING.md`, `manifest.json`, `SHA256SUMS` | Development agreement, change rules, inventory and integrity checks | Release identification and handoff |

The cases cover Linux SSH, Linux account creation, Linux file changes, Windows
logins, administrative group membership, PowerShell maintenance and OpenSSH client
vulnerability applicability. They are simulated incidents, not real intrusions
or raw Wazuh exports. Some narratives include separately supplied business or
configuration context that a single real alert would not contain.

The references include seven MITRE ATT&CK pages, platform/monitoring documentation,
and a CVE record, OpenSSH advisory and mapped CWE entry. Technical references
explain possibilities; they cannot establish missing incident facts or approval.

The 21 retrieval questions include 18 answerable questions and three questions
that cannot be answered from this reference collection. Expected behavior and
relevance judgments remain pending owner/independent review; development-use
agreement does not establish accepted gold labels.

## Verify and extract

On Linux with `sha256sum` and `unzip`, from the directory containing both downloads:

```sh
sha256sum -c shared-dev-v1.zip.sha256
sha256sum shared-dev-v1.zip
mkdir shared-dev-v1-check
unzip -n shared-dev-v1.zip -d shared-dev-v1-check
cd shared-dev-v1-check/shared-dev-v1
sha256sum manifest.json
sha256sum -c SHA256SUMS
```

Compare the printed ZIP and manifest hashes with the table above. Use a new
destination rather than extracting over existing data. If a hash differs, stop
and resolve the changed artifact before running a pipeline.

## Pipeline use and version changes

No-RAG receives incident inputs and the configured instructions/policy. Vector
RAG searches passages and embeddings derived from the reference corpus. Graph
RAG will query entities and supported relationships derived from those sources.
Both representations must preserve source identity and record any coverage gaps.
Do not recursively index the release directory; evaluator files stay outside
searchable knowledge and model context.

No chunks, embeddings, vector collection, graph database or predictions are
included. Collection/review files are not automatically compatible with existing
ingestion/evaluation loaders; preparation and integration are separate work.

Keep v1 unchanged. Any correction, label adjudication, addition or source refresh
creates `shared-dev-v2` or the next release, recording its predecessor manifest
hash, changed IDs and reasons. Preserve earlier releases. Derived artifacts live
separately and record the source release/manifest, code/configuration and relevant
model/tokenizer identities. Never silently reuse an index with changed sources.

All included cases and questions are development-only. Final-test groups remain
unselected; related scenarios/runs, near-duplicates and their derived records must
stay together. Development material cannot later be called untouched test data.

## Remaining foundation work

- Complete expectation review and reserve independent final-test groups.
- Add the roadmap's eligible historical SOC and threat-intelligence coverage.
- Resolve outstanding source-specific reuse questions recorded in the release.
  Uploading the package does not itself establish third-party redistribution rights.
- Verify the chosen local/cloud setup and an independent fetch/restore cycle.

GitHub stores this guide and release identity; Drive stores the downloadable
artifact. Private local notes, preparatory bundles and downloaded source corpora
are outside this documentation commit. The frozen package retains its original
local-only status at packaging; current hosting is recorded here separately.

Continue [B0](../docs/ROADMAP.md) in order: shared foundation → No-RAG → small Vector
RAG → independent reproduction. Storage rationale is recorded in
[ADR-006](../docs/adr/ADR-006.md). No pipeline/model-quality result is claimed here.
