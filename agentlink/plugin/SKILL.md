# AgentLink OpenClaw Plugin

**Agent-to-Agent State Protocol for OpenClaw**

Transfer complete internal states between AI agents with full context preservation.

## What is AgentLink?

AgentLink eliminates lossy natural-language reconstruction by enabling direct state transfer between agents:
- **Working memory** (hypotheses, decisions, findings)
- **Task context** (files, git info, errors)
- **Knowledge references** (A-MEM IDs, QMD refs, URLs)
- **Handoff metadata** (target agent, reason, required skills)

**No more dial-up modem vibes!** 📡→💾

## Prerequisites

- AgentLink backend running (see deployment docs)
- Backend URL configured in `tools/config.json`

## Configuration

Create `tools/config.json`:

```json
{
  "url": "http://YOUR_VM_IP:8000",
  "agentId": "auto"
}
```

- `url`: AgentLink backend API endpoint
- `agentId`: "auto" uses OpenClaw session agent name, or specify manually

## Commands

### Create State

Create a new agent state:

```bash
agentlink create-state \
  --type bug_fix \
  --description "Fixed datetime serialization" \
  --priority 5 \
  --status done \
  --file backend/main.py \
  --git-commit 7ea63a2 \
  --decision "Use model_dump(mode='json')" \
  --reason "Pydantic v2 datetime fix"
```

**Options:**
- `--type`: bug_fix | feature | review | research | refactor
- `--description`: Task description
- `--priority`: 1-5 (5 = highest)
- `--status`: pending | in_progress | blocked | done
- `--file <path>`: Add file to context (repeatable)
- `--git-commit <hash>`: Git commit reference
- `--decision <what>`: Add decision to working memory
- `--reason <why>`: Reason for decision
- `--handoff <agent-id>`: Hand off to another agent

### Get State

Retrieve a state by ID:

```bash
agentlink get-state <state-id>
```

Returns full state as JSON.

### List States

List all states, optionally filtered:

```bash
agentlink list-states
agentlink list-states --agent-id castiel
agentlink list-states --status done
agentlink list-states --limit 10
```

### Create Handoff

Create a handoff to another agent:

```bash
agentlink handoff <agent-id> \
  --reason "Architecture review needed" \
  --skill architecture \
  --skill distributed-systems
```

Uses current session state and hands off to target agent.

### Claim State

Claim a state for exclusive work (prevents concurrent editing):

```bash
agentlink claim <state-id>
agentlink claim <state-id> --duration 60
```

**Options:**
- `--duration <minutes>`: Claim duration (default: 30 minutes)

Returns 409 Conflict if already claimed by another agent.

### Release State

Release a claimed state:

```bash
agentlink release <state-id>
```

Only the claiming agent can release. Returns error if not claimed or claimed by different agent.

### Extend Claim

Extend an existing claim:

```bash
agentlink extend <state-id>
agentlink extend <state-id> --duration 90
```

**Options:**
- `--duration <minutes>`: New claim duration from now (default: 30 minutes)

### Health Check

Check backend health:

```bash
agentlink health
```

## Usage from OpenClaw Sessions

### Example: Bug Fix Handoff

```bash
# Agent fixes bug
agentlink create-state \
  --type bug_fix \
  --description "Fixed PostgreSQL datetime serialization" \
  --priority 5 \
  --status done \
  --file backend/main.py \
  --git-commit abc123 \
  --decision "Use model_dump(mode='json') for Pydantic v2" \
  --reason "Datetime objects not JSON serializable by default" \
  --handoff reviewer

# Reviewer agent later
agentlink list-states --agent-id reviewer
agentlink get-state <state-id>
```

### Example: Research Handoff

```bash
# Research agent creates state
agentlink create-state \
  --type research \
  --description "Evaluate Redis vs Event Sourcing for Phase 3" \
  --priority 4 \
  --status in_progress \
  --decision "Redis Pub/Sub enables real-time handoffs" \
  --decision "Event Sourcing provides full audit trail" \
  --handoff architect

# Architect reviews and decides
agentlink get-state <state-id>
# ... makes decision ...
agentlink create-state \
  --type research \
  --description "Phase 3: Redis first, Event Sourcing later" \
  --priority 5 \
  --status done \
  --handoff implementer
```

### Example: Claim & Collaborate

```bash
# Agent A finds a state to work on
agentlink list-states --status pending

# Claim it to prevent concurrent work
agentlink claim <state-id> --duration 60

# Do the work...
# If taking longer than expected:
agentlink extend <state-id> --duration 90

# When done:
agentlink release <state-id>

# If Agent B tries to claim while A has it:
agentlink claim <state-id>
# ❌ Error: State already claimed by castiel until 2026-02-24 22:30:00
```

**Use claims to prevent:**
- Parallel editing conflicts (like the memory/2026-02-24.md incident!)
- Wasted work when multiple agents pick the same task
- Race conditions in multi-agent workflows

## Integration with Session Memory

AgentLink automatically integrates with OpenClaw session memory:
- Current agent ID from session context
- File paths resolved relative to workspace
- Git info extracted from current repository

## Backend Deployment

See main AgentLink repository:
- https://github.com/tilleulenspiegel/agentlink

## Troubleshooting

### Connection refused

Check backend is running:
```bash
curl http://YOUR_VM_IP:8000/health
```

### Invalid agent ID

Ensure `agentId` in config.json matches your session agent name, or use "auto".

### State not found

Use `list-states` to see available states and their IDs.

## Architecture

```
┌──────────────────┐
│  OpenClaw Agent  │
│   (Your Session) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ AgentLink Plugin │
│  (This Skill)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ TypeScript Client│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  AgentLink API   │
│  (Backend)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   PostgreSQL     │
│  (Persistent)    │
└──────────────────┘
```

## Contributing

See main repository for contribution guidelines.

## License

MIT
