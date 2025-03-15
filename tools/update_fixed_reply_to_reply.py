#!/usr/bin/env python3
import os
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase, basic_auth

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

def update_function_references():
    """
    Updates Neo4j database to change fixed_reply to reply in all workflow nodes
    """
    if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
        logger.error("Missing Neo4j connection details. Make sure NEO4J_URL, NEO4J_USERNAME, and NEO4J_PASSWORD are in .env.local")
        return False
    
    logger.info("Connecting to Neo4j database...")
    
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URL,
            auth=basic_auth(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            # Find all nodes that use fixed_reply
            result = session.run("""
                MATCH (n:STEP)
                WHERE n.function CONTAINS 'fixed_reply'
                RETURN n.id as id, n.function as function
            """)
            
            nodes_to_update = list(result)
            logger.info(f"Found {len(nodes_to_update)} nodes using fixed_reply")
            
            # Update function references from fixed_reply to reply
            result = session.run("""
                MATCH (n:STEP)
                WHERE n.function CONTAINS 'fixed_reply'
                SET n.function = REPLACE(n.function, 'fixed_reply', 'reply')
                RETURN n.id as id, n.function as updated_function
            """)
            
            updated_nodes = list(result)
            for node in updated_nodes:
                logger.info(f"Updated node {node['id']} from fixed_reply to {node['updated_function']}")
            
            # Update any input data that might reference fixed_reply
            result = session.run("""
                MATCH (n:STEP)
                WHERE n.input CONTAINS 'fixed_reply'
                SET n.input = REPLACE(n.input, 'fixed_reply', 'reply')
                RETURN n.id as id
            """)
            
            nodes_with_input_updated = list(result)
            logger.info(f"Updated input references in {len(nodes_with_input_updated)} nodes")
            
            logger.info("Database update completed successfully")
        
        driver.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating Neo4j database: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting fixed_reply to reply reference update")
    success = update_function_references()
    if success:
        logger.info("Successfully updated all fixed_reply references to reply")
    else:
        logger.error("Failed to update some or all fixed_reply references") 