"""
core/workflow/migrations/update_workflow_data.py
----------------
This script updates existing workflow data to match the new schema.
"""

from neo4j import Driver
import json
import logging

logger = logging.getLogger(__name__)

def migrate(driver: Driver) -> bool:
    """
    Update existing workflow data to match the new schema.
    
    Args:
        driver: Neo4j driver instance
        
    Returns:
        bool: True if migration was successful, False otherwise
    """
    try:
        with driver.session() as session:
            # Update existing STEP nodes with status
            session.run("""
                MATCH (s:STEP)
                WHERE s.status IS NULL
                SET s.status = 'inactive'
            """)
            
            # Update existing SESSION nodes with new state structure
            session.run("""
                MATCH (s:SESSION)
                WHERE s.state IS NULL
                WITH s, {
                    id: s.id,
                    workflow: {
                        root: {
                            status: 'active',
                            error: ''
                        }
                    },
                    data: {
                        outputs: {},
                        messages: []
                    }
                } as state_obj
                SET s.state = apoc.convert.toJson(state_obj)
            """)
            
            logger.info("Successfully updated workflow data")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update workflow data: {str(e)}")
        return False

def rollback(driver: Driver) -> bool:
    """
    Rollback the data changes.
    
    Args:
        driver: Neo4j driver instance
        
    Returns:
        bool: True if rollback was successful, False otherwise
    """
    try:
        with driver.session() as session:
            # Remove status from STEP nodes
            session.run("""
                MATCH (s:STEP)
                REMOVE s.status
            """)
            
            # Remove state from SESSION nodes
            session.run("""
                MATCH (s:SESSION)
                REMOVE s.state
            """)
            
            logger.info("Successfully rolled back workflow data")
            return True
            
    except Exception as e:
        logger.error(f"Failed to rollback workflow data: {str(e)}")
        return False 