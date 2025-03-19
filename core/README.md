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

```json
{
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "system": "You are a helpful assistant specializing in explaining topics in a user-friendly way. Provide clear explanations that assume no prior knowledge. Maintain the conversation context and topic throughout your responses. Be super brief and concise.",
  "user": "@{SESSION_ID}.get-question.response",
  "include_history": true,
  "directly_set_reply": true,
  "schema": {
    "type": "object",
    "properties": {
      "response": {
        "type": "string",
        "description": "The main response to the user query"
      },
      "followup": {
        "type": "string",
        "description": "A question for the user that encourages them to continue to explore the subject."
      },
      "merits_followup": {
        "type": "boolean",
        "description": "Determines if the response from the user merits a follow up question."
      }
    },
    "required": ["response", "followup"]
  }
}
``` 