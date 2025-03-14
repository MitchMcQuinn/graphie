import os
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

def check_workflow():
    """Check the workflow graph to verify all nodes and relationships"""
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        logger.info("Connected to Neo4j successfully")
        
        with driver.session() as session:
            # Get all steps
            result = session.run("MATCH (n:STEP) RETURN n.id as id, n.function as function ORDER BY n.id")
            steps = list(result)
            
            logger.info(f"Found {len(steps)} workflow steps:")
            for step in steps:
                logger.info(f"  - {step['id']}: {step['function']}")
            
            # Get all relationships
            result = session.run("""
                MATCH (a:STEP)-[r:NEXT]->(b:STEP)
                RETURN a.id as from_id, b.id as to_id, r.function as condition
                ORDER BY a.id, b.id
            """)
            relationships = list(result)
            
            logger.info(f"Found {len(relationships)} relationships:")
            for rel in relationships:
                logger.info(f"  - {rel['from_id']} -> {rel['to_id']} [Condition: {rel['condition']}]")
            
            # Check paths from root to get-input
            result = session.run("""
                MATCH path = (:STEP {id: 'root-2'})-[:NEXT*]->(:STEP {id: 'get-input'})
                RETURN length(path) as path_length
            """)
            paths = list(result)
            if paths:
                logger.info(f"Found path from root-2 to get-input with length {paths[0]['path_length']}")
            else:
                logger.warning("No path found from root-2 to get-input!")
            
            # Check paths from get-input to extract-animal
            result = session.run("""
                MATCH path = (:STEP {id: 'get-input'})-[:NEXT*]->(:STEP {id: 'extract-animal'})
                RETURN length(path) as path_length
            """)
            paths = list(result)
            if paths:
                logger.info(f"Found path from get-input to extract-animal with length {paths[0]['path_length']}")
            else:
                logger.warning("No path found from get-input to extract-animal!")
            
            # Check paths from get-input to analyze-input
            result = session.run("""
                MATCH path = (:STEP {id: 'get-input'})-[:NEXT*]->(:STEP {id: 'analyze-input'})
                RETURN length(path) as path_length
            """)
            paths = list(result)
            if paths:
                logger.info(f"Found path from get-input to analyze-input with length {paths[0]['path_length']}")
            else:
                logger.warning("No path found from get-input to analyze-input!")
            
            # Check paths from extract-animal to return-animal
            result = session.run("""
                MATCH path = (:STEP {id: 'extract-animal'})-[:NEXT*]->(:STEP {id: 'return-animal'})
                RETURN length(path) as path_length
            """)
            paths = list(result)
            if paths:
                logger.info(f"Found path from extract-animal to return-animal with length {paths[0]['path_length']}")
            else:
                logger.warning("No path found from extract-animal to return-animal!")
            
            # Check for any isolated nodes (no incoming or outgoing relationships)
            result = session.run("""
                MATCH (n:STEP)
                WHERE NOT (n)-[:NEXT]->() AND NOT ()-[:NEXT]->(n)
                RETURN n.id as id
            """)
            isolated = list(result)
            if isolated:
                logger.warning(f"Found {len(isolated)} isolated nodes:")
                for node in isolated:
                    logger.warning(f"  - {node['id']}")
            else:
                logger.info("No isolated nodes found.")
            
            # Check for nodes with inputs referencing non-existent variables
            result = session.run("""
                MATCH (n:STEP)
                WHERE n.input CONTAINS '@{'
                RETURN n.id as id, n.input as input
            """)
            nodes_with_vars = list(result)
            
            logger.info(f"Found {len(nodes_with_vars)} nodes with variable references:")
            for node in nodes_with_vars:
                logger.info(f"  - {node['id']}: {node['input']}")
            
        # Close the Neo4j connection
        driver.close()
        logger.info("Neo4j connection closed")
        
    except Exception as e:
        logger.error(f"Error checking workflow: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting workflow verification")
    check_workflow()
    logger.info("Workflow verification completed") 