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

# Update the generate-followup node to use proper variable referencing
with driver.session() as session:
    result = session.run('''
    MATCH (n:STEP {id: 'generate-followup'})
    SET n.input = '{
  "system": "You are creating helpful follow-up questions for a conversational assistant.", 
  "temperature": 0.7, 
  "model": "gpt-4-turbo",
  "user": "@{provide-answer}.response",
  "directly_set_reply": true,
  "include_history": true,
  "schema": {
    "type": "object",
    "properties": {
      "follow_up_question": {
        "type": "string",
        "description": "A single follow-up question related to the previous topic"
      },
      "response": {
        "type": "string",
        "description": "A question to offer more information to the user"
      }
    },
    "required": ["follow_up_question", "response"]
  }
}'
    RETURN n
    ''')
    print('Updated generate-followup node:', result.single())
    
    # Update the provide-answer node to also use the step-based variable pattern
    result = session.run('''
    MATCH (n:STEP {id: 'provide-answer'})
    SET n.input = '{
  "response": "@{generate-answer}.generation.response"
}'
    RETURN n
    ''')
    print('Updated provide-answer node:', result.single())
    
    # Make sure get-question node also uses proper variable references
    result = session.run('''
    MATCH (n:STEP {id: 'get-question'})
    SET n.input = '{
  "query": "@{generate-followup}.response|Hello! How can I help you today?"
}'
    RETURN n
    ''')
    print('Updated get-question node:', result.single())

# Close the connection
driver.close()
print('Neo4j connection closed') 