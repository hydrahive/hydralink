#!/usr/bin/env node
/**
 * AgentLink Client Example
 * 
 * Run: node example.js
 */

const { AgentLinkClient } = require('./dist/index.js');

async function main() {
  // Initialize client
  const client = new AgentLinkClient({
    url: 'http://localhost:8000',
    agentId: 'example-agent'
  });

  try {
    // Health check
    console.log('\n=== Health Check ===');
    const health = await client.health();
    console.log('Status:', health.status);
    console.log('States Count:', health.states_count);

    // Create a state
    console.log('\n=== Creating State ===');
    const newState = await client.createState({
      task: {
        type: 'feature',
        description: 'Test AgentLink TypeScript client',
        priority: 5,
        status: 'done'
      },
      context: {
        files: [{
          path: 'client/example.js'
        }]
      },
      working_memory: {
        decisions: [{
          what: 'Built TypeScript client',
          why: 'Enable agent-to-agent communication',
          when: new Date().toISOString()
        }]
      }
    });
    console.log('Created State ID:', newState.id);

    // Get the state back
    console.log('\n=== Retrieving State ===');
    const retrieved = await client.getState(newState.id);
    console.log('Retrieved:', retrieved.agent_id, '/', retrieved.task.description);

    // List all states
    console.log('\n=== Listing States ===');
    const states = await client.listStates();
    console.log('Total States:', states.length);
    states.forEach(s => {
      console.log(' -', s.id, ':', s.task.description);
    });

    // WebSocket example (commented out - backend needs Redis Pub/Sub first)
    // console.log('\n=== WebSocket Connection ===');
    // client.connect((state) => {
    //   console.log('State Update:', state.id, state.task.description);
    // });

    console.log('\n✅ All tests passed!');
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();
