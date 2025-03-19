#!/usr/bin/env python
"""
List all STEP nodes in the Neo4j database to understand their structure.
"""

import os
import logging
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Get Neo4j connection details
neo4j_uri = os.getenv('NEO4J_URL')
neo4j_user = os.getenv('NEO4J_USERNAME')
neo4j_password = os.getenv('NEO4J_PASSWORD')

def list_all_steps():
    """
    List all STEP nodes in the Neo4j database to understand their structure.
    """
    # Connect to Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            # Query to get all STEP nodes
            query = """
            MATCH (s:STEP)
            RETURN s
            """
            results = session.run(query)
            
            # Process and log the results
            steps = []
            for record in results:
                step = record["s"]
                props = dict(step.items())
                steps.append(props)
                logger.info(f"Step ID: {props.get('id', 'N/A')}")
                for key, value in props.items():
                    if key != 'id':
                        # Pretty-print JSON for input and other JSON fields
                        if key in ['input'] and value:
                            try:
                                json_value = json.loads(value)
                                logger.info(f"  {key}: {json.dumps(json_value, indent=2)}")
                            except json.JSONDecodeError:
                                logger.info(f"  {key}: {value}")
                        else:
                            logger.info(f"  {key}: {value}")
                logger.info("-" * 50)
            
            logger.info(f"Total steps found: {len(steps)}")
            
            # Specifically look for structured_generation
            for step in steps:
                for key, value in step.items():
                    if value and isinstance(value, str) and 'structured_generation' in value:
                        logger.info(f"Found 'structured_generation' in step {step.get('id', 'N/A')}, property {key}: {value}")
    
    finally:
        driver.close()

if __name__ == "__main__":
    list_all_steps() 