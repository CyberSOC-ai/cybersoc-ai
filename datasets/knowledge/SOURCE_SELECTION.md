# S2-T01 expanded source selection

Owner Ahmed; user-selected expansion on 2026-10-29. Exact revisions, paths and
baseline versions live in [sources.json](sources.json). These are reproducible
initial selections, not proof of sufficient retrieval quality or comprehensive
security coverage.

| Source | Acquisition and role | Coverage boundary |
|---|---|---|
| MITRE ATT&CK Enterprise | Existing commit-pinned STIX snapshot; active techniques for reference and separate relationships for graph preparation | Other STIX object types excluded; graph endpoints can refer to upstream objects outside this selection |
| NVD | Entire official annual JSON 2.0 feed for **2024**, verified against its META size/SHA-256; bulk vulnerability reference | Covers that identifier year, not all historical/current CVEs; add explicit years in the selection for a broader mirror |
| Official CVE List V5 | Five commit-pinned CVE records: CVE-2024-6387, CVE-2024-3094, CVE-2024-1086, CVE-2024-2961, CVE-2024-3400 | Focused primary-record supplement; not a complete CVE List mirror and not evidence our lab has these vulnerabilities |
| CISA KEV | Full commit-pinned catalog; exact CVE-ID enrichment plus structured lookup | Catalog membership is known-exploitation context; absence is not evidence of safety, and membership does not prove our incident was exploited |
| MITRE CWE | Existing release 5.0 snapshot; active weakness descriptions/relationships | Consumed XML fields validated; no full upstream XSD validation |
| SigmaHQ | Three Linux rules covering account creation, OpenSSH errors and account discovery | All selected rules currently have upstream status `test`; preserve that status and false-positive guidance; no production detection-quality claim |
| Threat Hunter Playbook | Two Windows reference guides: local PowerShell execution and LSASS memory access | Reference-only content, including code/query text; never executed; does not claim deployed Windows lab coverage |
| Existing Wazuh observations | Two existing normalized SSH authentication-failure observations | Isolated observations, not a demonstrated brute-force attack; development-only |
| OTRF/Splunk event data | Selected Linux audit and Sysmon files under explicit source/run/family assignments | 33 public event excerpts, not 33 independent incidents; development-only; see [assignments](EXTERNAL_ASSIGNMENTS.md) |

The reference sources explain concepts, detection patterns and investigation
methods. Current Wazuh observations remain the evidence for what occurred in an
actual incident. External examples provide development material; their labels
must not become retrieval answers. Keep a separately reviewed frozen evaluation
set outside the corpus.

## Vulnerability joins

NVD and the CVE Program share CVE identifiers. The composer emits one searchable
record for each CVE, retains NVD enrichment and preserves CNA/ADP data and alternate
descriptions with a provenance chain. KEV is joined by the exact CVE ID, never
semantic similarity. Unmatched KEV records remain in `facts.sqlite` for exact
lookup and are counted; they do not create duplicate vector documents. Preserve
missing enrichment as missing. Version applicability needs actual software/version
observations and downstream matching; an ID or similar description alone does
not establish exposure.

Supplemental facts must be cited using the appropriate provenance-chain snapshot.
Do not attribute a KEV assertion or CNA-specific field to the NVD snapshot simply
because NVD supplies the primary searchable description. The current backend v1
evidence schema accepts the added `detection_rule` and `playbook` source values;
consumers with copied/frozen source enums must refresh them. Existing values and
valid examples remain accepted. No API route, embeddings, scoring or vector-store
selection is added here.

## Acquisition/storage

Only explicitly selected files from fixed official repositories are acquired.
Revision branches such as `main`/`master` are resolved to commits before selection.
Downloaders preserve notices, hashes, selection and receipts; Git LFS objects are
verified against their pointer OID/size. Archives are read without extracting
upstream paths. No payload execution, notebook execution or advisory crawling
occurs. The annual NVD importer has size/time budgets and detects META changes
while downloading. Larger feeds require an explicit budget review.

These are public sources with source-specific terms, not a universal public-domain
corpus. Preserve pinned notices. Sigma uses the upstream Detection Rule License;
OTRF has inconsistent README/root-license labels to resolve before redistribution.
No raw source artifacts are committed or publicly redistributed by this work.
Shared artifact storage remains proposed in ADR-006. `.local/ingestion` supplies
local replay only; preserve those snapshots through agreed storage before cleanup.

## Next validation

Soulaiman reviews the handoff schema, source selection and grouping policy.
S2-T02 chooses chunking, embeddings and the vector database; S2-T03 measures
retrieval against reviewed relevance judgments. Evaluate per scenario and source,
including false-positive controls and questions with insufficient evidence.
No corpus-size threshold, source reputation or passing parser test substitutes
for those retrieval/answer measurements.
