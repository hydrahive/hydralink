# AgentLink API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

**Phase 1:** None (localhost only)  
**Phase 2:** Shared secret header: `X-AgentLink-Secret: <secret>`  
**Phase 3:** JWT tokens via OAuth

## Endpoints

### Health Check

**GET** `/health`

Response:
```json
{
  "status": "healthy",
  "states_count": 42,
  "timestamp": "2026-02-22T14:30:00Z"
}
```

### Create State

**POST** `/states`

Request body:
```json
{
  "agent_id": "castiel",
  "task": {
    "type": "bug_fix",
    "description": "Fix memory leak in WebSocket handler",
    "priority": 4
  },
  "context": {
    "files": [{
      "path": "backend/websocket.py",
      "lines": [45, 67]
    }],
    "errors": [{
      "type": "MemoryError",
      "message": "WebSocket connections not closing",
      "stack": "..."
    }]
  }
}
```

Response: Full `AgentState` object with generated `id` and `timestamp`

### Get State

**GET** `/states/{state_id}`

Response: `AgentState` object

### List States

**GET** `/states?agent_id=castiel&status=in_progress&limit=10`

Query params:
- `agent_id` (optional) - Filter by agent
- `status` (optional) - Filter by task status
- `limit` (default: 100) - Max results

Response: Array of `AgentState` objects

### WebSocket

**WS** `/ws`

Real-time state updates and subscriptions.

**Subscribe to agent's states:**
```json
{
  "action": "subscribe",
  "agent_id": "castiel"
}
```

**Broadcast state update:**
```json
{
  "action": "broadcast",
  "state": { ... }
}
```

## State Schema

See [README.md](../README.md#agent-state-schema-v1) for full schema documentation.

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message"
}
```

HTTP Status Codes:
- `400` - Bad Request (invalid state schema)
- `404` - State not found
- `500` - Internal server error
