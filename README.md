# HydraLink

**HydraHive's AgentLink integration — agent-to-agent state protocol, native install (no Docker), tightly integrated with HydraHive2.**

HydraLink wraps [tilleulenspiegel/agentlink](https://github.com/tilleulenspiegel/agentlink) for use within the [HydraHive2](https://github.com/hydrahive/hydrahive2.0) ecosystem:

- **Native install** instead of `docker-compose` — Postgres, Redis, AgentLink-Backend run directly as systemd services. No Docker-in-LXC nightmares, no Compose-in-Core violations of HydraHive's spec.
- **ChromaDB removed** — unused in the current backend code (was reserved for a future semantic-search phase). When that phase ships, ChromaDB can be re-introduced together with the code that uses it.
- **HydraHive-friendly**: uses the same `apt`/`systemd`/`venv`-based deployment pattern that HydraHive2 itself uses. Postgres + Redis are listed as legitimate AgentLink dependencies in HydraHive2's SPEC (Tech-Stack table).

## Stack

| Component       | Source                              | Service unit            |
|-----------------|-------------------------------------|-------------------------|
| PostgreSQL      | apt (Ubuntu 24.04 default)          | `postgresql.service`    |
| Redis           | apt (Ubuntu 24.04 default)          | `redis-server.service`  |
| AgentLink Backend | `agentlink/backend/` (FastAPI)    | `agentlink.service`     |
| HydraHive2      | separate repo                       | `hydrahive2.service`    |

All four run on the same host. AgentLink listens on `127.0.0.1:8000` by default; HydraHive2 connects via `HH_AGENTLINK_URL=http://127.0.0.1:8000`.

## Install

```bash
sudo bash installer/install.sh
```

Idempotent. Re-run after a `git pull` to update.

Environment overrides:
- `HL_PREFIX` (default `/opt/hydralink`) — install dir
- `HL_USER` (default `hydralink`) — system user that runs the backend
- `HL_BIND_HOST` (default `127.0.0.1`) — bind address (loopback only by default)
- `HL_BACKEND_PORT` (default `8000`) — backend port

## Operate

```bash
systemctl status agentlink         # service state
journalctl -u agentlink -f          # follow logs
sudo systemctl restart agentlink    # restart after update
```

## Layout

```
hydralink/
├── README.md                       ← this file
├── agentlink/                      ← AgentLink code (copied from upstream, modified)
│   ├── backend/                    ← FastAPI + Postgres + Redis Pub/Sub + WebSocket
│   ├── client/                     ← TypeScript client library
│   ├── docker-compose.yml          ← upstream-style dev workflow (alternative to native)
│   └── ...
└── installer/
    ├── install.sh                  ← top-level entry point
    └── modules/
        ├── 00-deps.sh              ← apt install postgresql + redis-server
        ├── 10-postgres.sh          ← create role + db, idempotent
        └── 20-agentlink.sh         ← venv + systemd unit
```

## Upstream

AgentLink upstream: <https://github.com/tilleulenspiegel/agentlink>

We do not submodule or fork — the agentlink code is copied here so HydraLink can adapt it freely. To pull upstream changes, manually merge.

## License

MIT (matches AgentLink upstream + HydraHive2).
