"""
utils/store_memory.py
----------------
This module handles storing function outputs in Neo4j SESSION nodes.

Purpose:
    Provides functionality to store utility outputs in the graph database
    for persistent state management across workflow steps.
"""

import json
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

def store_memory(driver, session_id, step_id, output_data, error=None):
    """
    Store a utility function's output in a SESSION node's memory
    
    Args:
        driver: Neo4j driver instance
        session_id: The unique ID of the session
        step_id: The ID of the step that generated the output
        output_data: The output data to store (will be converted to JSON)
        error: Optional error information to store
        
    Returns:
        The cycle number assigned to this output
    """
    try:
        with driver.session() as db_session:
            # Get current memory and errors
            result = db_session.run("""
                MATCH (s:SESSION {id: $session_id})
                RETURN s.memory as memory, s.errors as errors
            """, session_id=session_id)
            
            record = result.single()
            if not record:
                logger.error(f"SESSION node with id {session_id} not found")
                return None
            
            # Parse memory and errors from JSON strings
            try:
                memory_str = record['memory'] if record['memory'] else "{}"
                memory = json.loads(memory_str)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid memory JSON for session {session_id}, resetting")
                memory = {}
                
            try:
                errors_str = record['errors'] if record['errors'] else "[]"
                errors = json.loads(errors_str)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid errors JSON for session {session_id}, resetting")
                errors = []
            
            # Determine cycle number
            if step_id not in memory:
                memory[step_id] = []
            cycle_number = len(memory[step_id])
            
            # Store output
            memory[step_id].append(output_data)
            
            # Store error if provided
            if error:
                errors.append({
                    "step_id": step_id,
                    "cycle": cycle_number,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Update SESSION node with JSON strings
            db_session.run("""
                MATCH (s:SESSION {id: $session_id})
                SET s.memory = $memory, s.errors = $errors
            """, 
               session_id=session_id, 
               memory=json.dumps(memory), 
               errors=json.dumps(errors)
            )
            
            logger.info(f"Stored output for step {step_id} (cycle {cycle_number}) in session {session_id}")
            return cycle_number
            
    except Exception as e:
        logger.error(f"Error storing memory: {str(e)}")
        return None 