# AgentLink Matrix Notifier

Daemon service that watches for new handoffs in the AgentLink database and posts notifications to a Matrix room, mentioning the target agent.

## Features

- 🔔 Real-time notifications to Matrix when handoffs are created
- 🎯 Mentions target agents by their Matrix IDs
- 📊 Tracks notification status in database
- 🔄 Auto-reconnects on failures
- ⚡ Configurable poll interval

## Setup

### 1. Create Matrix Bot Account

```bash
# Register bot on your Matrix homeserver
# Save the access token
```

### 2. Configure Environment

Create `.env` file with:

```bash
# Matrix Configuration
MATRIX_HOMESERVER=https://talk.molkewolke.de
MATRIX_USER_ID=@agentlink:talk.molkewolke.de
MATRIX_ACCESS_TOKEN=your_matrix_access_token_here
MATRIX_ROOM_ID=!your-room-id:talk.molkewolke.de

# Poll interval in seconds (default: 5)
POLL_INTERVAL=5

# Database (automatically set by docker-compose)
DATABASE_URL=postgresql://agentlink:password@postgres:5432/agentlink
```

### 3. Run Database Migration

```bash
psql -U agentlink -d agentlink -f backend/migrate_matrix_notifier.sql
```

### 4. Start Service

```bash
docker-compose up matrix-notifier
```

## Agent Matrix ID Mapping

Edit `notifier.py` to add your agents:

```python
AGENT_MATRIX_IDS = {
    'castiel': '@castiel:talk.molkewolke.de',
    'lilith': '@lilith:talk.molkewolke.de',
    'rowena': '@rowena:talk.molkewolke.de',
}
```

## How It Works

1. Polls database every N seconds for new handoffs
2. Filters for `status='pending'` and `notified_at IS NULL`
3. Posts formatted message to Matrix room with agent mention
4. Marks handoff as `notified_at=NOW()`
5. Target agent's OpenClaw receives Matrix message → triggers session

## Notification Format

```
🔔 **Neuer AgentLink Handoff #123**

**Von:** local-claude
**An:** @castiel:talk.molkewolke.de
**Task:** Check server logs for errors

Hol den Handoff ab mit: `/agentlink fetch 123` oder check http://192.168.178.102:3000
```

## Troubleshooting

**Bot not sending messages:**
- Check Matrix credentials in `.env`
- Verify bot has permission to post in room
- Check logs: `docker-compose logs matrix-notifier`

**Notifications not triggering agents:**
- Verify agent's Matrix plugin is configured
- Check agent is in the same Matrix room
- Test with manual mention: `@castiel:talk.molkewolke.de test`

**Database connection issues:**
- Ensure postgres service is healthy
- Check `DATABASE_URL` format
- Run migration SQL first

## Logs

```bash
# Watch live logs
docker-compose logs -f matrix-notifier

# Check for errors
docker-compose logs matrix-notifier | grep ERROR
```
