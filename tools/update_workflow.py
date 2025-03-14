import os
import logging
from neo4j import GraphDatabase
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

def update_workflow():
    """Update the workflow in Neo4j to fix the structured generation example"""
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(
        NEO4J_URL, 
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )
    
    try:
        with driver.session() as session:
            # First, check if the workflow exists
            result = session.run(
                "MATCH (n:STEP {id: 'root-2'}) RETURN count(n) as count"
            )
            record = result.single()
            
            if record and record['count'] > 0:
                logger.info("Found existing workflow, updating...")
                
                # Update the generate.generate step to store structured result
                session.run("""
                MATCH (n:STEP {id: 'analyze-input'})
                SET n.function = 'utils.structured_generation.analyze_input'
                """)
                logger.info("Updated analyze-input to use structured_generation.analyze_input")
                
                # Create the analyze_input function in structured_generation.py
                
                # Update the provide-analysis step
                session.run("""
                MATCH (n:STEP {id: 'provide-analysis'})
                SET n.function = 'utils.structured_generation.format_analysis',
                    n.input = '{
                      "is_positive": "@{analyze-input}.is_positive",
                      "feedback": "@{analyze-input}.feedback"
                    }'
                """)
                logger.info("Updated provide-analysis step")
                
                # Update show-analysis or create if it doesn't exist
                result = session.run(
                    "MATCH (n:STEP {id: 'show-analysis'}) RETURN count(n) as count"
                )
                show_record = result.single()
                
                if show_record and show_record['count'] > 0:
                    # Update existing show-analysis step
                    session.run("""
                    MATCH (n:STEP {id: 'show-analysis'})
                    SET n.function = 'reply.reply',
                        n.input = '{"reply": "@{provide-analysis}.formatted_result"}'
                    """)
                    logger.info("Updated show-analysis step")
                else:
                    # Create the show-analysis step
                    session.run("""
                    CREATE (show_analysis:STEP {
                      id: 'show-analysis',
                      description: 'Display the formatted analysis to the user',
                      function: 'reply.reply',
                      input: '{"reply": "@{provide-analysis}.formatted_result"}'
                    })
                    """)
                    logger.info("Created show-analysis step")
                    
                    # Update the workflow connections
                    try:
                        session.run("""
                        MATCH (provide:STEP {id: 'provide-analysis'})
                        MATCH (show:STEP {id: 'show-analysis'})
                        MATCH (continue:STEP {id: 'continue-question'})
                        OPTIONAL MATCH (provide)-[r:NEXT]->(continue)
                        DELETE r
                        MERGE (provide)-[:NEXT {id: 'to-show'}]->(show)
                        MERGE (show)-[:NEXT {id: 'to-continue'}]->(continue)
                        """)
                        logger.info("Updated workflow connections")
                    except Exception as e:
                        logger.error(f"Error updating connections: {e}")
                
                # Fix the if-yes condition to properly loop back
                try:
                    session.run("""
                    MATCH (continue:STEP {id: 'continue-question'})
                    MATCH (input:STEP {id: 'get-input'})
                    MATCH (continue)-[r:NEXT {id: 'if-yes'}]->(input)
                    SET r.function = 'condition.equals',
                        r.input = '{"value": "@{continue-question}.response", "equals": "yes"}'
                    """)
                    logger.info("Fixed if-yes condition")
                except Exception as e:
                    logger.error(f"Error fixing if-yes condition: {e}")
                
                # Fix the if-no condition
                try:
                    session.run("""
                    MATCH (continue:STEP {id: 'continue-question'})
                    MATCH (end:STEP {id: 'end'})
                    MATCH (continue)-[r:NEXT {id: 'if-no'}]->(end)
                    SET r.function = 'condition.not_equals',
                        r.input = '{"value": "@{continue-question}.response", "equals": "yes"}'
                    """)
                    logger.info("Fixed if-no condition")
                except Exception as e:
                    logger.error(f"Error fixing if-no condition: {e}")
            else:
                logger.error("Could not find workflow root node")
    
    except Exception as e:
        logger.error(f"Error updating workflow: {e}")
    finally:
        driver.close()

if __name__ == '__main__':
    update_workflow() 