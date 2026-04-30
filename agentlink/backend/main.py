"""
AgentLink - Agent State Protocol
FastAPI Backend with Redis Pub/Sub
"""
from fastapi import FastAPI, WebSocket, HTTPException, Depends, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Set
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
import uvicorn
import asyncio
import json
import logging
import os
import re
from redis.asyncio import Redis

from database import get_db, init_db, AgentStateDB

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client: Optional[Redis] = None
pubsub = None

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "all": set(),  # Clients subscribed to all states
        }
    
    async def connect(self, websocket: WebSocket, channel: str = "all"):
        """Accept WebSocket connection and subscribe to channel"""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        logger.info(f"Client connected to channel: {channel}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket from all subscriptions"""
        for channel_set in self.active_connections.values():
            if websocket in channel_set:
                channel_set.discard(websocket)
        logger.info("Client disconnected")
    
    async def broadcast(self, message: dict, channel: str = "all"):
        """Broadcast message to all clients subscribed to channel"""
        message_json = json.dumps(message)
        
        # Snapshot connections to avoid set modification during iteration
        clients = list(self.active_connections.get(channel, set()))
        dead_connections = []
        
        for ws in clients:
            try:
                await ws.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to {channel}: {e}")
                dead_connections.append(ws)
        
        # Cleanup dead connections after iteration
        for ws in dead_connections:
            self.disconnect(ws)

manager = ConnectionManager()

app = FastAPI(
    title="AgentLink API",
    description="Agent-to-Agent State Protocol with Redis Pub/Sub",
    version="0.3.1"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REDIS PUB/SUB
# ============================================================================

async def redis_listener():
    """Background task listening to Redis Pub/Sub with exponential backoff"""
    global redis_client, pubsub
    
    retry_delay = 1
    max_delay = 32
    
    while True:  # Retry loop inside task to avoid spawning multiple tasks
        try:
            redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
            pubsub = redis_client.pubsub()
            
            # Subscribe to all agentlink channels using pattern
            await pubsub.psubscribe("agentlink:*")
            logger.info("Redis listener started - subscribed to agentlink:*")
            
            retry_delay = 1  # Reset delay on successful connection
            
            async for message in pubsub.listen():
                # Handle both direct messages and pattern messages
                if message["type"] in ["message", "pmessage"]:
                    try:
                        data = json.loads(message["data"])
                        
                        # Broadcast to "all" channel
                        await manager.broadcast(data, channel="all")
                        
                        # Only broadcast to agent channel if it's a handoff
                        if data.get("type") == "handoff_received" and "to_agent" in data:
                            agent_channel = f"agent:{data['to_agent']}"
                            await manager.broadcast(data, channel=agent_channel)
                        
                        logger.info(f"Broadcasted message: {data.get('type', 'unknown')}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON from Redis: {e}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            logger.info(f"Reconnecting in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)  # Exponential backoff
        
        finally:
            # Cleanup connections
            if pubsub:
                try:
                    await pubsub.close()
                except Exception as e:
                    logger.error(f"Error closing pubsub: {e}")
            if redis_client:
                try:
                    await redis_client.close()
                except Exception as e:
                    logger.error(f"Error closing redis client: {e}")


async def publish_to_redis(channel: str, message: dict):
    """Publish message to Redis channel"""
    global redis_client
    
    if not redis_client:
        logger.warning("Redis client not initialized - skipping publish")
        return
    
    try:
        message_json = json.dumps(message)
        await redis_client.publish(channel, message_json)
        logger.info(f"Published to {channel}: {message.get('type', 'unknown')}")
    except Exception as e:
        logger.error(f"Error publishing to Redis: {e}")


# ============================================================================
# ============================================================================
# PHASE 5.1: AUTO-TIMEOUT BACKGROUND TASK
# ============================================================================

async def auto_timeout_task():
    """
    Background task that runs every 60 seconds.
    Releases expired claims automatically.
    """
    while True:
        try:
            await asyncio.sleep(60)  # Run every 60 seconds
            
            # Get DB session
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # Find expired claims
                now = datetime.utcnow()
                expired_states = db.query(AgentStateDB).filter(
                    AgentStateDB.claimed_by.isnot(None),
                    AgentStateDB.claim_expires_at < now
                ).all()
                
                if expired_states:
                    logger.info(f"Found {len(expired_states)} expired claims, releasing...")
                    
                    for db_state in expired_states:
                        # Log who had it
                        old_owner = db_state.claimed_by
                        state_id = db_state.id
                        
                        # Release claim
                        db_state.claimed_by = None
                        db_state.claimed_at = None
                        db_state.claim_expires_at = None
                        
                        # Broadcast event
                        await publish_to_redis("agentlink:events", {
                            "type": "state.claim.timeout",
                            "state_id": state_id,
                            "previous_owner": old_owner,
                            "released_at": now.isoformat()
                        })
                        
                        logger.info(f"Auto-released claim on {state_id[:8]}... (was: {old_owner})")
                    
                    db.commit()
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in auto_timeout_task: {e}")
            # Continue running even after errors


# SCHEMA - Agent State v1
# ============================================================================

class FileContext(BaseModel):
    path: str
    diff: Optional[str] = None
    lines: Optional[tuple[int, int]] = None
    hash: Optional[str] = None  # git blob hash


class GitContext(BaseModel):
    repo: str
    branch: str
    commit: str


class ErrorContext(BaseModel):
    type: str
    message: str
    stack: Optional[str] = None


class Context(BaseModel):
    files: List[FileContext] = []
    git: Optional[GitContext] = None
    errors: List[ErrorContext] = []


class Knowledge(BaseModel):
    amem_ids: List[str] = []
    qmd_refs: List[str] = []
    external_urls: List[str] = []


class Decision(BaseModel):
    what: str
    why: str
    when: datetime


class WorkingMemory(BaseModel):
    hypotheses: List[str] = []
    open_questions: List[str] = []
    decisions: List[Decision] = []
    findings: List[str] = []


class Task(BaseModel):
    type: Literal["bug_fix", "feature", "review", "research", "refactor"]
    description: str
    priority: int = Field(ge=1, le=5)
    status: Literal["pending", "in_progress", "blocked", "done"] = "pending"


class Handoff(BaseModel):
    to_agent: Optional[str] = None
    reason: Optional[str] = None
    required_skills: List[str] = []


class AgentState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task: Task
    context: Context
    knowledge: Knowledge = Knowledge()
    working_memory: WorkingMemory = WorkingMemory()
    handoff: Optional[Handoff] = None


# ============================================================================
# PHASE 5: CLAIM/RELEASE MODELS
# ============================================================================

class ClaimRequest(BaseModel):
    """Request to claim a state"""
    agent_id: str
    duration_minutes: Optional[int] = 30  # Default 30min

class ClaimResponse(BaseModel):
    """Response after claiming a state"""
    state_id: str
    claimed_by: str
    claimed_at: datetime
    expires_at: datetime



# ============================================================================
# DATABASE HELPERS
# ============================================================================

def pydantic_to_db(state: AgentState) -> AgentStateDB:
    """Convert Pydantic model to SQLAlchemy model"""
    return AgentStateDB(
        id=state.id,
        agent_id=state.agent_id,
        timestamp=state.timestamp,
        task=state.task.model_dump(mode="json"),
        context=state.context.model_dump(mode="json"),
        knowledge=state.knowledge.model_dump(mode="json"),
        working_memory=state.working_memory.model_dump(mode="json"),
        handoff=state.handoff.model_dump(mode="json") if state.handoff else None
    )


def db_to_pydantic(db_state: AgentStateDB) -> AgentState:
    """Convert SQLAlchemy model to Pydantic model"""
    return AgentState(
        id=db_state.id,
        agent_id=db_state.agent_id,
        timestamp=db_state.timestamp,
        task=Task(**db_state.task),
        context=Context(**db_state.context),
        knowledge=Knowledge(**db_state.knowledge),
        working_memory=WorkingMemory(**db_state.working_memory),
        handoff=Handoff(**db_state.handoff) if db_state.handoff else None
    )


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and Redis listener on startup"""
    init_db()
    asyncio.create_task(redis_listener())
    asyncio.create_task(auto_timeout_task())
    logger.info("AgentLink backend started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup Redis connections on shutdown"""
    global redis_client, pubsub
    
    if pubsub:
        try:
            await pubsub.close()
        except Exception as e:
            logger.error(f"Error closing pubsub on shutdown: {e}")
    if redis_client:
        try:
            await redis_client.close()
        except Exception as e:
            logger.error(f"Error closing redis client on shutdown: {e}")
    logger.info("AgentLink backend shutdown")


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": "AgentLink",
        "version": "0.3.1",
        "status": "online",
        "features": ["PostgreSQL", "Redis Pub/Sub", "WebSocket"],
        "endpoints": {
            "health": "/health",
            "states": "/states",
            "websocket": "/ws"
        }
    }


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    """Health check with state count and Redis status"""
    count = db.query(AgentStateDB).count()
    
    redis_status = "disconnected"
    if redis_client:
        try:
            await redis_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "error"
    
    return {
        "status": "healthy",
        "states_count": count,
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/states", response_model=AgentState)
async def create_state(state: AgentState, db: Session = Depends(get_db)):
    """Store a new agent state and broadcast via Redis"""
    # Save to PostgreSQL
    db_state = pydantic_to_db(state)
    db.add(db_state)
    db.commit()
    db.refresh(db_state)
    
    # Broadcast via Redis Pub/Sub
    event_message = {
        "type": "state_created",
        "state_id": state.id,
        "from_agent": state.agent_id,
        "timestamp": state.timestamp.isoformat(),
        "task_type": state.task.type,
        "task_status": state.task.status,
    }
    
    await publish_to_redis("agentlink:states", event_message)
    
    # If handoff, also publish to target agent channel
    if state.handoff and state.handoff.to_agent:
        handoff_message = {
            "type": "handoff_received",
            "state_id": state.id,
            "from_agent": state.agent_id,
            "to_agent": state.handoff.to_agent,
            "reason": state.handoff.reason,
            "timestamp": state.timestamp.isoformat(),
        }
        await publish_to_redis(f"agentlink:agent:{state.handoff.to_agent}", handoff_message)
        logger.info(f"Handoff published to agent:{state.handoff.to_agent}")
        # Also insert into handoffs table for Matrix notifier
        try:
            from sqlalchemy import text as sa_text
            db.execute(sa_text("INSERT INTO handoffs (source_agent, target_agent, task, context, status) VALUES (:source, :target, :task, cast(:context as jsonb), 'pending')"), {
                "source": state.agent_id,
                "target": state.handoff.to_agent,
                "task": state.task.description,
                "context": json.dumps({"reason": state.handoff.reason, "state_id": str(state.id)})
            })
            db.commit()
            logger.info(f"Inserted into handoffs table for {state.handoff.to_agent}")
        except Exception as e:
            logger.error(f"Failed to insert into handoffs table: {e}")
    
    return db_to_pydantic(db_state)


@app.get("/states/{state_id}", response_model=AgentState)
async def get_state(state_id: str, db: Session = Depends(get_db)):
    """Retrieve an agent state by ID from PostgreSQL"""
    db_state = db.query(AgentStateDB).filter(AgentStateDB.id == state_id).first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    return db_to_pydantic(db_state)


@app.get("/states", response_model=List[AgentState])
async def list_states(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List states with optional filters from PostgreSQL"""
    query = db.query(AgentStateDB)
    
    if agent_id:
        query = query.filter(AgentStateDB.agent_id == agent_id)
    
    results = query.order_by(AgentStateDB.timestamp.desc()).limit(limit).all()
    return [db_to_pydantic(s) for s in results]


@app.delete('/states/{state_id}')
async def delete_state(state_id: str, db: Session = Depends(get_db)):
    """Delete an agent state by ID"""
    db_state = db.query(AgentStateDB).filter(AgentStateDB.id == state_id).first()
    if not db_state:
        raise HTTPException(status_code=404, detail='State not found')
    db.delete(db_state)
    db.commit()
    return {'deleted': state_id}


# ============================================================================
# ANALYTICS & STATS ENDPOINTS
# ============================================================================

# ============================================================================
# PHASE 5: STATE LOCKING & COORDINATION
# ============================================================================

from datetime import timedelta

@app.post("/api/states/{state_id}/claim", response_model=ClaimResponse)
async def claim_state(
    state_id: str, 
    request: ClaimRequest,
    db: Session = Depends(get_db)
):
    """
    Claim a state for exclusive work.
    Returns 409 Conflict if already claimed by another agent.
    """
    # Get state
    db_state = db.query(AgentStateDB).filter(AgentStateDB.id == state_id).first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Check if already claimed
    now = datetime.utcnow()
    if db_state.claimed_by and db_state.claim_expires_at:
        if db_state.claim_expires_at > now:
            # Still claimed by someone
            if db_state.claimed_by != request.agent_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"State already claimed by {db_state.claimed_by} until {db_state.claim_expires_at}"
                )
    
    # Claim it!
    db_state.claimed_by = request.agent_id
    db_state.claimed_at = now
    db_state.claim_expires_at = now + timedelta(minutes=request.duration_minutes)
    
    db.commit()
    db.refresh(db_state)
    
    # Broadcast WebSocket event
    await publish_to_redis("agentlink:events", {
        "type": "state.claim.acquired",
        "state_id": state_id,
        "claimed_by": request.agent_id,
        "claimed_at": db_state.claimed_at.isoformat(),
        "expires_at": db_state.claim_expires_at.isoformat()
    })
    
    return ClaimResponse(
        state_id=state_id,
        claimed_by=db_state.claimed_by,
        claimed_at=db_state.claimed_at,
        expires_at=db_state.claim_expires_at
    )


@app.post("/api/states/{state_id}/release")
async def release_state(
    state_id: str,
    agent_id: str,  # Query parameter
    db: Session = Depends(get_db)
):
    """
    Release a claimed state.
    Only the claiming agent can release it.
    """
    db_state = db.query(AgentStateDB).filter(AgentStateDB.id == state_id).first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Check if claimed
    if not db_state.claimed_by:
        return {"message": "State was not claimed", "state_id": state_id}
    
    # Check if caller is the claimer
    if db_state.claimed_by != agent_id:
        raise HTTPException(
            status_code=403,
            detail=f"Only {db_state.claimed_by} can release this state"
        )
    
    # Release it
    db_state.claimed_by = None
    db_state.claimed_at = None
    db_state.claim_expires_at = None
    
    db.commit()
    
    # Broadcast WebSocket event
    await publish_to_redis("agentlink:events", {
        "type": "state.claim.released",
        "state_id": state_id,
        "released_by": agent_id
    })
    
    return {"message": "State released", "state_id": state_id}


@app.post("/api/states/{state_id}/extend", response_model=ClaimResponse)
async def extend_claim(
    state_id: str,
    request: ClaimRequest,
    db: Session = Depends(get_db)
):
    """
    Extend an existing claim.
    Only the claiming agent can extend it.
    """
    db_state = db.query(AgentStateDB).filter(AgentStateDB.id == state_id).first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Check if claimed by requester
    if db_state.claimed_by != request.agent_id:
        raise HTTPException(
            status_code=403,
            detail=f"State is claimed by {db_state.claimed_by or 'no one'}, not {request.agent_id}"
        )
    
    # Extend the claim
    now = datetime.utcnow()
    db_state.claim_expires_at = now + timedelta(minutes=request.duration_minutes)
    
    db.commit()
    db.refresh(db_state)
    
    # Broadcast WebSocket event
    await publish_to_redis("agentlink:events", {
        "type": "state.claim.extended",
        "state_id": state_id,
        "claimed_by": request.agent_id,
        "new_expires_at": db_state.claim_expires_at.isoformat()
    })
    
    return ClaimResponse(
        state_id=state_id,
        claimed_by=db_state.claimed_by,
        claimed_at=db_state.claimed_at,
        expires_at=db_state.claim_expires_at
    )


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get aggregated statistics"""
    from sqlalchemy import func, distinct
    
    # Total states
    total_states = db.query(func.count(AgentStateDB.id)).scalar() or 0
    
    # Total unique agents
    unique_agents = db.query(func.count(distinct(AgentStateDB.agent_id))).scalar() or 0
    
    # States with handoffs
    total_handoffs = db.query(func.count(AgentStateDB.id)).filter(
        AgentStateDB.handoff.isnot(None)
    ).scalar() or 0
    
    # States by task type
    task_types = {}
    for task_type in ["bug_fix", "feature", "review", "research", "refactor"]:
        count = db.query(func.count(AgentStateDB.id)).filter(
            AgentStateDB.task.op('->>')('type') == task_type
        ).scalar() or 0
        task_types[task_type] = count
    
    # States by status
    statuses = {}
    for status in ["pending", "in_progress", "blocked", "done"]:
        count = db.query(func.count(AgentStateDB.id)).filter(
            AgentStateDB.task.op('->>')('status') == status
        ).scalar() or 0
        statuses[status] = count
    
    # Currently active WebSocket connections
    active_ws_connections = sum(len(conns) for conns in manager.active_connections.values())
    
    return {
        "total_states": total_states,
        "unique_agents": unique_agents,
        "total_handoffs": total_handoffs,
        "task_types": task_types,
        "statuses": statuses,
        "active_ws_connections": active_ws_connections,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/analytics")
async def get_analytics(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get time-series analytics data"""
    from sqlalchemy import func
    from datetime import timedelta
    
    # Calculate time window
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # States created over time (grouped by hour)
    states_over_time = db.query(
        func.date_trunc('hour', AgentStateDB.timestamp).label('hour'),
        func.count(AgentStateDB.id).label('count')
    ).filter(
        AgentStateDB.timestamp >= since
    ).group_by('hour').order_by('hour').all()
    
    # Handoffs over time
    handoffs_over_time = db.query(
        func.date_trunc('hour', AgentStateDB.timestamp).label('hour'),
        func.count(AgentStateDB.id).label('count')
    ).filter(
        AgentStateDB.timestamp >= since,
        AgentStateDB.handoff.isnot(None)
    ).group_by('hour').order_by('hour').all()
    
    # Activity by agent
    activity_by_agent = db.query(
        AgentStateDB.agent_id,
        func.count(AgentStateDB.id).label('count')
    ).filter(
        AgentStateDB.timestamp >= since
    ).group_by(AgentStateDB.agent_id).all()
    
    return {
        "time_window_hours": hours,
        "since": since.isoformat(),
        "states_over_time": [
            {"hour": row.hour.isoformat(), "count": row.count}
            for row in states_over_time
        ],
        "handoffs_over_time": [
            {"hour": row.hour.isoformat(), "count": row.count}
            for row in handoffs_over_time
        ],
        "activity_by_agent": [
            {"agent_id": row.agent_id, "count": row.count}
            for row in activity_by_agent
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/agents/active")
async def get_active_agents():
    """Get list of currently connected agents via WebSocket"""
    # Extract agent IDs from active channels
    active_agents = []
    
    for channel, connections in manager.active_connections.items():
        if channel.startswith("agent:") and len(connections) > 0:
            agent_id = channel.split(":", 1)[1]
            active_agents.append({
                "agent_id": agent_id,
                "connections": len(connections),
                "channel": channel
            })
    
    # Also check total broadcast listeners
    all_connections = len(manager.active_connections.get("all", set()))
    
    return {
        "active_agents": active_agents,
        "total_broadcast_listeners": all_connections,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# WEBSOCKET - Real-time Updates
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time state updates"""
    # Accept connection and register with ConnectionManager
    await manager.connect(websocket, channel="all")
    current_channel = "all"
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "channel": current_channel,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            # Receive subscription commands from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    new_channel = message.get("channel", "all")
                    
                    # Validate channel
                    if new_channel == "all":
                        # OK
                        pass
                    elif new_channel.startswith("agent:"):
                        agent_id = new_channel.split(":", 1)[1]
                        # Validate agent_id (alphanumeric + underscore/dash)
                        if not re.match(r'^[a-zA-Z0-9_-]+$', agent_id):
                            await websocket.send_json({
                                "type": "error",
                                "message": "Invalid agent_id format"
                            })
                            continue
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Unknown channel type (use 'all' or 'agent:ID')"
                        })
                        continue
                    
                    # Unsubscribe from current channel
                    if current_channel in manager.active_connections:
                        manager.active_connections[current_channel].discard(websocket)
                    
                    # Subscribe to new channel
                    current_channel = new_channel
                    if current_channel not in manager.active_connections:
                        manager.active_connections[current_channel] = set()
                    manager.active_connections[current_channel].add(websocket)
                    
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": current_channel,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif action == "unsubscribe":
                    manager.disconnect(websocket)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    break
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected from channel: {current_channel}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
