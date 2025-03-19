"""
core/session_manager.py
----------------
This script provides a centralized interface for interacting with session data stored in Neo4j. 
It encapsulates all the common operations related to creating, reading, updating, and managing SESSION nodes in the graph database.

This module serves as a critical abstraction layer between the application logic and the Neo4j database:
- Session State Management: It provides methods to create, retrieve, update, and check the existence of SESSION nodes.
- Memory Operations: It handles the storage and retrieval of step outputs in the session memory, maintaining the history of outputs through cycles.
- Chat History Management: It provides methods to get and update the chat history for a session.
- Error Handling: It records and retrieves errors that occur during workflow execution.
- Singleton Pattern: It implements a singleton pattern to ensure a single instance is shared across the application.

Purpose:
    Centralizes Neo4j session operations to reduce code duplication and
    simplify interactions with the session state.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Encapsulates operations for managing session state in Neo4j.
    """
    
    def __init__(self, driver):
        """
        Initialize the SessionManager.
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
    
    def get_memory(self, session_id: str) -> Dict[str, Any]:
        """
        Get the complete memory for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            dict: The session memory or empty dict if not found
        """
        try:
            with self.driver.session() as db_session:
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.memory as memory
                """, session_id=session_id)
                
                record = result.single()
                if not record:
                    logger.warning(f"Session {session_id} not found")
                    return {}
                
                try:
                    memory_str = record['memory'] if record['memory'] else "{}"
                    return json.loads(memory_str)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid memory JSON for session {session_id}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting session memory: {str(e)}")
            return {}
    
    def store_memory(self, session_id: str, step_id: str, output_data: Any, error: Optional[str] = None) -> Optional[int]:
        """
        Store output data in session memory.
        
        Args:
            session_id: The session ID
            step_id: The step ID
            output_data: The output data to store
            error: Optional error message
            
        Returns:
            int: The cycle number or None if error
        """
        try:
            with self.driver.session() as db_session:
                # Get current memory and errors
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.memory as memory, s.errors as errors
                """, session_id=session_id)
                
                record = result.single()
                if not record:
                    logger.error(f"SESSION node with id {session_id} not found")
                    return None
                
                # Parse memory and errors
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
                
                # Update SESSION node
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
    
    def get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get the chat history for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            list: The chat history or empty list if not found
        """
        try:
            with self.driver.session() as db_session:
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.chat_history as chat_history
                """, session_id=session_id)
                
                record = result.single()
                if not record:
                    return []
                
                try:
                    chat_history_str = record['chat_history'] if record['chat_history'] else "[]"
                    return json.loads(chat_history_str)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid chat history JSON for session {session_id}")
                    return []
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return []
    
    def add_user_message(self, session_id: str, message: str) -> bool:
        """
        Add a user message to chat history.
        
        Args:
            session_id: The session ID
            message: The user message
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current chat history
            chat_history = self.get_chat_history(session_id)
            
            # Add user message
            chat_history.append({
                'role': 'user',
                'content': message
            })
            
            # Update chat history
            with self.driver.session() as db_session:
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.chat_history = $chat_history
                """, session_id=session_id, chat_history=json.dumps(chat_history))
                
            logger.info(f"Added user message to chat history for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding user message to chat history: {str(e)}")
            return False
    
    def add_assistant_message(self, session_id: str, message: str) -> bool:
        """
        Add an assistant message to chat history.
        
        Args:
            session_id: The session ID
            message: The assistant message
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current chat history
            chat_history = self.get_chat_history(session_id)
            
            # Add assistant message
            chat_history.append({
                'role': 'assistant',
                'content': message
            })
            
            # Update chat history
            with self.driver.session() as db_session:
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.chat_history = $chat_history
                """, session_id=session_id, chat_history=json.dumps(chat_history))
                
            logger.info(f"Added assistant message to chat history for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding assistant message to chat history: {str(e)}")
            return False
    
    def set_session_status(self, session_id: str, status: str) -> bool:
        """
        Set the session status.
        
        Args:
            session_id: The session ID
            status: The new status ('active', 'awaiting_input', etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.driver.session() as db_session:
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.status = $status
                """, session_id=session_id, status=status)
                
            logger.info(f"Set status for session {session_id} to {status}")
            return True
        except Exception as e:
            logger.error(f"Error setting session status: {str(e)}")
            return False
    
    def set_next_steps(self, session_id: str, next_steps: List[str]) -> bool:
        """
        Set the next steps for a session.
        
        Args:
            session_id: The session ID
            next_steps: List of step IDs
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.driver.session() as db_session:
                db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    SET s.next_steps = $next_steps
                """, session_id=session_id, next_steps=next_steps)
                
            logger.info(f"Set next steps for session {session_id}: {next_steps}")
            return True
        except Exception as e:
            logger.error(f"Error setting next steps: {str(e)}")
            return False
    
    def get_step_output(self, session_id: str, step_id: str, key: Optional[str] = None) -> Any:
        """
        Get the latest output from a step.
        
        Args:
            session_id: The session ID
            step_id: The step ID
            key: Optional key within the output to return
            
        Returns:
            The step output, a specific key from the output, or None if not found
        """
        memory = self.get_memory(session_id)
        
        if step_id not in memory or not memory[step_id]:
            return None
        
        latest_output = memory[step_id][-1]
        
        if key is not None:
            return latest_output.get(key)
        
        return latest_output
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the full status of a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            dict: The session status information
        """
        try:
            with self.driver.session() as db_session:
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.status as status, s.next_steps as next_steps, 
                           s.memory as memory, s.errors as errors,
                           s.chat_history as chat_history
                """, session_id=session_id)
                
                record = result.single()
                if not record:
                    return {"error": f"Session {session_id} not found"}
                
                # Parse JSON strings
                try:
                    memory_str = record['memory'] if record['memory'] else "{}"
                    memory = json.loads(memory_str)
                except (json.JSONDecodeError, TypeError):
                    memory = {}
                    
                try:
                    errors_str = record['errors'] if record['errors'] else "[]"
                    errors = json.loads(errors_str)
                except (json.JSONDecodeError, TypeError):
                    errors = []
                    
                try:
                    chat_history_str = record['chat_history'] if record['chat_history'] else "[]"
                    chat_history = json.loads(chat_history_str)
                except (json.JSONDecodeError, TypeError):
                    chat_history = []
                
                return {
                    "status": record['status'],
                    "next_steps": record['next_steps'],
                    "memory": memory,
                    "errors": errors,
                    "chat_history": chat_history
                }
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return {"error": str(e)}
    
    def create_session(self, session_id: str) -> bool:
        """
        Create a new session.
        
        Args:
            session_id: The session ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.driver.session() as db_session:
                # Create the SESSION node
                db_session.run("""
                    CREATE (s:SESSION {
                        id: $session_id,
                        memory: $memory,
                        next_steps: $next_steps,
                        created_at: datetime(),
                        status: 'active',
                        errors: $errors,
                        chat_history: $chat_history
                    })
                """, 
                session_id=session_id,
                memory='{}',  # Empty JSON object
                errors='[]',  # Empty JSON array
                chat_history='[]',  # Empty JSON array
                next_steps=['root']  # Initial next steps
                )
                
                logger.info(f"Created new SESSION node with ID: {session_id}")
                return True
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return False
    
    def has_session(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: The session ID
            
        Returns:
            bool: True if the session exists, False otherwise
        """
        try:
            with self.driver.session() as db_session:
                result = db_session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN count(s) as count
                """, session_id=session_id)
                
                record = result.single()
                return record and record['count'] > 0
        except Exception as e:
            logger.error(f"Error checking if session exists: {str(e)}")
            return False

# Global session manager instance
_session_manager = None

def get_session_manager(driver=None):
    """
    Get a singleton SessionManager instance.
    
    Args:
        driver: Optional Neo4j driver instance. If not provided, gets one.
        
    Returns:
        SessionManager instance or None if no driver could be obtained
    """
    global _session_manager
    
    # Return existing session manager if already initialized
    if _session_manager is not None:
        return _session_manager
    
    # If no driver provided, try to get one
    if driver is None:
        try:
            from .database import get_neo4j_driver
            driver = get_neo4j_driver()
        except ImportError:
            logger.error("Could not import get_neo4j_driver from core.database")
            return None
            
    if not driver:
        logger.error("No Neo4j driver provided and could not create one")
        return None
    
    # Create new session manager
    _session_manager = SessionManager(driver)
    return _session_manager 