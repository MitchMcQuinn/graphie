# Core Package

This package contains the core components of the graph-based workflow engine.

## Purpose

The `core` package provides the foundational infrastructure for the graph-based workflow engine, separating core engine components from agent-accessible utilities. 

## Modules

- **graph_engine.py**: Implements the `GraphWorkflowEngine` class, which manages workflow execution using a Neo4j graph database.

- **database.py**: Centralizes Neo4j database connectivity, providing a consistent way to establish and maintain database connections.

- **session_manager.py**: Provides a centralized interface for interacting with session data stored in Neo4j.

- **store_memory.py**: Handles the storage of outputs from workflow steps in Neo4j SESSION nodes.

- **resolve_variable.py**: Resolves variable references between workflow steps for data passing.

## Usage

Core components must be imported directly:

```python
from core.graph_engine import get_graph_workflow_engine
from core.session_manager import get_session_manager
from core.database import get_neo4j_driver
```

Workflow utilities should be imported from the utils package:

```python
from utils.generate import generate
from utils.request import request
from utils.reply import reply
``` 

## Workflow Graph Ontology
### SESSION node

state:
  ```json
  {
    "state": {
      "id": "",                    // UUID 
      "workflow": {                // Branch execution management      
        "step_id": {              // 'step_id' replaced with step being logged
          "status": "active|pending|complete",      // 'pending', 'active', or 'complete'
          "dependencies": ["@{SESSION_ID}.step-id.key"], // Array of the variables that the action depends on
          "error": "string"        // logged errors
        }
      },
      "data": {
        "outputs": {},            // Step outputs (JSONs) indexed by step_id
        "messages": []            // Chat history log
      }
    }
  }
  ```
    
#### STEP node

id: string                         // Unique identifier
utility: [module].[function]       // Pointer to a function in the utility directory
input: 
    ```json
    input: {
        "[property]": " @{SESSION_ID}.generate-answer.followup |default-value ",     // JSON that defines inputs for the utility function
    }
    ```

### NEXT relationship
id: string                         // Unique identifier
condition: ['@{SESSION_ID}.generate-answer.followup'] // An array of values expected to be boolean
operator: String // ('AND' or 'OR')


## Session Workflow Logic
### Initialization
1. Create a Neo4j driver connection
2. Generate a unique session ID
3. Create a SESSION node with a state object initialized as:
  ```json
  {
    "state": {
      "id": "[UUID]", //UUID generated in step 2
      "workflow": {  
        "root": {
          "status": "active",   
          "error": ""
        }
      },
      "data": {
        "outputs": {},
        "messages": []
      }
    }
  }
  ```
  

### Workflow Processing Loop
For each STEP node with status 'active' in state.workflow[step-id]:
  1. Variable Resolution:
     - If step requires input variables:
       - Look up each variable in state.data.outputs[step-id]
       - If any variable missing:
         - Mark step as 'pending'
         - Continue to next active step
     - If no variables needed or all found:
       - Proceed to execution

  2. Step Execution:
     - If utility function defined:
       - Execute the function (with any resolved inputs)
       - Store result in state.data.outputs[step_id]
       - Mark step as 'complete'
     - If no utility:
       - Mark step as 'complete'

  3. Path Progression:
     - Check for outgoing NEXT relationships from completed step
     - For each outgoing NEXT relationship:
       - Get the relationship's condition array and operator
       - Evaluate all conditions in the array by resolving each value
       - Determine if relationship is valid:
         - If operator is 'AND': all conditions must be true
         - If operator is 'OR': at least one condition must be true
       - If relationship is valid:
         - Acquire lock on SESSION node
         - Mark target step as 'active' in state.workflow
         - Release lock
     - Multiple paths may activate in parallel, but state updates are serialized through locking

  4. Continue processing until:
     - No active steps remain
     - All active steps are pending
     - Step requests user input
