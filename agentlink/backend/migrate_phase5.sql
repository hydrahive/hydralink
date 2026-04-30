-- AgentLink Phase 5 Migration: State Locking & Coordination
-- Adds claimed_by, claimed_at, claim_expires_at columns

-- Add columns (if not exists)
ALTER TABLE agent_states 
ADD COLUMN IF NOT EXISTS claimed_by VARCHAR(255) DEFAULT NULL;

ALTER TABLE agent_states 
ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP DEFAULT NULL;

ALTER TABLE agent_states 
ADD COLUMN IF NOT EXISTS claim_expires_at TIMESTAMP DEFAULT NULL;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_states_claimed_by 
ON agent_states(claimed_by);

CREATE INDEX IF NOT EXISTS idx_states_claim_expires 
ON agent_states(claim_expires_at);

-- Verify
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'agent_states' 
AND column_name IN ('claimed_by', 'claimed_at', 'claim_expires_at')
ORDER BY column_name;
