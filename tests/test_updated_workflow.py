"""
test_updated_workflow.py
----------------------
This script tests the updated workflow with the new graph-based session management.
It creates a test session and executes a partial workflow to verify variable resolution.
"""

import uuid
import json
import logging
from datetime import datetime
from engine import get_neo4j_driver
from variable_resolver import resolve_session_id_templates

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_session(driver):
    """Create a test SESSION node with a unique ID"""
    session_id = str(uuid.uuid4())
    
    with driver.session() as session:
        session.run("""
            CREATE (s:SESSION {
                id: $id,
                memory: "{}",
                next_steps: ['root'],
                created_at: datetime(),
                status: 'active',
                errors: "[]",
                chat_history: "[]"
            })
        """, id=session_id)
        
        logger.info(f"Created test SESSION node with ID: {session_id}")
        return session_id

def store_test_response(driver, session_id, response_text):
    """Store a test response in the SESSION node memory for testing variable resolution"""
    with driver.session() as session:
        # Store response in memory for 'get-question' step
        # Convert complex objects to JSON strings for Neo4j
        memory_json = json.dumps({
            'get-question': [{
                'response': response_text,
                'timestamp': datetime.now().isoformat()
            }]
        })
        
        session.run("""
            MATCH (s:SESSION {id: $session_id})
            SET s.memory = $memory
        """, session_id=session_id, memory=memory_json)
        
        logger.info(f"Stored test response in SESSION {session_id}")

def simulate_step_execution(driver, session_id, step_id):
    """Simulate execution of a workflow step with variable resolution"""
    # First get the step information
    with driver.session() as session:
        step_result = session.run("""
            MATCH (s:STEP {id: $step_id})
            RETURN s.id as id, s.function as function, s.input as input
        """, step_id=step_id).single()
        
        if not step_result:
            logger.error(f"Step {step_id} not found")
            return None
        
        step_info = dict(step_result)
        logger.info(f"Executing step: {step_id} (function: {step_info['function']})")
        
        # Parse and process input with variable resolution
        if step_info.get('input'):
            try:
                input_data = json.loads(step_info['input']) 
                
                # First replace SESSION_ID templates
                resolved_data = resolve_session_id_templates(driver, session_id, input_data)
                
                # Then resolve actual variable references by looking up SESSION node memory
                # (simplified version of what would happen in the actual engine)
                memory_result = session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.memory as memory
                """, session_id=session_id).single()
                
                # Parse the memory JSON string
                memory_str = memory_result['memory'] if memory_result else "{}"
                try:
                    memory = json.loads(memory_str)
                except (json.JSONDecodeError, TypeError):
                    memory = {}
                
                # Simple variable resolution for testing
                def resolve_actual_refs(data, memory):
                    if isinstance(data, str) and data.startswith(f'@{{{session_id}}}'):
                        # Format is @{session_id}.step-id.property
                        try:
                            parts = data.split('.')
                            ref_step = parts[1]
                            ref_prop = parts[2]
                            
                            # Get the latest cycle
                            if ref_step in memory and len(memory[ref_step]) > 0:
                                latest = memory[ref_step][-1]
                                return latest.get(ref_prop, f"<undefined:{ref_prop}>")
                            else:
                                return f"<step not found: {ref_step}>"
                        except (IndexError, KeyError):
                            return f"<invalid reference: {data}>"
                    elif isinstance(data, dict):
                        return {k: resolve_actual_refs(v, memory) for k, v in data.items()}
                    elif isinstance(data, list):
                        return [resolve_actual_refs(item, memory) for item in data]
                    else:
                        return data
                
                final_data = resolve_actual_refs(resolved_data, memory)
                
                logger.info(f"Original input: {input_data}")
                logger.info(f"With SESSION_ID templates: {resolved_data}")
                logger.info(f"Final resolved data: {final_data}")
                
                # Save the processed results in the SESSION memory
                if step_id == 'generate-answer':
                    # Simulate storing output in the memory
                    # Get current memory and update it
                    current_memory = memory.copy()
                    
                    # Prepare the new memory entry
                    output_data = {
                        'reply': f"Response to: {final_data.get('user', 'unknown')}",
                        'key_points': ['Test point 1', 'Test point 2'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Update the memory structure
                    if step_id not in current_memory:
                        current_memory[step_id] = []
                    current_memory[step_id].append(output_data)
                    
                    # Convert to JSON string for Neo4j storage
                    memory_json = json.dumps(current_memory)
                    
                    # Update the SESSION node
                    session.run("""
                        MATCH (s:SESSION {id: $session_id})
                        SET s.memory = $memory
                    """, session_id=session_id, memory=memory_json)
                    
                    logger.info(f"Stored output for {step_id} in SESSION node")
                
                return final_data
                
            except json.JSONDecodeError:
                logger.error(f"Error parsing input JSON for step {step_id}")
                return None
        else:
            logger.info(f"Step {step_id} has no input data")
            return None

def test_workflow_execution():
    """Test the entire workflow execution chain with variable resolution"""
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Failed to connect to Neo4j")
        return
    
    try:
        # Create a test session
        session_id = create_test_session(driver)
        
        # Store test user response
        store_test_response(driver, session_id, "Tell me about graph databases")
        
        # Test the generate-answer step which should use the response variable
        logger.info("Testing generate-answer step...")
        generate_result = simulate_step_execution(driver, session_id, 'generate-answer')
        
        if generate_result:
            logger.info(f"Successfully processed generate-answer step")
            logger.info(f"Result: {generate_result}")
            
            # Now test the provide-answer step which should use the last_reply variable
            logger.info("\nTesting provide-answer step...")
            provide_result = simulate_step_execution(driver, session_id, 'provide-answer')
            
            if provide_result:
                logger.info(f"Successfully processed provide-answer step")
                logger.info(f"Result: {provide_result}")
            
        # Clean up test session
        with driver.session() as session:
            session.run("""
                MATCH (s:SESSION {id: $id})
                DELETE s
            """, id=session_id)
            
            logger.info(f"Cleaned up test SESSION node: {session_id}")
        
    except Exception as e:
        logger.error(f"Error testing workflow: {str(e)}")

if __name__ == "__main__":
    print("Testing updated workflow with variable resolution...")
    test_workflow_execution()
    print("Test complete") 