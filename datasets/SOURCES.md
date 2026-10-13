# Knowledge sources and evaluation inventory

Checked: 2026-10-13. Entries describe planned acquisition, not existing artifacts. Record immutable release/revision and license evidence at acquisition; do not use an unpinned `latest` URL as a reproducible dataset version.

## Knowledge and threat-intelligence sources

| ID / intended use | Official source and acquisition format | Licensing / usage notes | Version / preparation and limits |
|---|---|---|---|
| K-ATTACK / required S2-T01, S3 | [MITRE ATT&CK® STIX repository](https://github.com/mitre-attack/attack-stix-data); Enterprise STIX JSON release | [MITRE license](https://github.com/mitre-attack/attack-stix-data/blob/master/LICENSE.txt) permits research/development/commercial use with copyright and license retained; no endorsement implied | Pin release and commit/hash; preserve STIX and external technique IDs, relationships and revocation flags; reject revoked/deprecated techniques from current mappings |
| K-CVE / required S2-T01, S3 | [NVD data feeds](https://nvd.nist.gov/vuln/data-feeds), [CVE API 2.0](https://nvd.nist.gov/developers/vulnerabilities); bounded JSON subset | [NIST data policy](https://www.nist.gov/open/license) distinguishes government-produced public data from protected third-party material; retain attribution/notices and inspect dataset-specific terms | Pin acquisition and hash; keep CVE IDs, modification times, references, available CVSS/CWE/CPE. Missing enrichment stays missing. Cache offline, obey request limits, never crawl linked advisories by default |
| K-CWE / required S2-T01, S3 | [MITRE CWE downloads](https://cwe.mitre.org/data/downloads.html); versioned XML archive | [CWE terms](https://cwe.mitre.org/about/termsofuse.html) permit research/development/commercial use with MITRE copyright/license reproduced | Pin release and XSD; keep weakness IDs, descriptions and relationships; do not treat categories/views as individual weaknesses |
| TI-THREATFOX / intended primary S2-T08 | [ThreatFox Community API](https://threatfox.abuse.ch/api/) recent IOC JSON; [export formats](https://threatfox.abuse.ch/export/) as alternative acquisition | Auth-Key required; [abuse.ch terms](https://abuse.ch/terms-of-use/) allow authenticated nonprofit access within fair-use limits; commercial use can require subscription. Do not assume an unrestricted redistribution license | Owner Ahmed obtains access privately and confirms snapshot/normalization/indexing rights before ingestion. Pin bounded recent response, timestamp/hash and terms evidence; keep expired/stale indicators distinct. Not yet acquired |
| TI-URLHAUS / fallback candidate S2-T08 | [URLhaus Community API](https://urlhaus.abuse.ch/api/); bounded authenticated JSON/export | Same abuse.ch terms/access gate; independent coverage alternative, not a way around those conditions | Confirm rights/access before switching; record change in ADR-008. URLs need host extraction and source attribution; do not visit URLs or download payloads. Not yet acquired |

**Intended feed:** use a bounded ThreatFox recent-IOC snapshot for S2-T08 after its access/use gate is met. Normalize supported IP/domain/hash records into vector evidence and structured IOC lookup; preserve malware family, tags, source confidence when present, first/last observation and source record IDs. Do not invent confidence or malware labels when absent. IP:port indicators must retain port/protocol separately. Unsupported IOC types are counted and excluded explicitly. This is the planned implementation input, not a claim that access is already provisioned.

The official ThreatFox API documentation reports expiry of indicators older than six months. A pinned historical snapshot is useful for reproducibility but must not be described as current threat intelligence. Retain snapshot age and observation timestamps. The sample duration queried and any filtering must be recorded.

If the primary is unavailable, evaluate URLhaus under its own source/use requirements and record selection in ADR-008. If neither source is accessible/permitted, report S2-T08 blocked; a synthetic local IOC set can test adapters but cannot satisfy a real-feed ingestion claim. No raw IOC snapshot redistribution is authorized by this inventory.

## Lab logs for retrieval

The [lab scenario catalog](../infrastructure/soc-lab/README.md#3-scenario-catalog) defines stimuli and expected observations, not collected data. Wazuh owns detection; CyberSOC AI consumes and investigates alerts.

| Source ID | Producer / planned records | Eligible retrieval use and limitations |
|---|---|---|
| SOC-AUTH | `linux-01` SSH/authentication logs and `soc-01` Wazuh alerts; LAB-01 and CTRL-01 | Historical development runs; sanitized source/user/host, event times, rule/agent IDs, authentication outcome. Missing correlated alerts remain explicit collection failures |
| SOC-FIM | Linux fixture-directory FIM events/alerts; LAB-02 and CTRL-02 | Changes with integrity/path evidence; authorized maintenance context kept separate from malicious judgments |
| SOC-ACCOUNT | Linux account/privilege audit records; LAB-03 | Disposable-account development scenarios after audit collection is enabled; preserve operator authorization reference |
| SOC-WINDOWS | Optional registered Windows process/PowerShell records; LAB-04 | Only if Windows collection is actually deployed; no coverage claimed otherwise |
| SOC-NET | Endpoint network events and registered local sink receipts; LAB-05 | Bounded connection metadata; no public connections or packet payloads in Git |
| SOC-IOC | Inert file hash/local synthetic IOC match; LAB-06 | Clearly labeled synthetic IOC-set version and detection provenance; no live malware samples |

Record run/scenario ID, stable endpoint and inventory revision, Wazuh release/rule configuration, event/alert identifiers, UTC times, sanitized record reference and split membership. Raw artifacts stay restricted. Replace credentials and unnecessary personal identifiers while preserving consistent pseudonyms needed for correlation. Data generation grants no permission to redistribute embedded third-party content.

S1-T06 normalizes eligible alerts; S2-T01 produces a separate SOC-log corpus/collection and graph ETL inputs with provenance. Only development/history records explicitly permitted by the frozen split manifest may enter retrieval. Quarantine unlabeled or unassigned runs until split membership is known. Related logs, alerts, summaries, entity associations and duplicates from one held-out incident are excluded together. Ground-truth verdicts/expected actions never become retrieved incident content.

## Candidate SOC datasets

| Candidate / role | Official source, format and labels | Licensing / acquisition notes | Fit and gaps |
|---|---|---|---|
| Lab-built `soc-eval-v1` / primary | Project lab run records and normalized alerts; scenario ground truth and benign controls | Project-generated sanitized records; owners verify no third-party/private content; dataset publication license remains a team decision | Closest match to incident assistant; requires real collected cases, independent reviewed labels, balanced controls and development/frozen-test split in S1-T02 |
| OTRF Security Datasets / optional event examples | [Official repository](https://github.com/OTRF/Security-Datasets); replayable security event datasets and context | [Repository MIT license](https://github.com/OTRF/Security-Datasets/blob/master/LICENSE); retain notices and inspect per-artifact rights/content before copying | Useful Windows/event context; not pre-labeled full assistant outcomes. Requires normalization, reviewed triage/action labels and split grouping |
| UNSW-NB15 / optional network context | [UNSW source page](https://research.unsw.edu.au/projects/unsw-nb15-dataset); CSV flow features/labels and raw formats | Academic research use granted; commercial use needs author agreement; preserve the five required paper citations listed by the source. Raw download access untested | Network attack/normal labels, not complete SOC incident explanations; no automatic severity/MITRE/action ground truth; avoid large PCAP downloads |
| CICIDS2017 / optional network context | [UNB CIC source page](https://www.unb.ca/cic/datasets/ids-2017.html); labeled flows/CSV and PCAP | Researcher access described with required citation to Sharafaldin, Lashkari and Ghorbani (ICISSP 2018); do not infer unrestricted commercial/redistribution rights | Optional small sanitized flow subset; labels alone cannot validate assistant faithfulness, action safety or MITRE attribution |

External candidates supplement lab evidence and do not replace S1-T02's case/label protocol. Network classification labels are not automatically equivalent to true/false-positive incident verdicts. Public availability is not a blanket redistribution license. Keep citations/license records in each artifact manifest, including acquisition-time terms and any required permission. No third-party data is committed here.

## Evaluation-case requirements for S1-T02

Each case needs a stable case/incident ID, dataset version, source/run references, acquisition provenance, environment/configuration references, sanitized incident and relevant contextual evidence. Keep evaluator-only expected labels separate from model inputs and retrieval records:

- Triage verdict: true positive or false positive, defined against scenario intent and supporting observations; unresolved/failing collection is not a clean negative case.
- Expected severity and evidence-backed MITRE technique/sub-technique mapping; explain unknown/not-applicable labels rather than fabricating a technique.
- Expected action type, exact normalized target and permitted arguments, or an explicit no-response expectation for benign cases; analyst approval is required for every state-changing recommendation that is executed.
- Gold evidence references and relevance judgments for retrieval; atomic supported claims for faithfulness and the four CDC response-quality dimensions.
- Label author/reviewer, rationale, adjudication status and evaluation protocol version. Never copy ground truth from the evaluated model's output.

S0-T06 fixes metric and split conventions; S1-T02 supplies the implemented protocol and the CDC target of at least 50 manually double-labeled claims for judge validation. Group by incident/scenario-run family before splitting; keep near-duplicates together, freeze test membership/version, and record exclusions. Separate malicious-style simulations from authorized benign controls. Test labels are accessed only by evaluators; they cannot enter prompt design, fine-tuning or retrieval indexes. This inventory does not select split ratios, redefine metrics or produce benchmark results.

## Acquisition checklist for downstream tasks

Verify rights/access and notices; choose immutable source revision; capture bounded content and integrity hash; sanitize and validate; record exclusions and missing fields; assign split/provenance; store outside Git where appropriate; test normalization; obtain assigned review before claiming ingestion is ready. These are implementation gates, not results already achieved by S0-T05.
