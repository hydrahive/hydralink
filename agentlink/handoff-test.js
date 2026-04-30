#!/usr/bin/env node
/**
 * AgentLink Handoff Test: Castiel → Lilith
 */

const { AgentLinkClient } = require('./client/dist/index.js');

async function main() {
  const castiel = new AgentLinkClient({
    url: 'http://localhost:8000',
    agentId: 'castiel'
  });

  console.log('🪶 Castiel creating state with handoff to Lilith...\n');

  const state = await castiel.createState({
    task: {
      type: 'review',
      description: 'TypeScript client deployment - architecture review and Phase 2 planning',
      priority: 5,
      status: 'done'
    },
    context: {
      files: [
        { path: 'client/src/index.ts', hash: '7ea63a2' },
        { path: 'client/src/types.ts', hash: '7ea63a2' },
        { path: 'backend/main.py', diff: 'Fixed datetime serialization' }
      ],
      git: {
        repo: 'http://192.168.178.203:3000/claude/agentlink',
        branch: 'main',
        commit: '7ea63a2'
      }
    },
    knowledge: {
      qmd_refs: ['agentlink-backend-complete', 'typescript-client-tested'],
      external_urls: ['http://192.168.178.102:8000/docs']
    },
    working_memory: {
      decisions: [
        {
          what: 'Built TypeScript client with REST + WebSocket',
          why: 'Enable agent-to-agent state transfer',
          when: new Date().toISOString()
        },
        {
          what: 'Fixed backend datetime serialization bug',
          why: 'model_dump(mode=json) required for Pydantic v2',
          when: new Date().toISOString()
        }
      ],
      findings: [
        'All REST endpoints working',
        'Exponential backoff reconnection tested',
        'Type system complete and validated',
        '2 states in database (test + example)'
      ]
    },
    handoff: {
      to_agent: 'lilith',
      reason: 'Architecture review complete, need Phase 2 priority decision',
      required_skills: ['architecture', 'distributed-systems', 'protocol-design']
    }
  });

  console.log('✅ State created:', state.id);
  console.log('📤 Handed off to:', state.handoff.to_agent);
  console.log('\n🌙 Lilith - your turn! Fetch this state and respond:\n');
  console.log();
  console.log('   Agent: castiel');
  console.log('   Task: Architecture review and Phase 2 planning');
}

main().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
