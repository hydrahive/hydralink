# AgentLink TypeScript Client

OpenClaw plugin for AgentLink state protocol integration.

## Installation

```bash
npm install
```

## Development

```bash
npm run dev
```

## Usage

```typescript
import { AgentLinkClient } from '@agentlink/client';

const client = new AgentLinkClient({
  url: 'http://localhost:8000',
  agentId: 'castiel'
});

// Create a state
const state = await client.createState({
  task: {
    type: 'bug_fix',
    description: 'Fix memory leak',
    priority: 4
  },
  context: {
    files: [{ path: 'main.py', lines: [45, 67] }]
  }
});

// Subscribe to updates
client.subscribe((state) => {
  console.log('State update:', state);
});
```

## TODO

- [ ] Client class implementation
- [ ] WebSocket connection handling
- [ ] State serialization/deserialization
- [ ] OpenClaw plugin integration
- [ ] Error handling & retries
- [ ] Type definitions export
