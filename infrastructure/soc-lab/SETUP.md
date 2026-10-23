# S1-T05 — Reproduce the Windows Docker lab

Read [results/limitations](S1-T05-RESULTS.md). The original deployment was guided interactively; clean-machine reproduction of this document remains pending. Use disposable authorized lab systems only.

1. Install Docker Desktop with Linux/WSL 2 backend on Windows and VirtualBox with two Ubuntu Server VMs. Verify docker version shows Client/Server. Record exact host/VM versions and resources. Keep host RAM/storage headroom. The observed disk-full failure demonstrates the need for monitoring.
2. Configure Host-only Windows 192.168.56.1 and endpoint 192.168.56.20/24. Internal cybersoc-test connects endpoint 192.168.77.20/24 and simulation 192.168.77.30/24, without gateways. Adapt addresses to avoid host/VPN overlaps. Discover interface names with ip -br address. Use Netplan static entries, netplan generate and netplan try from VM console; preserve temporary NAT until downloads finish. Disable IPv4/IPv6 forwarding on endpoint, remove NAT before scenario, inspect routes/firewall and preserve recovery access. Simulation has no Host-only interface.
3. Clone the [upstream Docker stack](https://github.com/wazuh/wazuh-docker/tree/v4.14.9/single-node) outside CyberSOC. Use tag v4.14.9 and record git rev-parse HEAD. Follow [vendor deployment](https://documentation.wazuh.com/current/deployment-options/docker/wazuh-container.html). Do not copy the live runtime into this repository.

```powershell
git clone --branch v4.14.9 --depth 1 https://github.com/wazuh/wazuh-docker.git
cd wazuh-docker/single-node
wsl -d docker-desktop -u root -- sysctl -w vm.max_map_count=262144
```

4. In upstream Compose publish manager only as 192.168.56.1:1514:1514 and 192.168.56.1:1515:1515. Remove manager 514/55000 and indexer 9200 host publications. Set dashboard to 127.0.0.1:8443:5601. Keep named data volumes and internal service connections. Restrict enrollment to the intended endpoint and close it when no longer needed. Verify Windows firewall; do not disable it globally.
5. Set disabled=yes in manager active-response block in config/wazuh_cluster/wazuh_manager.conf. Generate local certificates and download images:

```powershell
docker compose config --quiet
docker compose -f generate-indexer-certs.yml run --rm generator
docker compose pull
```

6. Configure private, distinct strong passwords following [Wazuh password management](https://documentation.wazuh.com/current/deployment-options/docker/changing-default-password.html). admin hash must match INDEXER_PASSWORD in manager AND dashboard. kibanaserver hash must match DASHBOARD_PASSWORD. API account wazuh-wui must match API_PASSWORD in both services and password in config/wazuh_dashboard/wazuh.yml. Preserve run_as=true. Apply indexer hashes using vendor securityadmin.sh procedure; recreate services after environment changes (restart alone does not reload env). Never print rendered secrets, paste passwords in issues or commit their hashes/private keys. This package deliberately contains no live secret-bearing Compose.
7. Start with docker compose up -d, check docker compose ps and open https://127.0.0.1:8443. Verify dashboard login and API online, not merely running containers. After credential changes discard stale browser sessions. Reapply vm.max_map_count after Docker/WSL restart when necessary.
8. On Ubuntu endpoint install agent 4.14.9 with manager 192.168.56.1 and name linux-01:

```bash
wget -O wazuh-agent-4.14.9.deb https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_4.14.9-1_amd64.deb
sudo WAZUH_MANAGER='192.168.56.1' WAZUH_AGENT_NAME='linux-01' dpkg -i ./wazuh-agent-4.14.9.deb
sudo systemctl daemon-reload
sudo systemctl enable --now wazuh-agent
```

9. Verify agent Active and Connected to server in ossec.log. Set disabled=yes ONLY in its active-response block, preserve CA settings and restart. Use existing unfiltered journald collection; avoid adding duplicate auth.log collector. Install OpenSSH server on endpoint and client on simulation while NAT available. Create disposable labtest; keep its password private. Verify effective SSH password authentication for that account, not root. Verify the host fingerprint using endpoint console before trusting SSH.
10. Remove NAT, verify isolation, take clean snapshots and record pre-state. Ensure Docker responsive, API online, agent Active and disk headroom before exercising. On simulation:

```bash
date -u
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o NumberOfPasswordPrompts=1 labtest@192.168.77.20
date -u
```

Enter ONE deliberately wrong password, then stop. Search Threat Hunting with agent.name:"linux-01" AND data.srcip:"192.168.77.30" in matching timeframe. Save alert JSON and screenshot, repeat as a separately identified run after ending sessions/resetting test state. Fill [RUN_TEMPLATE.md](RUN_TEMPLATE.md), preserving failures and unknown metadata. Suggested future definition EXP-S1T05-ssh-failure-v1 and unique RUN-<UTC timestamp>-<suffix> identifiers; original exports were not prelabelled with these IDs. Rule 5760 proves single failure detection, not correlated brute force.
11. Stop guest OSs with sudo poweroff and containers with docker compose stop. Restart Docker Desktop, sysctl and docker compose up -d. Never use down -v, WSL unregister or factory reset as ordinary cleanup. Preserve volumes and evidence.

Repository checks run from CyberSOC root using its development Compose, separately from this Wazuh runtime. CI does not deploy or certify the lab. See [development setup](../../docs/development.md).
