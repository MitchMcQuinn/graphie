"""
core/workflow/path.py
----------------
This module implements the PathEvaluator class which handles path progression and condition evaluation
in the workflow engine.
"""

import logging
from typing import Dict, Any, List, Optional
from neo4j import Driver

from .state import WorkflowState
from .executor import StepExecutor

logger = logging.getLogger(__name__)

class PathEvaluator:
    """
    Handles path progression and condition evaluation in the workflow.
    """
    
    def __init__(self, driver: Driver, state: WorkflowState, executor: StepExecutor):
        """
        Initialize the PathEvaluator.
        
        Args:
            driver: Neo4j driver instance
            state: WorkflowState instance
            executor: StepExecutor instance
        """
        self.driver = driver
        self.state = state
        self.executor = executor
    
    def evaluate_paths(self, step_id: str) -> List[str]:
        """
        Evaluate all possible paths from a completed step.
        
        Args:
            step_id: ID of the completed step
            
        Returns:
            List[str]: List of step IDs that should be activated
        """
        try:
            with self.driver.session() as session:
                # Get all outgoing NEXT relationships
                result = session.run("""
                    MATCH (s:STEP {id: $step_id})-[r:NEXT]->(t:STEP)
                    RETURN t.id as target_id, r.conditions as conditions, r.operator as operator
                """, step_id=step_id)
                
                activated_steps = []
                
                for record in result:
                    target_id = record['target_id']
                    conditions = record['conditions']
                    operator = record['operator']
                    
                    # Evaluate conditions
                    if self._evaluate_conditions(conditions, operator):
                        activated_steps.append(target_id)
                
                return activated_steps
                
        except Exception as e:
            logger.error(f"Error evaluating paths from step {step_id}: {str(e)}")
            return []
    
    def _evaluate_conditions(self, conditions: List[Dict[str, Any]], operator: str) -> bool:
        """
        Evaluate a list of conditions using the specified operator.
        
        Args:
            conditions: List of condition dictionaries
            operator: Operator to use ('AND' or 'OR')
            
        Returns:
            bool: True if conditions are satisfied, False otherwise
        """
        if not conditions:
            return True
        
        results = []
        for condition in conditions:
            try:
                # Resolve the condition's variable reference
                var_ref = condition.get('variable')
                if not var_ref:
                    continue
                
                value = self.executor.resolve_variables('', {'value': var_ref})['value']
                
                # Compare with expected value
                expected = condition.get('value')
                if expected is None:
                    continue
                
                # Handle different comparison operators
                op = condition.get('operator', '==')
                result = self._compare_values(value, expected, op)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error evaluating condition: {str(e)}")
                results.append(False)
        
        if not results:
            return True
        
        # Apply operator
        if operator == 'AND':
            return all(results)
        elif operator == 'OR':
            return any(results)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    def _compare_values(self, value: Any, expected: Any, operator: str) -> bool:
        """
        Compare two values using the specified operator.
        
        Args:
            value: Actual value
            expected: Expected value
            operator: Comparison operator
            
        Returns:
            bool: True if comparison is satisfied, False otherwise
        """
        try:
            if operator == '==':
                return value == expected
            elif operator == '!=':
                return value != expected
            elif operator == '>':
                return value > expected
            elif operator == '>=':
                return value >= expected
            elif operator == '<':
                return value < expected
            elif operator == '<=':
                return value <= expected
            elif operator == 'in':
                return value in expected
            elif operator == 'not in':
                return value not in expected
            else:
                logger.warning(f"Unknown comparison operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error comparing values: {str(e)}")
            return False
    
    def activate_steps(self, step_ids: List[str]) -> bool:
        """
        Activate a list of steps in the workflow state.
        
        Args:
            step_ids: List of step IDs to activate
            
        Returns:
            bool: True if all steps were activated successfully, False otherwise
        """
        success = True
        for step_id in step_ids:
            if not self.state.update_step_status(step_id, "active"):
                success = False
                logger.error(f"Failed to activate step {step_id}")
        
        return success
    
    def get_step_dependencies(self, step_id: str) -> List[str]:
        """
        Get all dependencies for a step.
        
        Args:
            step_id: ID of the step
            
        Returns:
            List[str]: List of step IDs that this step depends on
        """
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:STEP {id: $step_id})<-[r:NEXT]-(t:STEP)
                    RETURN t.id as dependency_id
                """, step_id=step_id)
                
                return [record['dependency_id'] for record in result]
                
        except Exception as e:
            logger.error(f"Error getting dependencies for step {step_id}: {str(e)}")
            return [] 