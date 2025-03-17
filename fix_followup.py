import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Connect to Neo4j
driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

print('Connected to Neo4j')

# Fix the generate-followup node to correctly update last_reply with the question text
with driver.session() as session:
    # Update generate-followup node with improved schema and response format
    generate_followup_result = session.run("""
    MATCH (n:STEP {id: 'generate-followup'})
    SET n.input = '{
  "system": "You are creating helpful follow-up questions for a conversational assistant. Create a single, concise follow-up question related to the previous topic that would help continue the conversation naturally.", 
  "temperature": 0.7, 
  "model": "gpt-4-turbo",
  "user": "@{last_reply}",
  "directly_set_reply": true,
  "include_history": true,
  "schema": {
    "type": "object",
    "properties": {
      "response": {
        "type": "string",
        "description": "A natural follow-up question to continue the conversation"
      }
    },
    "required": ["response"]
  }
}'
    RETURN n.id, n.input
    """)
    record = generate_followup_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")

# Close the connection
driver.close()
print('Neo4j connection closed')
print('Please restart the Flask app to apply these changes.') 