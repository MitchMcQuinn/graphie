#!/usr/bin/env python
"""
Diagnostic script to test variable resolution functionality
"""

import logging
import sys
import os
from dotenv import load_dotenv

# Set up logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('variable_test')

# Load environment variables
load_dotenv('.env.local')

def main():
    """Main test function"""
    logger.info("Starting variable resolution test")
    
    # Import after logging setup
    from engine import get_neo4j_driver
    from utils.session_manager import get_session_manager
    from utils.resolve_variable import resolve_variable, process_variables

    # Connect to Neo4j
    driver = get_neo4j_driver()
    if not driver:
        logger.error("Failed to connect to Neo4j")
        return
    
    # Get the session manager
    session_manager = get_session_manager(driver)
    if not session_manager:
        logger.error("Failed to get session manager")
        return

    # Check for provided session ID or use a hardcoded one for testing
    if len(sys.argv) > 1:
        test_session_id = sys.argv[1]
        logger.info(f"Using provided session ID: {test_session_id}")
    else:
        # Use the most recent session ID from the logs
        logger.info("No session ID provided, using hardcoded test session ID")
        test_session_id = "3670542d-4856-41e6-9541-312f0c1f27b9"
    
    # Check if the session exists
    if not session_manager.has_session(test_session_id):
        logger.error(f"Session {test_session_id} does not exist")
        return
    
    # Test direct session memory access
    session_status = session_manager.get_session_status(test_session_id)
    logger.info(f"Session status: {session_status['status']}")
    logger.info(f"Session memory keys: {list(session_status['memory'].keys())}")
    
    # Try to access generate-answer outputs
    if 'generate-answer' in session_status['memory']:
        outputs = session_status['memory']['generate-answer']
        logger.info(f"Found {len(outputs)} outputs for generate-answer")
        for i, output in enumerate(outputs):
            logger.info(f"Output {i} keys: {list(output.keys())}")
            if 'response' in output:
                logger.info(f"Response value for output {i}: {output['response'][:100]}...")
    else:
        logger.warning("No generate-answer outputs found")
    
    # Test variable resolution directly 
    variable_to_test = f"@{{SESSION_ID}}.generate-answer.response"
    logger.info(f"Testing variable resolution for: {variable_to_test}")
    
    # Log each step of the resolution process
    logger.info("Step 1: Replace SESSION_ID")
    var_with_id = variable_to_test.replace("SESSION_ID", test_session_id)
    logger.info(f"After SESSION_ID replacement: {var_with_id}")
    
    logger.info("Step 2: Extract parts")
    parts = var_with_id.replace("@{", "").replace("}", "").split(".")
    logger.info(f"Parts: {parts}")
    
    logger.info("Step 3: Get value directly from session manager")
    if len(parts) >= 3:
        session_id = parts[0]
        step_id = parts[1]
        key = parts[2]
        
        logger.info(f"Looking up session_id={session_id}, step_id={step_id}, key={key}")
        
        # Get the memory first
        memory = session_manager.get_memory(session_id)
        logger.info(f"Memory keys: {list(memory.keys())}")
        
        # Check if the step_id exists in memory
        if step_id in memory:
            logger.info(f"Found step_id={step_id} in memory")
            step_outputs = memory[step_id]
            logger.info(f"Step outputs count: {len(step_outputs)}")
            
            # Get the latest output
            if step_outputs:
                latest_output = step_outputs[-1]
                logger.info(f"Latest output keys: {list(latest_output.keys())}")
                
                # Check if the key exists in the latest output
                if key in latest_output:
                    logger.info(f"Found key={key} in latest output")
                    value = latest_output[key]
                    logger.info(f"Value: {value[:100]}..." if isinstance(value, str) and len(value) > 100 else f"Value: {value}")
                else:
                    logger.error(f"Key {key} not found in latest output")
            else:
                logger.error(f"No outputs found for step_id={step_id}")
        else:
            logger.error(f"Step ID {step_id} not found in memory")
            
        # Now try the get_step_output method
        direct_value = session_manager.get_step_output(session_id, step_id, key)
        logger.info(f"Direct value type: {type(direct_value)}")
        logger.info(f"Direct value: {direct_value[:100]}..." if isinstance(direct_value, str) and len(direct_value) > 100 else f"Direct value: {direct_value}")
    
    logger.info("Step 4: Full variable resolution attempt")
    resolved_value = resolve_variable(driver, test_session_id, variable_to_test)
    logger.info(f"Resolved value type: {type(resolved_value)}")
    logger.info(f"Resolved value: {resolved_value[:100]}..." if isinstance(resolved_value, str) and len(resolved_value) > 100 else f"Resolved value: {resolved_value}")
    
    # Try also with the session ID directly in the variable
    direct_variable = f"@{{{test_session_id}}}.generate-answer.response"
    logger.info(f"Testing direct session ID variable: {direct_variable}")
    resolved_direct = resolve_variable(driver, test_session_id, direct_variable)
    logger.info(f"Resolved direct type: {type(resolved_direct)}")
    logger.info(f"Resolved direct: {resolved_direct[:100]}..." if isinstance(resolved_direct, str) and len(resolved_direct) > 100 else f"Resolved direct: {resolved_direct}")
    
    # Test the resolution using process_variables
    input_data = {'response': variable_to_test}
    logger.info(f"Testing process_variables with: {input_data}")
    processed_data = process_variables(driver, test_session_id, input_data)
    logger.info(f"Processed data: {processed_data}")
    
    logger.info("Test complete")

if __name__ == "__main__":
    main() 