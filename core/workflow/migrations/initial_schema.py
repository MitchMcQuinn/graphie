"""
core/workflow/migrations/001_initial_schema.py
----------------
This script sets up the initial Neo4j schema for the new workflow engine.
"""

from neo4j import Driver
import logging

logger = logging.getLogger(__name__)

def migrate(driver: Driver) -> bool:
    """
    Run the initial schema migration.
    
    Args:
        driver: Neo4j driver instance
        
    Returns:
        bool: True if migration was successful, False otherwise
    """
    try:
        with driver.session() as session:
            # Create constraints
            session.run("""
                CREATE CONSTRAINT session_id IF NOT EXISTS
                FOR (s:SESSION) REQUIRE s.id IS UNIQUE
            """)
            
            session.run("""
                CREATE CONSTRAINT step_id IF NOT EXISTS
                FOR (s:STEP) REQUIRE s.id IS UNIQUE
            """)
            
            # Create indexes
            session.run("""
                CREATE INDEX session_state IF NOT EXISTS
                FOR (s:SESSION) ON (s.state)
            """)
            
            session.run("""
                CREATE INDEX step_status IF NOT EXISTS
                FOR (s:STEP) ON (s.status)
            """)
            
            # Update existing NEXT relationships with default conditions
            session.run("""
                MATCH (s:STEP)-[r:NEXT]->(t:STEP)
                WHERE r.conditions IS NULL
                SET r.conditions = [],
                    r.operator = 'AND'
            """)
            
            # Create relationship property existence constraint
            session.run("""
                CREATE CONSTRAINT next_relationship IF NOT EXISTS
                FOR ()-[r:NEXT]-() REQUIRE r.conditions IS NOT NULL
            """)
            
            logger.info("Successfully created Neo4j schema")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create Neo4j schema: {str(e)}")
        return False

def rollback(driver: Driver) -> bool:
    """
    Rollback the schema changes.
    
    Args:
        driver: Neo4j driver instance
        
    Returns:
        bool: True if rollback was successful, False otherwise
    """
    try:
        with driver.session() as session:
            # Drop constraints
            session.run("DROP CONSTRAINT session_id IF EXISTS")
            session.run("DROP CONSTRAINT step_id IF EXISTS")
            session.run("DROP CONSTRAINT next_relationship IF EXISTS")
            
            # Drop indexes
            session.run("DROP INDEX session_state IF EXISTS")
            session.run("DROP INDEX step_status IF EXISTS")
            
            logger.info("Successfully rolled back Neo4j schema")
            return True
            
    except Exception as e:
        logger.error(f"Failed to rollback Neo4j schema: {str(e)}")
        return False 