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
            # Update provide-analysis node to use fixed_reply instead of format_analysis
            result = session.run(
                """
                MATCH (n:STEP {id: 'provide-analysis'})
                WHERE n.function = 'utils.format_analysis.format_analysis'
                SET n.function = 'utils.reply.reply',
                    n.input = '{"reply": "Analysis results: Animal: @{extract-animal}.animals, Sentiment: @{analyze-input}.sentiment"}'
                RETURN n
                """
            )
            
            for node in result:
                logger.info(f"Updated {node['id']} to use reply instead of format_analysis")
            
            # Update show-analysis node to use fixed_reply with direct variable references
            result = session.run(
                """
                MATCH (n:STEP {id: 'show-analysis'})
                SET n.function = 'utils.reply.reply',
                    n.input = '{"reply": "Analysis complete. Animal: @{extract-animal}.animals, Sentiment: @{analyze-input}.sentiment"}'
                RETURN n
                """
            )
            
            for node in result:
                logger.info(f"Updated {node['id']} to use reply and direct variable references")
            
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