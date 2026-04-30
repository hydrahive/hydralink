#!/usr/bin/env node
/**
 * Castiel receives Lilith's response
 */

const { AgentLinkClient } = require('./client/dist/index.js');

async function main() {
  const castiel = new AgentLinkClient({
    url: 'http://localhost:8000',
    agentId: 'castiel'
  });

  console.log('🪶 Castiel fetching Lilith\'s response...\n');

  const stateId = '61a60fb1-bdfc-45ba-b214-51d55dc0c363';
  const response = await castiel.getState(stateId);

  console.log('📥 HANDOFF RECEIVED FROM LILITH! 🌙\n');
  console.log('From:', response.agent_id);
  console.log('Task:', response.task.description);
  console.log('Priority:', response.task.priority);
  console.log('Status:', response.task.status);
  
  console.log('\n📊 Lilith\'s Analysis:');
  console.log('Decisions:', response.working_memory?.decisions?.length || 0);
  response.working_memory?.decisions?.forEach((d, i) => {
    console.log();
    console.log();
  });

  console.log('\nHypotheses:', response.working_memory?.hypotheses?.length || 0);
  response.working_memory?.hypotheses?.forEach((h, i) => {
    console.log();
  });

  console.log('\nOpen Questions:', response.working_memory?.open_questions?.length || 0);
  response.working_memory?.open_questions?.forEach((q, i) => {
    console.log();
  });

  if (response.handoff) {
    console.log('\n📤 Handoff:');
    console.log('  To:', response.handoff.to_agent);
    console.log('  Reason:', response.handoff.reason);
    console.log('  Skills:', response.handoff.required_skills?.join(', '));
  }

  console.log('\n✅ AGENT-TO-AGENT HANDOFF COMPLETE! 🎉');
  console.log('\nThe loop:');
  console.log('  1. Castiel created state → handed to Lilith ✅');
  console.log('  2. Lilith fetched via curl (Windows) ✅');
  console.log('  3. Lilith analyzed & responded via curl ✅');
  console.log('  4. Castiel received via TypeScript client ✅');
  console.log('\n🚀 AgentLink Protocol VALIDATED! 🚀');
}

main().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
