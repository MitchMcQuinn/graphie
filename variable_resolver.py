"""
variable_resolver.py
------------------
This module provides functions for replacing SESSION_ID template
placeholders at runtime when processing variable references.

Purpose:
    Handles the transition to new variable reference format by resolving
    templates like @{SESSION_ID}.step-id.property to actual session IDs.
"""

import re
import logging
from utils.resolve_variable import resolve_variable, process_variables
from utils.database import get_neo4j_driver

# Set up logging
logger = logging.getLogger(__name__)

def resolve_session_id_templates(driver, session_id, data):
    """
    Replace SESSION_ID templates with actual session IDs in variable references.
    Works with the new variable reference system while providing backward
    compatibility for transitioning to graph-based sessions.
    
    Args:
        driver: Neo4j driver instance
        session_id: Current session ID
        data: Data (str, dict, list) containing variable references
        
    Returns:
        Data with SESSION_ID templates replaced by actual session IDs
    """
    if isinstance(data, str):
        # Check if this is a variable reference with SESSION_ID template
        if '@{SESSION_ID}.' in data:
            updated = data.replace('@{SESSION_ID}.', f'@{{{session_id}}}.')
            logger.debug(f"Replaced SESSION_ID template: {data} -> {updated}")
            return updated
        # Check for legacy variable references (backward compatibility)
        elif '@{' in data and not re.search(r'@\{[0-9a-f-]+\}', data):
            # This is a legacy reference without session ID - handle according to type
            if data == '@{response}':
                return f'@{{{session_id}}}.get-question.response'
            elif data == '@{last_reply}':
                return f'@{{{session_id}}}.provide-answer.reply'
            # Add more legacy variable mappings as needed
            
            # If no specific mapping, leave as is (handled by legacy variable resolution)
            return data
        else:
            return data
    elif isinstance(data, dict):
        return {k: resolve_session_id_templates(driver, session_id, v) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_session_id_templates(driver, session_id, item) for item in data]
    else:
        return data

def process_step_input(driver, session_id, input_data):
    """
    Process input data for a workflow step, handling both template variables
    and actual variable resolution.
    
    Args:
        driver: Neo4j driver instance
        session_id: Current session ID
        input_data: Input data (string, dict, or primitive) to process
        
    Returns:
        Processed input data with variables resolved
    """
    # First replace SESSION_ID templates with actual session ID
    data_with_session_id = resolve_session_id_templates(driver, session_id, input_data)
    
    # Then resolve the actual variable references
    resolved_data = process_variables(driver, session_id, data_with_session_id)
    
    return resolved_data

# Patch the graph_engine's _process_step method to use our enhanced variable resolution
def patch_graph_engine():
    """
    Patch the GraphWorkflowEngine to use our enhanced variable resolution.
    This is a temporary fix during the transition period.
    """
    try:
        from graph_engine import get_graph_workflow_engine
        engine = get_graph_workflow_engine()
        original_process_step = engine._process_step
        
        def patched_process_step(session_id, step_info):
            # Parse input JSON and process variables with our enhanced resolution
            input_data = {}
            if 'input' in step_info and step_info['input']:
                try:
                    import json
                    input_data = json.loads(step_info['input'])
                    
                    # Process variable references with SESSION_ID template support
                    input_data = process_step_input(engine.driver, session_id, input_data)
                except json.JSONDecodeError as e:
                    error_msg = f"Error parsing input JSON for step {step_info.get('id', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    engine._record_error(session_id, step_info.get('id', 'unknown'), error_msg)
                    return None
                    
            # Execute the rest of the original method with our processed input
            step_info_copy = step_info.copy()
            step_info_copy['processed_input'] = input_data
            return original_process_step(session_id, step_info_copy)
        
        # Apply the patch
        engine._process_step = patched_process_step
        logger.info("Successfully patched GraphWorkflowEngine._process_step with enhanced variable resolution")
        return True
    except Exception as e:
        logger.error(f"Failed to patch GraphWorkflowEngine: {str(e)}")
        return False

if __name__ == "__main__":
    # Set up logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    print("Testing variable resolver...")
    
    # Test with some sample data
    test_data = {
        "text": "@{SESSION_ID}.get-question.response",
        "complex": {
            "nested": "@{SESSION_ID}.provide-answer.reply"
        },
        "legacy": "@{response}"
    }
    
    driver = get_neo4j_driver()
    
    if driver:
        test_session_id = "test-session-123"
        resolved = resolve_session_id_templates(driver, test_session_id, test_data)
        print(f"Original: {test_data}")
        print(f"Resolved: {resolved}")
        
        # Apply the patch
        patched = patch_graph_engine()
        print(f"Applied engine patch: {patched}")
    else:
        print("Could not connect to Neo4j for testing") 