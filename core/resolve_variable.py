"""
core/resolve_variable.py
----------------
This module plays a fundamental role in the graph-based workflow engine:
- Variable Reference Resolution: It resolves references in the format @{SESSION_ID}.STEP_ID.key|default to their actual values stored in Neo4j SESSION nodes.
- Data Passing Between Steps: It enables workflow steps to access outputs from previous steps, creating a connected data flow.
- Template Support: It handles the special SESSION_ID placeholder, allowing workflows to be designed with session-agnostic references that get replaced at runtime.
- Default Value Handling: It supports fallback values using the pipe syntax @{...}|default for cases where the referenced data doesn't exist.
- Complex Data Structure Processing: It can process nested dictionaries and lists, recursively resolving all variable references.

Purpose:
    Provides functionality to extract and resolve variable references 
    in the format @{SESSION_ID}.STEP_ID.key[index]|default.

    
"""

import re
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

def resolve_variable(driver, session_id, ref):
    """
    Resolve a variable reference from a SESSION node.
    
    Args:
        driver: Neo4j driver instance
        session_id: The session ID or SESSION_ID placeholder
        ref: The variable reference to resolve (format: @{session_id}.step_id.key or @{SESSION_ID}.step_id.key)
        
    Returns:
        The resolved value, or the original reference if not resolvable
    """
    # Early return for direct values (not variable references)
    if not isinstance(ref, str) or not ref.startswith('@{'):
        return ref
    
    # Log that we're resolving a variable
    logger.debug(f"Resolving variable reference: {ref}")
    
    # Extract the session ID, step ID, and key from the reference
    # Format: @{session_id}.step_id.key or @{SESSION_ID}.step_id.key
    
    # Check for default value (format: @{...}|default)
    default_value = None
    if '|' in ref:
        ref_parts = ref.split('|', 1)
        ref = ref_parts[0].strip()
        default_value = ref_parts[1].strip() if len(ref_parts) > 1 else None
    
    # Replace SESSION_ID placeholder with actual session ID
    if 'SESSION_ID' in ref:
        expanded_ref = ref.replace('SESSION_ID', session_id)
        logger.info(f"After SESSION_ID replacement: {expanded_ref}")
        ref = expanded_ref
    
    # Extract reference parts using regex for better handling
    match = re.match(r'@\{([^}]+)\}\.([^.]+)\.(.+)', ref)
    if not match:
        logger.warning(f"Invalid variable reference format: {ref}")
        return default_value if default_value is not None else ref
    
    # Extract components
    ref_session_id, step_id, key = match.groups()
    
    # Check if the referenced session exists
    try:
        with driver.session() as db_session:
            # First check if the session exists
            session_check = db_session.run("""
                MATCH (s:SESSION {id: $session_id})
                RETURN count(s) as count
            """, session_id=ref_session_id)
            
            session_exists = session_check.single()['count'] > 0
            
            if not session_exists:
                logger.warning(f"Session {ref_session_id} not found")
                return default_value if default_value is not None else ref
            
            # Get memory from the session
            result = db_session.run("""
                MATCH (s:SESSION {id: $session_id})
                RETURN s.memory
            """, session_id=ref_session_id)
            
            record = result.single()
            if not record:
                logger.warning(f"No memory found for session {ref_session_id}")
                return default_value if default_value is not None else ref
            
            # Parse memory from JSON
            try:
                memory_str = record[0] if record[0] else "{}"
                memory = json.loads(memory_str)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid memory JSON for session {ref_session_id}")
                return default_value if default_value is not None else ref
            
            # Check if the step is in memory
            if step_id not in memory:
                logger.warning(f"Step {step_id} not found in session memory")
                return default_value if default_value is not None else ref
            
            # Get the latest output for the step
            step_outputs = memory[step_id]
            if not step_outputs:
                logger.warning(f"No outputs for step {step_id}")
                return default_value if default_value is not None else ref
            
            latest_output = step_outputs[-1]
            
            # Check if the key exists in the output
            if key not in latest_output:
                logger.warning(f"Key {key} not found in output for step {step_id}")
                return default_value if default_value is not None else ref
            
            # Get the value
            value = latest_output[key]
            logger.info(f"Successfully resolved {ref} to value of type {type(value)}")
            
            return value
            
    except Exception as e:
        logger.error(f"Error resolving variable: {str(e)}")
        return default_value if default_value is not None else ref

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
        # Handle special case of SESSION_ID direct replacement
        if 'SESSION_ID' in data and not data.startswith('@{'):
            data = data.replace('SESSION_ID', session_id)
        
        # Handle complete replacement vs. substring replacement
        if data.startswith('@{') and data.endswith('}'):
            # Complete replacement
            return resolve_variable(driver, session_id, data)
        elif data.startswith('@{') and '}.' in data:
            # This is a reference like @{SESSION_ID}.step_id.key
            # We need to parse and resolve it as one unit
            parts = data.split('}.')
            if len(parts) == 2:
                prefix = parts[0] + '}'
                suffix = parts[1]
                
                # Try to resolve the combined reference
                combined_ref = prefix + '.' + suffix
                logger.debug(f"Processing combined reference: {combined_ref}")
                return resolve_variable(driver, session_id, combined_ref)
            
            # Fall back to the default substring replacement if parsing failed
            return re.sub(r'@\{[^}]+\}', lambda m: str(resolve_variable(driver, session_id, m.group(0))), data)
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
    # Simplified check - just make sure it's a valid session ID format
    # This is less strict to ensure we don't reject valid session IDs
    return re.match(r'^[0-9a-f\-]+$', s, re.IGNORECASE) is not None 