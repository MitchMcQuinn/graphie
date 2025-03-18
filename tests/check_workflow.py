from neo4j import GraphDatabase
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

def check_workflow():
    """Check the workflow structure in Neo4j"""
    # Neo4j connection details
    neo4j_url = os.getenv('NEO4J_URL')
    neo4j_username = os.getenv('NEO4J_USERNAME')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    # Create driver
    driver = GraphDatabase.driver(
        neo4j_url,
        auth=(neo4j_username, neo4j_password)
    )
    
    try:
        with driver.session() as session:
            # Check STEP nodes
            result = session.run("MATCH (s:STEP) RETURN s.id as id, s.function as function ORDER BY id")
            steps = [(record['id'], record['function']) for record in result]
            logger.info(f"STEP nodes: {steps}")
            
            # Check NEXT relationships
            result = session.run("""
                MATCH (s1:STEP)-[r:NEXT]->(s2:STEP)
                RETURN s1.id as source, s2.id as target, 
                       CASE WHEN r.function IS NOT NULL THEN r.function ELSE 'none' END as condition
            """)
            relationships = [(record['source'], record['target'], record['condition']) for record in result]
            logger.info(f"NEXT relationships: {relationships}")
            
            # Check SESSION nodes
            result = session.run("""
                MATCH (s:SESSION)
                RETURN s.id as id, s.status as status, s.next_steps as next_steps
            """)
            sessions = [(record['id'], record['status'], record['next_steps']) for record in result]
            logger.info(f"SESSION nodes: {sessions}")
            
            # Check a specific session's memory
            if sessions and len(sessions) > 0:
                session_id = sessions[0][0]  # Get the first session ID
                result = session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.memory as memory, s.chat_history as chat_history
                """, session_id=session_id)
                
                record = result.single()
                if record:
                    logger.info(f"Sample session memory: {record['memory'][:100]}...")
                    logger.info(f"Sample chat history: {record['chat_history'][:100]}...")
    except Exception as e:
        logger.error(f"Error checking workflow: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    check_workflow() 