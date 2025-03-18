#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

def update_workflow_steps():
    """Update the workflow steps to use the correct variable references"""
    # Connect to Neo4j
    driver = GraphDatabase.driver(
        NEO4J_URL, 
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )
    
    try:
        with driver.session() as session:
            # Update the provide-answer step
            result = session.run("""
                MATCH (s:STEP {id: 'provide-answer'})
                SET s.input = '{\n  "response": "@{SESSION_ID}.generate-answer.response"\n}'
                RETURN s.id as id, s.input as input
            """)
            
            record = result.single()
            if record:
                logger.info(f"Updated step {record['id']} with input: {record['input']}")
            else:
                logger.warning("Failed to update provide-answer step")
            
            # Update the generate-followup step
            result = session.run("""
                MATCH (s:STEP {id: 'generate-followup'})
                SET s.input = REPLACE(s.input, '@{SESSION_ID}.provide-answer.reply', '@{SESSION_ID}.generate-answer.response')
                RETURN s.id as id, s.input as input
            """)
            
            record = result.single()
            if record:
                logger.info(f"Updated step {record['id']} with input: {record['input']}")
            else:
                logger.warning("Failed to update generate-followup step")
                
    finally:
        driver.close()
        
    logger.info("Workflow steps updated successfully")

if __name__ == "__main__":
    logger.info("Updating workflow steps...")
    update_workflow_steps()
    logger.info("Done!") 