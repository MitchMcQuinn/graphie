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

def fix_show_analysis_node():
    """Fix the show-analysis node to correctly display sentiment analysis results"""
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        logger.info("Connected to Neo4j successfully")
        
        with driver.session() as session:
            # Update the provide-analysis node to properly use our variables
            result = session.run("""
                MATCH (n:STEP {id: 'provide-analysis'})
                SET n.function = 'utils.fixed_reply.fixed_reply',
                    n.input = '{"reply": "Based on your message, I detected the following: sentiment - @{analyze-input}.sentiment. Extracted animals: @{extract-animal}.animals."}'
                RETURN n.id as id
            """)
            
            updated = list(result)
            for node in updated:
                logger.info(f"Updated {node['id']} to use fixed_reply instead of format_analysis")
            
            # Update the show-analysis node to directly reference sentiment
            result = session.run("""
                MATCH (n:STEP {id: 'show-analysis'})
                SET n.function = 'utils.fixed_reply.fixed_reply',
                    n.input = '{"reply": "Here is what I found in your message: @{analyze-input}.sentiment You mentioned: @{extract-animal}.animals"}'
                RETURN n.id as id
            """)
            
            updated = list(result)
            for node in updated:
                logger.info(f"Updated {node['id']} to use fixed_reply and direct variable references")
            
        # Close the Neo4j connection
        driver.close()
        logger.info("Neo4j connection closed")
        logger.info("Show analysis node fixed successfully")
        
    except Exception as e:
        logger.error(f"Error fixing show analysis node: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting to fix show analysis node")
    fix_show_analysis_node()
    logger.info("Fix completed") 