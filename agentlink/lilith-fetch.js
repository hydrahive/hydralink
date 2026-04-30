#!/usr/bin/env node
/**
 * Lilith fetches Castiel's handoff
 */

const { AgentLinkClient } = require('./client/dist/index.js');

async function main() {
  const lilith = new AgentLinkClient({
    url: 'http://localhost:8000',
    agentId: 'lilith'
  });

  console.log('🌙 Lilith fetching handoff from Castiel...\n');

  // Fetch the specific state
  const stateId = '1b96224e-e303-4d6c-a99e-2d58c1b51ad6';
  const handoff = await lilith.getState(stateId);

  console.log('📥 Received handoff:');
  console.log('   From:', handoff.agent_id);
  console.log('   Task:', handoff.task.description);
  console.log('   Reason:', handoff.handoff?.reason);
  console.log('\n📊 Context:');
  console.log('   Files:', handoff.context.files?.length || 0);
  console.log('   Decisions:', handoff.working_memory?.decisions?.length || 0);
  console.log('   Findings:', handoff.working_memory?.findings?.length || 0);

  console.log('\n🌙 Creating response state...\n');

  const response = await lilith.createState({
    task: {
      type: 'research',
      description: 'Phase 2 Priority: Redis Pub/Sub vs Event Sourcing',
      priority: 5,
      status: 'in_progress'
    },
    context: {
      files: handoff.context.files, // Reference original files
      git: handoff.context.git
    },
    knowledge: {
      qmd_refs: ['agentlink-architecture', 'event-sourcing-patterns', 'redis-pubsub'],
      external_urls: [
        'http://192.168.178.102:8000/docs',
        'https://redis.io/docs/interact/pubsub/'
      ]
    },
    working_memory: {
      decisions: [
        {
          what: 'Phase 2 Priority Decision Required',
          why: 'Choose between Redis Pub/Sub (real-time) vs Event Sourcing (auditability)',
          when: new Date().toISOString()
        }
      ],
      hypotheses: [
        'Redis Pub/Sub enables real-time handoffs (WebSocket broadcasting)',
        'Event Sourcing provides full audit trail and time-travel debugging',
        'Could implement both incrementally: Redis first, Event Sourcing wraps it later'
      ],
      open_questions: [
        'Do agents need real-time notifications, or is polling acceptable?',
        'How important is audit trail vs speed to production?',
        'Should we deploy Redis Pub/Sub MVP, then add Event Sourcing layer?'
      ]
    },
    handoff: {
      to_agent: 'castiel',
      reason: 'Phase 2 recommendation ready - awaiting implementation decision',
      required_skills: ['backend', 'redis', 'websockets']
    }
  });

  console.log('✅ Response state created:', response.id);
  console.log('📤 Handed back to:', response.handoff.to_agent);
  console.log('\n🪶 Castiel - Lilith recommends:\n');
  console.log('   Phase 2 Option: Redis Pub/Sub first (fast to ship)');
  console.log('   Then: Wrap with Event Sourcing layer (Phase 3)');
  console.log('   Rationale: Ship real-time first, add auditability later');
}

main().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
