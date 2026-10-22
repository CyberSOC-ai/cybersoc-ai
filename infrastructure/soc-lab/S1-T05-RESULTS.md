# S1-T05 — SOC Lab MVP: results and handoff

Owner: Achraf. Reviewer: Ahmed (@ElrhAhmed). Evidence date: 2026-10-22.
Status: two observed detections; review, hosted CI, credential rotation and merge pending. User retains merge control.

## Actual deployment

Wazuh manager, indexer and dashboard 4.14.9 run as Linux containers in Windows Docker Desktop / WSL 2. Two Ubuntu Server VMs remain in VirtualBox: linux-01 (hostname linuxsoc) and simulation-01. This adapts the three-VM central-service plan in [S0-T07](README.md); the SOC VM is not used.

Windows Host-only address: 192.168.56.1. Endpoint enp0s8: 192.168.56.20/24; endpoint enp0s9: 192.168.77.20/24. Simulation enp0s8: 192.168.77.30/24 on internal cybersoc-test. Endpoint forwarding was disabled. Simulation console showed no default route after NAT removal. Full final endpoint/Windows firewall and isolation evidence remains to be recorded.

Observed Docker Desktop 4.96.0, Engine 29.9.1, Compose 5.6.0; agent 4.14.9. Host RAM user-reported 16 GB; Docker reported 8189050880 bytes and 8 logical CPUs. Exact WSL/VirtualBox/ISO versions, VM UUIDs, snapshots and actual VM allocations were not captured. Proposed allocations were endpoint 2 GB and simulation 1 GB; these are not measured facts.

Published ports observed: manager 1514/1515 on 192.168.56.1, dashboard 8443 on 127.0.0.1; indexer 9200 not published. Agent connected to manager; local active-response disabled=yes verified. Manager disablement was configured during setup; fresh runtime confirmation not captured. Collection is journald without an added auth.log collector.

## Observed results

| Run | Alert UTC | Raw event ID | Index document ID |
|---|---|---|---|
| 1 | 2026-10-22T13:43:25.130Z | 1792676605.79530 | FjTaY6EB8VSRWyZyN6EY |
| 2 | 2026-10-22T13:46:26.157Z | 1792676786.80539 | GzTdY6EB8VSRWyZyDKGj |

Both [run 1](evidence/lab01-run01-alert.json) and [run 2](evidence/lab01-run02-alert.json) report rule 5760, level 5, sshd: authentication failed, source 192.168.77.30, account labtest and agent linux-01 (001). [Screenshot](evidence/lab01-run01-dashboard.png) shows the first alert. Source log times are 13:43:23 and 13:46:24; those text fields have no timezone offset. Alert timestamps are explicit UTC.

This proves repeatable detection of SSH password failure. It does NOT prove correlated brute-force detection, a detection-rate/latency benchmark or one alert per attempt. firedtimes is not a per-run attempt count. Run 1 total attempts are not established by the export; run 2 followed instructions for one further attempt but a full terminal transcript was not retained. Full start/end, reset/snapshot and clock-sync metadata are unavailable. These are retrospective exploratory run records, not frozen benchmark runs. No model, normalizer or automated response was executed.

JSON bytes are preserved from the user-provided .json.txt files with extension corrected to .json. Kept addresses/account/hostname are lab identifiers. [Manifest](evidence/manifest.json) hashes supplied JSON and screenshot bytes; it is not a signed or full experiment manifest.

## Failed attempt and recovery

An earlier 11-failure sequence at 13:10:04–13:11:43 UTC exceeded the planned ten-attempt/60-second limit and occurred during manager unavailability. It is not counted as validated detection. Agent reconnected at 13:29:39. Docker reported disk full while writing init.log; Windows C: had about 1 GB free, then 22.7 GB after user cleanup. Docker/WSL recovery preceded the successful evidence. Monitor free disk and data-volume growth before repetition; do not delete Wazuh volumes as cleanup.

Authentication mismatches were corrected through consistent hashes/config and container recreation. Passwords disclosed during troubleshooting must be rotated before final acceptance; completion has not been verified. No live Compose, passwords/hashes, runtime-check YAML, certificates or VM disks are included in this package.

## Handoff to Ahmed / S1-T06

The exports are OpenSearch wrappers. `_source` is the raw Wazuh alert; live manager alerts.json lines correspond to that object without the wrapper. `_source.id` is detector event identity; `_id` is index document identity. Preserve provenance and define duplicate/replay handling explicitly.

Normalize using the [incident contract](../../backend/contracts/v1/incident.schema.json): UTC timestamps must end in Z; preserve the instant represented by +0000. Wazuh level 5 needs an explicit contract-severity mapping, not a blind copy. agent.ip is endpoint management address; data.srcip is simulation source. Detector MITRE annotations are not independently verified malicious ground truth. Context is an authorized lab simulation of failed credential use.

Generation was live; reading saved exports in tests is replay. Keep these as development fixtures; frozen evaluation split assignment belongs to S1-T02. Do not present raw exports as already normalized incidents. Follow [experiment conventions](../../experiments/README.md) for future full run metadata.

## Completion checklist

- [x] SOC service, monitored endpoint and two distinct live SSH-failure alerts evidenced.
- [x] Raw exports and screenshot inspected and packaged without runtime credentials.
- [ ] Rotate disclosed credentials and verify final isolation/host firewall.
- [ ] Ahmed reviews setup and raw-alert handoff.
- [ ] Hosted repository-checks passes; actual PR link recorded.
- [ ] User merges when ready. Task is not marked Done here.
