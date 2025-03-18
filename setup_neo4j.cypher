// Create constraint to ensure SESSION IDs are unique
CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:SESSION) REQUIRE s.id IS UNIQUE;

// Create index on SESSION node id for better performance
CREATE INDEX session_id_index IF NOT EXISTS FOR (s:SESSION) ON (s.id);

// Create a test SESSION node with memory as a JSON string if it doesn't exist
MERGE (s:SESSION {id: 'test-session'})
ON CREATE SET 
    s.memory = '{}',
    s.next_steps = ['root'],
    s.created_at = datetime(),
    s.status = 'active',
    s.errors = '[]',
    s.chat_history = '[]';

// Display message
RETURN 'Neo4j schema setup complete' AS message; 