"""
tools/run_migrations.py
----------------
This script runs the database migrations for the workflow engine.
"""

import os
import sys
import logging
from neo4j import GraphDatabase

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow.migrations.manager import MigrationManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run the database migrations."""
    try:
        # Get Neo4j connection details from environment
        uri = os.getenv("NEO4J_URL")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not all([uri, user, password]):
            logger.error("Missing required environment variables")
            sys.exit(1)
        
        # Create Neo4j driver
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        try:
            # Create migration manager
            manager = MigrationManager(driver)
            
            # Run migrations
            if not manager.run_migrations():
                logger.error("Failed to run migrations")
                sys.exit(1)
            
            logger.info("Successfully completed all migrations")
            
        finally:
            # Close the driver
            driver.close()
            
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 