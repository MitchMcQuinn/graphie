import os
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv

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
try:
    driver = GraphDatabase.driver(
        NEO4J_URL, 
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )
    logger.info("Connected to Neo4j database")
except Exception as e:
    logger.error(f"Failed to connect to Neo4j: {str(e)}")
    exit(1)

def update_workflow():
    """
    Update the workflow to support parallel processing.
    This function adds parallel branches and conditions to the workflow.
    """
    with driver.session() as session:
        # First, check if there's a relationship between get-input and extract-animal
        result = session.run("""
        MATCH (input:STEP {id: 'get-input'})-[r:NEXT]->(extract:STEP {id: 'extract-animal'})
        RETURN r
        """)
        
        if result.single():
            logger.info("Relationship between get-input and extract-animal already exists")
        else:
            # Create a relationship with a true condition to ensure it always executes
            session.run("""
            MATCH (input:STEP {id: 'get-input'})
            MATCH (extract:STEP {id: 'extract-animal'})
            CREATE (input)-[r:NEXT {
                description: "Always extract animal",
                function: "condition.true",
                input: '{}'
            }]->(extract)
            """)
            logger.info("Added relationship between get-input and extract-animal with true condition")
        
        # Also make sure there's a relationship between get-input and analyze-input
        result = session.run("""
        MATCH (input:STEP {id: 'get-input'})-[r:NEXT]->(analyze:STEP {id: 'analyze-input'})
        RETURN r
        """)
        
        if result.single():
            logger.info("Relationship between get-input and analyze-input already exists")
        else:
            # Create a relationship with a true condition to ensure it always executes
            session.run("""
            MATCH (input:STEP {id: 'get-input'})
            MATCH (analyze:STEP {id: 'analyze-input'})
            CREATE (input)-[r:NEXT {
                description: "Always analyze sentiment",
                function: "condition.true",
                input: '{}'
            }]->(analyze)
            """)
            logger.info("Added relationship between get-input and analyze-input with true condition")
        
        # Make sure the extract-animal step is properly configured
        session.run("""
        MATCH (n:STEP {id: 'extract-animal'})
        SET n.function = 'utils.structured_generation.analyze_input',
            n.input = '{
    "type": "structured",
    "system": "You are an experience analyzer that identifies key topic of discussion (in this case, likely an animal) within a sample of text. Your objective is to extract the name of the animal.",
    "user": "@{get-input}.response",
    "temperature": 0.5,
    "model": "gpt-4-turbo",
    "function_name": "extract_animal",
    "function_description": "Extract the animal name from the response",
    "response_format": {
      "type": "object",
      "properties": {
        "animal_name": {
          "type": "string", "description":"The animal name in singular form"
        }
      }
    }
  }'
        """)
        logger.info("Updated extract-animal step")
        
        # Make sure the return-animal step is properly configured
        session.run("""
        MATCH (n:STEP {id: 'return-animal'})
        SET n.function = 'reply.reply',
            n.input = '{"reply": "The extracted animal is: @{extract-animal}.animal_name"}'
        """)
        logger.info("Updated return-animal step")
        
        # Make sure there's a relationship between extract-animal and return-animal
        result = session.run("""
        MATCH (extract:STEP {id: 'extract-animal'})-[r:NEXT]->(return:STEP {id: 'return-animal'})
        RETURN r
        """)
        
        if result.single():
            logger.info("Relationship between extract-animal and return-animal already exists")
        else:
            # Create a relationship
            session.run("""
            MATCH (extract:STEP {id: 'extract-animal'})
            MATCH (return:STEP {id: 'return-animal'})
            CREATE (extract)-[:NEXT]->(return)
            """)
            logger.info("Added relationship between extract-animal and return-animal")
        
        # Add a relationship from return-animal to continue-question
        # This ensures both paths eventually converge
        result = session.run("""
        MATCH (return:STEP {id: 'return-animal'})-[r:NEXT]->(continue:STEP {id: 'continue-question'})
        RETURN r
        """)
        
        if result.single():
            logger.info("Relationship between return-animal and continue-question already exists")
        else:
            # Create a relationship
            session.run("""
            MATCH (return:STEP {id: 'return-animal'})
            MATCH (continue:STEP {id: 'continue-question'})
            CREATE (return)-[:NEXT {id: 'to-continue-from-animal'}]->(continue)
            """)
            logger.info("Added relationship between return-animal and continue-question")
    
    # Re-display the workflow structure
    with driver.session() as session:
        step_count = session.run("MATCH (n:STEP) RETURN count(n) as count").single()["count"]
        rel_count = session.run("MATCH ()-[r:NEXT]->() RETURN count(r) as count").single()["count"]
        
        logger.info(f"Updated workflow structure: {step_count} nodes, {rel_count} relationships")
        logger.info("Workflow now supports parallel processing for animal extraction!")

if __name__ == "__main__":
    logger.info("Updating workflow for parallel processing...")
    update_workflow()
    
    # Close the Neo4j connection
    driver.close()
    logger.info("Workflow update completed!") 