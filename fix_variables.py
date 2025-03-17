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

# Get all nodes to see the structure before updating
with driver.session() as session:
    result = session.run("MATCH (n:STEP) RETURN n.id, n.input")
    print("Current nodes in the graph:")
    for record in result:
        print(f"Node ID: {record['n.id']}")
        print(f"Input: {record['n.input']}\n")

# Now update nodes with proper variable references
with driver.session() as session:
    # Fix get-question node - simplify by using a hardcoded greeting
    get_question_result = session.run("""
    MATCH (n:STEP {id: 'get-question'})
    SET n.input = '{"query": "Hello! How can I help you today?"}'
    RETURN n.id, n.input
    """)
    record = get_question_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")
    
    # Fix generate-answer node to correctly access user input
    generate_answer_result = session.run("""
    MATCH (n:STEP {id: 'generate-answer'})
    SET n.input = '{
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "system": "You are a helpful assistant specializing in explaining topics in a user-friendly way. Provide clear explanations that assume no prior knowledge. Maintain the conversation context and topic throughout your responses.",
  "user": "@{response}",
  "include_history": true,
  "directly_set_reply": true,
  "schema": {
    "type": "object",
    "properties": {
      "response": {
        "type": "string",
        "description": "The main response to the user query"
      },
      "key_points": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "Key points covered in the response"
      }
    },
    "required": ["response", "key_points"]
  }
}'
    RETURN n.id, n.input
    """)
    record = generate_answer_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")
    
    # Fix provide-answer node - simplify to use last_reply
    provide_answer_result = session.run("""
    MATCH (n:STEP {id: 'provide-answer'})
    SET n.input = '{"response": "@{last_reply}"}'
    RETURN n.id, n.input
    """)
    record = provide_answer_result.single()
    print(f"Updated {record['n.id']} node with input: {record['n.input']}")
    
    # Fix generate-followup node - simplify to use a cleaner format
    generate_followup_result = session.run("""
    MATCH (n:STEP {id: 'generate-followup'})
    SET n.input = '{
  "system": "You are creating helpful follow-up questions for a conversational assistant. Your task is to generate a single follow-up question related to the previous response.", 
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
        "description": "A single helpful follow-up question related to the previous topic"
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