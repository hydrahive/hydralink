# AgentLink

**Agent-to-Agent State Protocol** - Direct state transfer between AI agents, eliminating lossy natural-language reconstruction.

## 🎯 What is AgentLink?

AgentLink enables AI agents to transfer complete internal states with full context preservation:
- **Working memory** (hypotheses, decisions, findings)
- **Task context** (files, git info, errors)
- **Knowledge references** (A-MEM IDs, QMD refs, external URLs)
- **Handoff metadata** (target agent, reasoning, required skills)

**No more dial-up modem vibes!** 📡→💾

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for TypeScript client)

### Deploy Backend

```bash
cd agentlink
docker compose up -d
```

Services:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- ChromaDB: localhost:8001

### Install TypeScript Client

```bash
cd client
npm install
npm run build
```

### Basic Usage

```typescript
import { AgentLinkClient } from '@agentlink/client';

const client = new AgentLinkClient({
  url: 'http://localhost:8000',
  agentId: 'my-agent'
});

// Create a state
const state = await client.createState({
  task: {
    type: 'bug_fix',
    description: 'Fix datetime serialization',
    priority: 5,
    status: 'done'
  },
  context: {
    files: [{ path: 'backend/main.py', diff: 'Fixed model_dump' }],
    git: { repo: 'agentlink', branch: 'main', commit: 'abc123' }
  },
  working_memory: {
    decisions: [{
      what: 'Use model_dump(mode="json")',
      why: 'Pydantic v2 datetime serialization',
      when: new Date().toISOString()
    }]
  },
  handoff: {
    to_agent: 'reviewer',
    reason: 'Code review needed',
    required_skills: ['python', 'fastapi']
  }
});

// Get a state
const retrieved = await client.getState(state.id);

// List states
const states = await client.listStates({ agent_id: 'my-agent' });
```

## 📊 Architecture

```
┌─────────────┐
│   Agents    │
│ (Castiel,   │
│  Lilith,    │
│  David...)  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ TypeScript      │
│ Client Library  │
│ - REST API      │
│ - WebSocket     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FastAPI Backend │
│ - State CRUD    │
│ - Validation    │
└────────┬────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    ▼         ▼         ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌─────────┐
│ Postgre│Chrome│ Redis│ │(Future) │
│  SQL   │  DB  │PubSub│ │EventSrc │
└────────┘ └──────┘ └──────┘ └─────────┘
```

## 🎯 Current Status

**Phase 1 - MVP ✅ COMPLETE**
- [x] Backend (FastAPI + PostgreSQL)
- [x] TypeScript Client (REST + WebSocket stub)
- [x] Real handoff validated (Castiel ↔ Lilith)
- [x] Docker deployment
- [x] Schema versioning

**Phase 2 - OpenClaw Plugin** 🔌 (Next)
- [ ] OpenClaw plugin wrapper
- [ ] CLI integration
- [ ] Session memory integration

**Phase 3 - Real-time & Event Sourcing** (Future)
- [ ] Redis Pub/Sub for WebSocket broadcasting
- [ ] Event Sourcing layer for audit trails
- [ ] ChromaDB semantic search
- [ ] Blockchain/IPFS hybrid storage

## 📖 Documentation

- [Deployment Guide](./DEPLOYMENT.md)
- [First Handoff Test](./HANDOFF-TEST.md)
- [API Reference](http://localhost:8000/docs) (when running)
- [Client API](./client/README.md)

## 🧪 Validation

**First successful agent-to-agent handoff:**
- Castiel (Linux VM, TypeScript) → Lilith (Windows, curl)
- Full state transfer with context preservation
- Round-trip validated ✅

See [HANDOFF-TEST.md](./HANDOFF-TEST.md) for details.

## 🛠️ Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Client
cd client
npm install
npm run build
npm run dev  # watch mode
```

## 📝 State Schema

See [backend/main.py](./backend/main.py) for full schema definitions.

Key fields:
- `agent_id`: Agent identifier
- `task`: Task type, description, priority, status
- `context`: Files, git info, errors
- `knowledge`: A-MEM IDs, QMD refs, URLs
- `working_memory`: Hypotheses, decisions, findings
- `handoff`: Target agent, reason, required skills

## 🚀 Roadmap

1. **OpenClaw Plugin** - Make it usable from live sessions
2. **Real-time Updates** - Redis Pub/Sub + WebSocket
3. **Event Sourcing** - Full audit trail
4. **Semantic Search** - ChromaDB integration
5. **Blockchain Layer** - Immutable state history

## 📜 License

MIT

## 🤝 Contributors

- Castiel 🪶 - Backend, Client, Infrastructure
- Lilith 🌙 - Architecture, Protocol Design
- Till - Product Vision

---

**Built with ❤️ by AI agents, for AI agents.**
