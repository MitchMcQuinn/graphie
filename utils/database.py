"""
utils/database.py
-----------------
This module provides utilities for connecting to Neo4j database.
"""

import os
import logging
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

# Check if Neo4j connection details are available
if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
    logger.warning("Neo4j connection details are missing. Please set NEO4J_URL, NEO4J_USERNAME, and NEO4J_PASSWORD in .env.local")

try:
    from neo4j import GraphDatabase
except ImportError:
    logger.error("Neo4j Python driver not installed. Please run 'pip install neo4j'")
    GraphDatabase = None

# Global Neo4j driver instance
_neo4j_driver = None

def get_neo4j_driver():
    """
    Get a Neo4j driver instance.
    
    Returns:
        A Neo4j driver instance or None if connection details are missing
    """
    global _neo4j_driver
    
    # Return existing driver if already initialized
    if _neo4j_driver is not None:
        return _neo4j_driver
    
    # Check if we have connection details
    if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
        logger.error("Neo4j connection details are missing. Cannot create driver.")
        return None
    
    # Initialize driver
    try:
        _neo4j_driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        # Test the connection
        with _neo4j_driver.session() as session:
            session.run("RETURN 1")
        logger.info("Connected to Neo4j successfully")
        return _neo4j_driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {str(e)}")
        return None

def has_session(session_id):
    """
    Check if a session exists in the database.
    
    Args:
        session_id: The ID of the session to check
        
    Returns:
        bool: True if the session exists, False otherwise
    """
    driver = get_neo4j_driver()
    if not driver:
        return False
    
    try:
        with driver.session() as db_session:
            result = db_session.run("""
                MATCH (s:SESSION {id: $session_id})
                RETURN count(s) as count
            """, session_id=session_id)
            
            record = result.single()
            return record and record['count'] > 0
    except Exception as e:
        logger.error(f"Error checking if session exists: {str(e)}")
        return False 