from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

def run_setup():
    """Run the Neo4j setup script"""
    try:
        # Create driver
        driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        # Test connection
        with driver.session() as session:
            session.run("RETURN 1")
            logger.info("Connected to Neo4j successfully")
        
        # Read the setup script
        with open('setup_neo4j.cypher', 'r') as f:
            setup_script = f.read()
        
        # Split the script into individual statements
        # This regex splits on semicolons that are not inside quotes
        statements = []
        current_statement = []
        
        for line in setup_script.split('\n'):
            # Skip empty lines and comments
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('//'):
                continue
            
            current_statement.append(line)
            
            # If the line ends with a semicolon, it's the end of a statement
            if stripped_line.endswith(';'):
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        # Run each statement separately
        with driver.session() as session:
            for i, statement in enumerate(statements):
                if statement.strip():
                    logger.info(f"Running statement {i+1}: {statement[:50]}...")
                    result = session.run(statement)
                    for record in result:
                        logger.info(f"Result: {record}")
        
        logger.info("Neo4j schema setup complete")
        
        # Close the driver
        driver.close()
        return True
    except Exception as e:
        logger.error(f"Error setting up Neo4j schema: {str(e)}")
        return False

if __name__ == "__main__":
    run_setup() 