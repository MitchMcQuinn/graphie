from graph_engine import get_graph_workflow_engine
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_sessions():
    """Check all session states in the database"""
    try:
        # Get the graph workflow engine
        engine = get_graph_workflow_engine()
        
        # Check all sessions
        with engine.driver.session() as session:
            # Get all SESSION nodes
            result = session.run("""
                MATCH (s:SESSION) 
                RETURN s.id as id, s.status as status, s.next_steps as next_steps
            """)
            
            sessions = list(result)
            logger.info(f"Found {len(sessions)} sessions")
            
            for record in sessions:
                session_id = record["id"]
                status = record["status"]
                next_steps = record["next_steps"]
                
                logger.info(f"Session {session_id}: status={status}, next_steps={next_steps}")
                
                # Get more details for each session
                result = session.run("""
                    MATCH (s:SESSION {id: $session_id})
                    RETURN s.memory as memory, s.chat_history as chat_history, s.errors as errors
                """, session_id=session_id)
                
                detail = result.single()
                if detail:
                    # Parse memory to see what steps have been processed
                    try:
                        memory_str = detail["memory"] if detail["memory"] else "{}"
                        memory = json.loads(memory_str)
                        
                        logger.info(f"Session {session_id} memory contains {len(memory)} steps:")
                        for step_id, outputs in memory.items():
                            logger.info(f"  - {step_id}: {len(outputs)} outputs")
                            
                            # Show the last output of each step
                            if outputs:
                                last_output = outputs[-1]
                                if isinstance(last_output, dict):
                                    if 'response' in last_output:
                                        logger.info(f"    Last response: {last_output['response'][:50]}...")
                                    if 'reply' in last_output:
                                        logger.info(f"    Last reply: {last_output['reply'][:50]}...")
                    except Exception as e:
                        logger.error(f"Error parsing memory for session {session_id}: {str(e)}")
                    
                    # Check for errors
                    try:
                        errors_str = detail["errors"] if detail["errors"] else "[]"
                        errors = json.loads(errors_str)
                        
                        if errors:
                            logger.info(f"Session {session_id} has {len(errors)} errors:")
                            for error in errors:
                                logger.info(f"  - Step {error.get('step_id')}: {error.get('error')}")
                    except Exception as e:
                        logger.error(f"Error parsing errors for session {session_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Error checking sessions: {str(e)}")

if __name__ == "__main__":
    check_sessions() 