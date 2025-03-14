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

def check_and_clean_workflow():
    """Check the workflow graph and clean up conflicting nodes"""
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
            
            # Look for analyze-input and extract-animal nodes with structured_generation
            result = session.run("""
                MATCH (n:STEP)
                WHERE n.id IN ['analyze-input', 'extract-animal'] AND n.function CONTAINS 'structured_generation'
                RETURN n.id as id, n.function as function
            """)
            
            bad_nodes = list(result)
            if bad_nodes:
                logger.warning(f"Found {len(bad_nodes)} nodes with incorrect functions:")
                for node in bad_nodes:
                    logger.warning(f"  - {node['id']}: {node['function']}")
                
                # Update these nodes to use our analyze.py module
                logger.info("Updating nodes to use analyze.analyze_input...")
                
                result = session.run("""
                    MATCH (n:STEP)
                    WHERE n.id = 'analyze-input'
                    SET n.function = 'analyze.analyze_input',
                        n.input = '{"function": "sentiment_analysis", "input": "@{get-input}.user_input"}'
                    RETURN n.id as id
                """)
                
                updated = list(result)
                for node in updated:
                    logger.info(f"Updated {node['id']} to use analyze.analyze_input")
                
                result = session.run("""
                    MATCH (n:STEP)
                    WHERE n.id = 'extract-animal'
                    SET n.function = 'analyze.analyze_input',
                        n.input = '{"function": "extract_animal_names", "input": "@{get-input}.user_input"}'
                    RETURN n.id as id
                """)
                
                updated = list(result)
                for node in updated:
                    logger.info(f"Updated {node['id']} to use analyze.analyze_input")
            else:
                logger.info("No nodes with incorrect functions found")
            
            # Check for other nodes with incorrect variable references
            result = session.run("""
                MATCH (n:STEP)
                WHERE n.id = 'return-animal'
                RETURN n.id as id, n.input as input
            """)
            
            animal_nodes = list(result)
            if animal_nodes:
                logger.info("Checking return-animal nodes for correct variable references")
                for node in animal_nodes:
                    if '@{extract-animal}.animal_name' in node['input']:
                        # Update to use .animals instead
                        logger.info(f"Updating {node['id']} to use correct variable references")
                        session.run("""
                            MATCH (n:STEP)
                            WHERE n.id = 'return-animal'
                            SET n.input = '{"reply": "I notice you mentioned @{extract-animal}.animals. @{analyze-input}.sentiment Would you like to know more about this animal?"}'
                            RETURN n.id as id
                        """)
                        logger.info(f"Updated {node['id']} to use correct variable references")
            
            # Check paths are correct
            result = session.run("""
                MATCH p = (:STEP {id: 'get-input'})-[:NEXT]->(:STEP {id: 'extract-animal'})-[:NEXT]->(:STEP {id: 'return-animal'})
                RETURN COUNT(p) as path_count
            """)
            
            path_count = result.single()['path_count']
            logger.info(f"Found {path_count} complete paths from get-input through extract-animal to return-animal")
            
            if path_count == 0:
                logger.warning("No complete path found, checking individual relationships...")
                
                # Check get-input to extract-animal
                result = session.run("""
                    MATCH (:STEP {id: 'get-input'})-[r:NEXT]->(:STEP {id: 'extract-animal'})
                    RETURN COUNT(r) as rel_count
                """)
                
                rel_count = result.single()['rel_count']
                if rel_count == 0:
                    logger.warning("No relationship from get-input to extract-animal, creating...")
                    
                    session.run("""
                        MATCH (a:STEP {id: 'get-input'}), (b:STEP {id: 'extract-animal'})
                        CREATE (a)-[:NEXT {function: 'condition.true', input: '{}'}]->(b)
                    """)
                    
                    logger.info("Created relationship from get-input to extract-animal")
                
                # Check extract-animal to return-animal
                result = session.run("""
                    MATCH (:STEP {id: 'extract-animal'})-[r:NEXT]->(:STEP {id: 'return-animal'})
                    RETURN COUNT(r) as rel_count
                """)
                
                rel_count = result.single()['rel_count']
                if rel_count == 0:
                    logger.warning("No relationship from extract-animal to return-animal, creating...")
                    
                    session.run("""
                        MATCH (a:STEP {id: 'extract-animal'}), (b:STEP {id: 'return-animal'})
                        CREATE (a)-[:NEXT {function: 'condition.true', input: '{}'}]->(b)
                    """)
                    
                    logger.info("Created relationship from extract-animal to return-animal")
            
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
                logger.info("No isolated nodes found")
            
        # Close the Neo4j connection
        driver.close()
        logger.info("Neo4j connection closed")
        
    except Exception as e:
        logger.error(f"Error checking workflow: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting workflow cleanup")
    check_and_clean_workflow()
    logger.info("Workflow cleanup completed") 