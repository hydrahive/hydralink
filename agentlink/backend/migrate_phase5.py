"""
Migration script for Phase 5: State Locking & Coordination
Adds claimed_by, claimed_at, claim_expires_at columns to agent_states table
"""
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agentlink:agentlink_dev@localhost:5432/agentlink")

# Parse DATABASE_URL
# postgresql://user:password@host:port/dbname
parts = DATABASE_URL.replace("postgresql://", "").split("@")
user_pass = parts[0].split(":")
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")

conn_params = {
    "user": user_pass[0],
    "password": user_pass[1],
    "host": host_port[0],
    "port": host_port[1],
    "database": host_port_db[1]
}

print("🔧 AgentLink Phase 5 Migration")
print("=" * 50)

try:
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    print("✅ Connected to database")
    
    # Check if columns already exist
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'agent_states' 
        AND column_name IN ('claimed_by', 'claimed_at', 'claim_expires_at')
    """)
    existing_columns = [row[0] for row in cursor.fetchall()]
    
    if len(existing_columns) == 3:
        print("⚠️  Migration already applied! Columns exist:")
        for col in existing_columns:
            print(f"   - {col}")
        conn.close()
        exit(0)
    
    # Add columns
    print("\n📝 Adding columns...")
    
    if 'claimed_by' not in existing_columns:
        cursor.execute("""
            ALTER TABLE agent_states 
            ADD COLUMN claimed_by VARCHAR(255) DEFAULT NULL
        """)
        print("   ✅ claimed_by added")
    
    if 'claimed_at' not in existing_columns:
        cursor.execute("""
            ALTER TABLE agent_states 
            ADD COLUMN claimed_at TIMESTAMP DEFAULT NULL
        """)
        print("   ✅ claimed_at added")
    
    if 'claim_expires_at' not in existing_columns:
        cursor.execute("""
            ALTER TABLE agent_states 
            ADD COLUMN claim_expires_at TIMESTAMP DEFAULT NULL
        """)
        print("   ✅ claim_expires_at added")
    
    # Add indexes
    print("\n📊 Creating indexes...")
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_states_claimed_by 
        ON agent_states(claimed_by)
    """)
    print("   ✅ idx_states_claimed_by")
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_states_claim_expires 
        ON agent_states(claim_expires_at)
    """)
    print("   ✅ idx_states_claim_expires")
    
    conn.commit()
    
    print("\n🎉 Migration completed successfully!")
    print("=" * 50)
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
    exit(1)
