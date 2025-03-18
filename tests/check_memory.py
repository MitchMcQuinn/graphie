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

# Get the memory for the generate-followup step
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
    
    # Get the memory for this session
    memory_result = session.run("""
        MATCH (s:SESSION {id: $session_id})
        RETURN s.memory as memory
    """, session_id=session_id)
    
    record = memory_result.single()
    if not record or not record['memory']:
        print("No memory found for session")
        exit(1)
    
    # Parse the memory
    memory = json.loads(record['memory'])
    
    # Print all step keys
    print("\nStep keys in memory:")
    for step_key in memory.keys():
        print(f"- {step_key}")
    
    # Check specifically for generate-followup
    if 'generate-followup' in memory:
        print("\nGenerate-followup memory:")
        followup_memory = memory['generate-followup']
        for idx, entry in enumerate(followup_memory):
            print(f"\nEntry {idx}:")
            for key, value in entry.items():
                print(f"  {key}: {value}")
    else:
        print("\nNo generate-followup in memory")
    
    # Check for generate step
    if 'generate' in memory:
        print("\nGenerate step memory:")
        generate_memory = memory['generate']
        for idx, entry in enumerate(generate_memory):
            print(f"\nEntry {idx}:")
            for key, value in entry.items():
                print(f"  {key}: {value}")
    
# Close the connection
driver.close()
print('\nNeo4j connection closed') 