"""
update_workflow.py
----------------
This script updates existing workflow nodes in Neo4j to be compatible
with the new graph-based session management architecture.

It replaces legacy variable references (@{response}, @{last_reply}, etc.)
with the new format (@{SESSION_ID}.step-id.property[index]|default) using
template variables that will be resolved at runtime.
"""

import os
import json
import logging
from dotenv import load_dotenv
from engine import get_neo4j_driver

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

def update_input_variables(input_str):
    """
    Update variable references in input JSON strings
    
    Replaces:
    - @{response} → @{SESSION_ID}.get-question.response
    - @{last_reply} → @{SESSION_ID}.provide-answer.reply
    - other legacy variables as needed
    
    Args:
        input_str: The input JSON string to update
        
    Returns:
        Updated input string with new variable references
    """
    # First parse the JSON to avoid breaking it
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse input JSON: {input_str}")
        return input_str
    
    # Function to recursively update variables in strings
    def update_vars(obj):
        if isinstance(obj, str):
            # Replace legacy variable references
            updated = obj
            # Replace user response reference
            updated = updated.replace('@{response}', '@{SESSION_ID}.get-question.response')
            
            # Replace last_reply references
            updated = updated.replace('@{last_reply}', '@{SESSION_ID}.provide-answer.reply')
            
            # Add more replacements as needed for other variable types
            
            return updated
        elif isinstance(obj, dict):
            return {k: update_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [update_vars(item) for item in obj]
        else:
            return obj
    
    # Update variables in the JSON
    updated_data = update_vars(input_data)
    
    # Convert back to JSON string with consistent formatting
    return json.dumps(updated_data, indent=2)

def update_workflow():
    """
    Update all workflow nodes in Neo4j to use the new variable reference format
    """
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Failed to connect to Neo4j")
        return
    
    try:
        with driver.session() as session:
            # First, get all STEP nodes with input properties
            result = session.run("""
                MATCH (s:STEP)
                WHERE s.input IS NOT NULL
                RETURN s.id as id, s.input as input, s.function as function
            """)
            
            steps_to_update = []
            for record in result:
                step_id = record['id']
                input_str = record['input']
                function = record['function']
                
                if '@{' in input_str:
                    logger.info(f"Found variable references in step {step_id} (function: {function})")
                    steps_to_update.append({
                        'id': step_id,
                        'original_input': input_str,
                        'updated_input': update_input_variables(input_str)
                    })
            
            logger.info(f"Found {len(steps_to_update)} steps to update")
            
            # Update each step with new variable references
            for step in steps_to_update:
                logger.info(f"Updating step {step['id']}...")
                
                if step['original_input'] != step['updated_input']:
                    session.run("""
                        MATCH (s:STEP {id: $id})
                        SET s.input = $input,
                            s.original_input = $original_input,
                            s.updated_for_session_nodes = true
                    """, id=step['id'], input=step['updated_input'], original_input=step['original_input'])
                    
                    logger.info(f"Updated step {step['id']}")
                    logger.info(f"Original: {step['original_input']}")
                    logger.info(f"Updated: {step['updated_input']}")
                else:
                    logger.info(f"No changes needed for step {step['id']}")
            
            logger.info("Workflow update complete")
            
            # Return summary of changes
            return {
                'steps_updated': len([s for s in steps_to_update if s['original_input'] != s['updated_input']]),
                'steps_unchanged': len([s for s in steps_to_update if s['original_input'] == s['updated_input']]),
                'total_steps': len(steps_to_update)
            }
    
    except Exception as e:
        logger.error(f"Error updating workflow: {str(e)}")
        return {'error': str(e)}

def print_workflow():
    """Print the current workflow structure for verification"""
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Failed to connect to Neo4j")
        return
    
    try:
        with driver.session() as session:
            # Get all STEP nodes
            nodes_result = session.run("""
                MATCH (s:STEP)
                RETURN s.id as id, s.function as function, s.input as input, 
                       s.updated_for_session_nodes as updated
                ORDER BY s.id
            """)
            
            nodes = [dict(record) for record in nodes_result]
            
            # Get all relationships
            rels_result = session.run("""
                MATCH (source:STEP)-[r:NEXT]->(target:STEP)
                RETURN source.id as source, target.id as target, 
                       properties(r) as properties
            """)
            
            relationships = [dict(record) for record in rels_result]
            
            # Print workflow information
            print("\n=== Current Workflow Structure ===")
            print(f"Total nodes: {len(nodes)}")
            print(f"Total relationships: {len(relationships)}")
            print("\nNodes:")
            for node in nodes:
                print(f"  - {node['id']} (function: {node['function']})")
                print(f"    Updated for session nodes: {node.get('updated', False)}")
            
            print("\nRelationships:")
            for rel in relationships:
                props = ", ".join([f"{k}: {v}" for k, v in rel['properties'].items()]) if rel['properties'] else ""
                print(f"  - {rel['source']} → {rel['target']} {props}")
            
            # Print sample updated input
            print("\nSample Updated Input:")
            for node in nodes:
                if node.get('input') and node.get('updated', False):
                    print(f"\nStep: {node['id']}")
                    print(f"Input:\n{node['input']}")
                    break
    
    except Exception as e:
        logger.error(f"Error printing workflow: {str(e)}")

if __name__ == "__main__":
    print("Updating workflow for compatibility with graph-based session management...")
    result = update_workflow()
    print(f"Update complete: {result}")
    print_workflow() 