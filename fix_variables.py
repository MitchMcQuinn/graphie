import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import json
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

# Get all nodes to see the structure before updating
with driver.session() as session:
    result = session.run("MATCH (n:STEP) RETURN n.id, n.input")
    print("Current nodes in the graph:")
    for record in result:
        print(f"Node ID: {record['n.id']}")
        print(f"Input: {record['n.input']}\n")

# Now update all STEP nodes to ensure proper variable references and consistent output format
with driver.session() as session:
    # First remove any unnecessary nodes from the workflow
    check_ask_followup = session.run("""
    MATCH (n:STEP {id: 'ask-followup'})
    RETURN count(n) as count
    """)
    
    if check_ask_followup.single()['count'] > 0:
        print("Removing ask-followup node")
        session.run("""
        MATCH (n:STEP {id: 'ask-followup'})
        DETACH DELETE n
        """)
    
    # Update each node to ensure proper variables and references
    
    # Get-question node
    get_question_result = session.run('''
    MATCH (n:STEP {id: 'get-question'})
    SET n.input = '{"query": "@{SESSION_ID}.generate-followup.response|GM! How can I help you today?"}'
    RETURN n.id, n.input
    ''')
    record = get_question_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")
    
    # Generate-answer node - Updated to use response_key for consistent output format
    generate_answer_result = session.run("""
    MATCH (n:STEP {id: 'generate-answer'})
    SET n.input = '{
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "system": "You are a helpful assistant specializing in explaining topics in a user-friendly way. Provide clear explanations that assume no prior knowledge. Maintain the conversation context and topic throughout your responses.",
  "user": "@{SESSION_ID}.get-question.response",
  "include_history": true,
  "response_key": "response"
}'
    RETURN n.id, n.input
    """)
    record = generate_answer_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")
    
    # Provide-answer node
    provide_answer_result = session.run("""
    MATCH (n:STEP {id: 'provide-answer'})
    SET n.input = '{"response": "@{SESSION_ID}.generate-answer.response"}'
    RETURN n.id, n.input
    """)
    record = provide_answer_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")
    
    # Generate-followup node - Properly configured for direct response format
    # Important: 1) Removed schema parameter, 2) Added response_key parameter
    generate_followup_result = session.run("""
    MATCH (n:STEP {id: 'generate-followup'})
    SET n.input = '{
  "model": "gpt-4-turbo",
  "temperature": 0.7,
  "system": "You are creating a follow-up question for a conversational assistant. Generate a single relevant follow-up question based on the previous response.",
  "user": "@{SESSION_ID}.generate-answer.response",
  "include_history": true,
  "max_tokens": 100,
  "response_key": "response"
}'
    RETURN n.id, n.input
    """)
    record = generate_followup_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")
    
    # Ensure connections are set up properly to match the desired workflow
    print("Checking and fixing workflow connections...")
    
    # Make sure generate-followup connects back to get-question (circular flow)
    check_connection = session.run("""
    MATCH (source:STEP {id: 'generate-followup'})-[:NEXT]->(target:STEP {id: 'get-question'})
    RETURN count(*) as count
    """)
    
    if check_connection.single()['count'] == 0:
        print("Creating connection from generate-followup to get-question")
        session.run("""
        MATCH (source:STEP {id: 'generate-followup'}), (target:STEP {id: 'get-question'})
        CREATE (source)-[:NEXT]->(target)
        """)
    
    # Verify all workflow connections
    connection_check = session.run("""
    MATCH path = (root:STEP {id: 'root'})-[:NEXT*]->(n:STEP)
    RETURN [step in nodes(path) | step.id] as workflow_path
    """)
    
    for record in connection_check:
        print(f"Flow path: {' -> '.join(record['workflow_path'])}")

# Close the connection
driver.close()
print('Neo4j connection closed')
print('Please restart the Flask app to apply these changes.') 