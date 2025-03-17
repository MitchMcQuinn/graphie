"""
utils/resolve_variable.py
----------------
This module handles resolving variable references from SESSION nodes.

Purpose:
    Provides functionality to extract and resolve variable references 
    in the format @{SESSION_ID}.STEP_ID.key[index]|default.
"""

import re
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

def resolve_variable(driver, session_id, variable_ref):
    """
    Resolve a variable reference like @{SESSION_ID}.step_id.key or @{step_id.key}
    
    Args:
        driver: Neo4j driver 
        session_id: The session ID to resolve variables for
        variable_ref: The variable reference string
        
    Returns:
        The resolved value
    """
    # If the reference doesn't start with @{, it's already a direct value
    if not variable_ref.startswith('@{'):
        return variable_ref
    
    # Extract the reference part
    match = re.match(r'@\{([^}]+)\}', variable_ref)
    if not match:
        logger.warning(f"Malformed variable reference: {variable_ref}")
        return variable_ref
    
    ref = match.group(1)
    
    # The reference may have one of these forms:
    # 1. step_id.key - simple reference to a step output
    # 2. SESSION_ID.step_id.key - explicit session reference
    
    # Handle SESSION_ID references
    if ref.startswith('SESSION_ID.'):
        # Replace SESSION_ID with the actual session_id
        ref = ref.replace('SESSION_ID', session_id, 1)
        logger.info(f"Resolved SESSION_ID reference to: {ref}")
    
    # Split the reference by dots
    parts = ref.split('.')
    
    # If it starts with a session ID (UUID-like), extract it
    target_session_id = None
    step_id = None
    key = None
    
    if len(parts) == 3 and is_uuid_like(parts[0]):
        # Format: session_id.step_id.key
        target_session_id = parts[0]
        step_id = parts[1]
        key = parts[2]
    elif len(parts) == 2:
        # Format: step_id.key
        target_session_id = session_id
        step_id = parts[0]
        key = parts[1]
    else:
        logger.warning(f"Unexpected variable reference format: {ref}")
        return variable_ref
    
    # Check if the session ID matches the provided session ID
    if target_session_id != session_id:
        logger.warning(f"Session ID mismatch: {target_session_id} != {session_id}")
        # Use the original session_id to avoid cross-session references
        target_session_id = session_id
    
    # Look up the value in the SESSION node's memory
    try:
        with driver.session() as db_session:
            result = db_session.run("""
                MATCH (s:SESSION {id: $session_id})
                RETURN s.memory as memory
            """, session_id=target_session_id)
            
            record = result.single()
            if not record:
                logger.warning(f"SESSION node with id {target_session_id} not found")
                return variable_ref
            
            # Parse memory
            try:
                memory_str = record['memory'] if record['memory'] else "{}"
                memory = json.loads(memory_str)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid memory JSON for session {target_session_id}")
                return variable_ref
            
            # Find the step outputs
            step_outputs = memory.get(step_id, [])
            if not step_outputs:
                logger.warning(f"No outputs found for step {step_id} in session {target_session_id}")
                return variable_ref
            
            # Get the latest output for the step
            latest_output = step_outputs[-1]
            
            # Extract the key from the output
            if isinstance(latest_output, dict) and key in latest_output:
                return latest_output[key]
            else:
                logger.warning(f"Key {key} not found in output for step {step_id} in session {target_session_id}")
                return variable_ref
            
    except Exception as e:
        logger.error(f"Error resolving variable {variable_ref}: {str(e)}")
        return variable_ref

def process_variables(driver, session_id, data):
    """
    Process all variable references in a data structure
    
    Args:
        driver: Neo4j driver
        session_id: The session ID
        data: The data to process (dict, list, or primitive)
        
    Returns:
        The processed data with all variable references resolved
    """
    if isinstance(data, dict):
        return {k: process_variables(driver, session_id, v) for k, v in data.items()}
    elif isinstance(data, list):
        return [process_variables(driver, session_id, item) for item in data]
    elif isinstance(data, str) and '@{' in data:
        # Handle complete replacement vs. substring replacement
        if data.startswith('@{') and data.endswith('}'):
            # Complete replacement
            return resolve_variable(driver, session_id, data)
        else:
            # Substring replacement - find all variable references in the string
            def replace_var(match):
                var_ref = match.group(0)
                resolved = resolve_variable(driver, session_id, var_ref)
                if isinstance(resolved, (str, int, float, bool)):
                    return str(resolved)
                else:
                    # Can't embed complex objects in a string
                    logger.warning(f"Can't embed complex object in string: {var_ref}")
                    return var_ref
            
            pattern = r'@\{[^}]+\}'
            return re.sub(pattern, replace_var, data)
    else:
        return data

def is_uuid_like(s):
    """Check if a string looks like a UUID (8-4-4-4-12 format or similar)"""
    if not isinstance(s, str):
        return False
    return re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', s, re.IGNORECASE) is not None 