#!/usr/bin/env python
"""
Update workflow module paths in Neo4j steps.

This script updates references to utils.structured_generation module
to point to utils.generate instead, since the modules have been merged.
"""

import os
import logging
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

def update_workflow_module_paths():
    """
    Update function specifications in workflow steps from structured_generation to generate.
    """
    # Connect to Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            # Find and count structured_generation references in function specs
            count_query = """
            MATCH (s:STEP)
            WHERE s.function CONTAINS 'structured_generation'
            RETURN count(s) as count
            """
            count_result = session.run(count_query).single()
            if count_result:
                count = count_result["count"]
                logger.info(f"Found {count} steps using structured_generation")
                
                # Get the steps before updating
                steps_query = """
                MATCH (s:STEP)
                WHERE s.function CONTAINS 'structured_generation'
                RETURN s.id as step_id, s.function as function_spec
                """
                steps_before = []
                for record in session.run(steps_query):
                    steps_before.append((record["step_id"], record["function_spec"]))
                    logger.info(f"Found step {record['step_id']} with function: {record['function_spec']}")
                
                # Update the function specifications
                update_query = """
                MATCH (s:STEP)
                WHERE s.function CONTAINS 'structured_generation'
                SET s.function = REPLACE(s.function, 'structured_generation', 'generate')
                RETURN s.id as step_id, s.function as updated_function
                """
                update_results = session.run(update_query)
                
                # Log the updated steps
                updated_steps = []
                for record in update_results:
                    step_id = record["step_id"]
                    updated_function = record["updated_function"]
                    updated_steps.append((step_id, updated_function))
                    original_function = next(func for id, func in steps_before if id == step_id)
                    logger.info(f"Updated step {step_id}:")
                    logger.info(f"  Before: {original_function}")
                    logger.info(f"  After:  {updated_function}")
                
                if updated_steps:
                    logger.info(f"Successfully updated {len(updated_steps)} steps")
                else:
                    logger.info("No steps were updated")
            else:
                logger.info("No steps found using structured_generation")
    
    finally:
        driver.close()

if __name__ == "__main__":
    update_workflow_module_paths() 