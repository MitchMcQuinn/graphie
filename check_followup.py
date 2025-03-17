import json
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Connect to Neo4j
driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

print('Connected to Neo4j')

# Get the memory for the generate-followup step with detailed debugging
with driver.session() as session:
    # Find a recent session
    sessions_result = session.run("""
        MATCH (s:SESSION) 
        RETURN s.id as session_id 
        ORDER BY s.created_at DESC 
        LIMIT 1
    """)
    
    recent_session = sessions_result.single()
    if not recent_session:
        print("No sessions found")
        exit(1)
        
    session_id = recent_session['session_id']
    print(f"Using session ID: {session_id}")
    
    # Get the full memory structure for this session
    memory_result = session.run("""
        MATCH (s:SESSION {id: $session_id})
        RETURN s.memory as memory, s.id as id
    """, session_id=session_id)
    
    record = memory_result.single()
    if not record or not record['memory']:
        print("No memory found for session")
        exit(1)
    
    # Parse the memory
    memory = json.loads(record['memory'])
    
    # Focus on generate-followup step details
    if 'generate-followup' in memory:
        print("\n=== GENERATE-FOLLOWUP STEP DETAILS ===")
        followup_entries = memory['generate-followup']
        print(f"Number of entries: {len(followup_entries)}")
        
        for idx, entry in enumerate(followup_entries):
            print(f"\nEntry {idx} Keys: {list(entry.keys())}")
            json_entry = json.dumps(entry, indent=2)
            print(f"Full Entry {idx}:\n{json_entry}")
    else:
        print("No generate-followup entries found")

    # Also examine the 'generate' step which handles both steps
    if 'generate' in memory:
        print("\n=== GENERATE STEP DETAILS ===")
        generate_entries = memory['generate']
        print(f"Number of entries: {len(generate_entries)}")
        
        for idx, entry in enumerate(generate_entries):
            print(f"\nGenerate Entry {idx} Keys: {list(entry.keys())}")
            
            # Only print the last entry in full to avoid overwhelming output
            if idx == len(generate_entries) - 1:
                json_entry = json.dumps(entry, indent=2)
                print(f"Last Generate Entry:\n{json_entry}")

    # Find what step is actually generating the follow-up question
    print("\n=== SEARCHING FOR FOLLOW-UP QUESTION SOURCE ===")
    for step_id, entries in memory.items():
        if step_id.startswith('generate') or 'follow' in step_id.lower():
            for entry in entries:
                # Look for strings that look like questions
                for key, value in entry.items():
                    if isinstance(value, str) and '?' in value:
                        print(f"Found potential follow-up in step '{step_id}', key '{key}':")
                        print(f"  {value}")
            
# Close the connection
driver.close()
print('\nNeo4j connection closed') 