import os
import logging
import json
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
    logger.error("Neo4j connection details are missing. Please set NEO4J_URL, NEO4J_USERNAME, and NEO4J_PASSWORD in .env.local")
    exit(1)

try:
    from neo4j import GraphDatabase
except ImportError:
    logger.error("Neo4j Python driver not installed. Please run 'pip install neo4j'")
    exit(1)

def update_workflow():
    """
    Update the workflow to use fixed implementations of key functions
    
    This script:
    1. Updates node functions to use the fixed_reply module
    2. Ensures connections between key nodes in the workflow
    3. Adds clear logging to help with debugging
    """
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        logger.info("Connected to Neo4j successfully")
        
        with driver.session() as session:
            # Update all reply/respond functions to use the fixed implementations
            result = session.run(
                """
                MATCH (n:STEP)
                WHERE n.function = 'reply.reply' OR n.function = 'reply.respond'
                SET n.function = CASE 
                    WHEN n.function = 'reply.reply' THEN 'fixed_reply.fixed_reply'
                    WHEN n.function = 'reply.respond' THEN 'fixed_reply.fixed_respond'
                    ELSE n.function
                END
                RETURN COUNT(n) as updatedNodes
                """
            )
            record = result.single()
            logger.info(f"Updated {record['updatedNodes']} nodes to use fixed reply functions")
            
            # Make sure root-2 node exists (if it's not already there)
            result = session.run(
                """
                MERGE (root:STEP {id: 'root-2'})
                ON CREATE SET 
                    root.description = 'Root node for the workflow',
                    root.function = 'fixed_reply.fixed_reply',
                    root.input = '{"reply": "Hello! I am your assistant. How can I help you today?"}'
                RETURN root
                """
            )
            logger.info("Ensured root-2 node exists in the workflow")
            
            # Make sure get-input node exists
            result = session.run(
                """
                MERGE (n:STEP {id: 'get-input'})
                ON CREATE SET 
                    n.description = 'Get input from the user',
                    n.function = 'request.request',
                    n.input = '{"statement": "How can I help you today?"}'
                RETURN n
                """
            )
            logger.info("Ensured get-input node exists")
            
            # Add connection from root-2 to get-input if it doesn't exist
            result = session.run(
                """
                MATCH (root:STEP {id: 'root-2'}), (input:STEP {id: 'get-input'})
                MERGE (root)-[r:NEXT]->(input)
                ON CREATE SET r.function = 'condition.true', r.input = '{}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info(f"Ensured connection from root-2 to get-input")
            
            # Make sure extract-animal exists
            result = session.run(
                """
                MERGE (n:STEP {id: 'extract-animal'})
                ON CREATE SET 
                    n.description = 'Extract animal name from user input',
                    n.function = 'analyze.analyze_input',
                    n.input = '{"function": "extract_animal_names", "input": "@{get-input}.user_input"}'
                ON MATCH SET 
                    n.function = 'analyze.analyze_input',
                    n.input = '{"function": "extract_animal_names", "input": "@{get-input}.user_input"}'
                RETURN n
                """
            )
            logger.info("Ensured extract-animal node exists")
            
            # Make sure analyze-input exists
            result = session.run(
                """
                MERGE (n:STEP {id: 'analyze-input'})
                ON CREATE SET 
                    n.description = 'Analyze user input for sentiment',
                    n.function = 'analyze.analyze_input',
                    n.input = '{"function": "sentiment_analysis", "input": "@{get-input}.user_input"}'
                ON MATCH SET 
                    n.function = 'analyze.analyze_input',
                    n.input = '{"function": "sentiment_analysis", "input": "@{get-input}.user_input"}'
                RETURN n
                """
            )
            logger.info("Ensured analyze-input node exists")
            
            # Add connections from get-input to both extract-animal and analyze-input
            result = session.run(
                """
                MATCH (input:STEP {id: 'get-input'}), (animal:STEP {id: 'extract-animal'})
                MERGE (input)-[r:NEXT]->(animal)
                ON CREATE SET r.function = 'condition.true', r.input = '{}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info("Ensured connection from get-input to extract-animal")
            
            result = session.run(
                """
                MATCH (input:STEP {id: 'get-input'}), (analyze:STEP {id: 'analyze-input'})
                MERGE (input)-[r:NEXT]->(analyze)
                ON CREATE SET r.function = 'condition.true', r.input = '{}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info("Ensured connection from get-input to analyze-input")
            
            # Make sure return-animal exists
            result = session.run(
                """
                MERGE (n:STEP {id: 'return-animal'})
                ON CREATE SET 
                    n.description = 'Reply with extracted animal name',
                    n.function = 'fixed_reply.fixed_reply',
                    n.input = '{"reply": "I notice you mentioned @{extract-animal}.animals. @{analyze-input}.sentiment Would you like to know more about this animal?"}'
                ON MATCH SET 
                    n.function = 'fixed_reply.fixed_reply',
                    n.input = '{"reply": "I notice you mentioned @{extract-animal}.animals. @{analyze-input}.sentiment Would you like to know more about this animal?"}'
                RETURN n
                """
            )
            logger.info("Ensured return-animal node exists")
            
            # Add connection from extract-animal to return-animal
            result = session.run(
                """
                MATCH (animal:STEP {id: 'extract-animal'}), (return:STEP {id: 'return-animal'})
                MERGE (animal)-[r:NEXT]->(return)
                ON CREATE SET r.function = 'condition.true', r.input = '{}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info("Ensured connection from extract-animal to return-animal")
            
            # Make sure continue-question exists
            result = session.run(
                """
                MERGE (n:STEP {id: 'continue-question'})
                ON CREATE SET 
                    n.description = 'Ask if user wants to continue',
                    n.function = 'request.request',
                    n.input = '{"statement": "Would you like to ask me another question?"}'
                RETURN n
                """
            )
            logger.info("Ensured continue-question node exists")
            
            # Add connection from return-animal to continue-question
            result = session.run(
                """
                MATCH (return:STEP {id: 'return-animal'}), (cont:STEP {id: 'continue-question'})
                MERGE (return)-[r:NEXT]->(cont)
                ON CREATE SET r.function = 'condition.true', r.input = '{}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info("Ensured connection from return-animal to continue-question")
            
            # Make sure continue-yes and continue-no exist
            result = session.run(
                """
                MERGE (n:STEP {id: 'continue-yes'})
                ON CREATE SET 
                    n.description = 'User wants to continue',
                    n.function = 'fixed_reply.fixed_reply',
                    n.input = '{"reply": "Great! How can I help you?"}'
                RETURN n
                """
            )
            logger.info("Ensured continue-yes node exists")
            
            result = session.run(
                """
                MERGE (n:STEP {id: 'continue-no'})
                ON CREATE SET 
                    n.description = 'User does not want to continue',
                    n.function = 'fixed_reply.fixed_reply',
                    n.input = '{"reply": "Thank you for chatting with me today. Goodbye!"}'
                RETURN n
                """
            )
            logger.info("Ensured continue-no node exists")
            
            # Add connections from continue-question to both yes and no options
            result = session.run(
                """
                MATCH (q:STEP {id: 'continue-question'}), (yes:STEP {id: 'continue-yes'})
                MERGE (q)-[r:NEXT]->(yes)
                ON CREATE SET r.function = 'condition.contains', 
                             r.input = '{"value": "@{continue-question}.user_input", "substring": "yes"}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info("Ensured connection from continue-question to continue-yes")
            
            result = session.run(
                """
                MATCH (q:STEP {id: 'continue-question'}), (no:STEP {id: 'continue-no'})
                MERGE (q)-[r:NEXT]->(no)
                ON CREATE SET r.function = 'condition.contains', 
                             r.input = '{"value": "@{continue-question}.user_input", "substring": "no"}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info("Ensured connection from continue-question to continue-no")
            
            # Add connection from continue-yes back to get-input to create a loop
            result = session.run(
                """
                MATCH (yes:STEP {id: 'continue-yes'}), (input:STEP {id: 'get-input'})
                MERGE (yes)-[r:NEXT]->(input)
                ON CREATE SET r.function = 'condition.true', r.input = '{}'
                RETURN COUNT(r) as relationships
                """
            )
            logger.info("Ensured connection from continue-yes back to get-input")
            
            # Get stats about workflow
            result = session.run(
                """
                MATCH (n:STEP)
                RETURN COUNT(n) as nodeCount
                """
            )
            node_count = result.single()['nodeCount']
            
            result = session.run(
                """
                MATCH ()-[r:NEXT]->()
                RETURN COUNT(r) as relCount
                """
            )
            rel_count = result.single()['relCount']
            
            logger.info(f"Workflow now has {node_count} nodes and {rel_count} relationships")
            
        # Close the Neo4j connection
        driver.close()
        logger.info("Neo4j connection closed")
        
    except Exception as e:
        logger.error(f"Error updating workflow: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting workflow update for fixed engine implementation")
    update_workflow()
    logger.info("Workflow update completed") 