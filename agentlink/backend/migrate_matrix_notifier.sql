-- Add notified_at column to handoffs table for Matrix notifier tracking
ALTER TABLE handoffs 
ADD COLUMN IF NOT EXISTS notified_at TIMESTAMP DEFAULT NULL;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_handoffs_notified 
ON handoffs(id, status, notified_at);

-- Comment
COMMENT ON COLUMN handoffs.notified_at IS 'Timestamp when Matrix notification was sent';
