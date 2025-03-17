# Graph-Based Session Management Update

## Overview

We've implemented a significant architectural change to Graphie's session management system. Instead of storing session state in memory, we now persist all session data in Neo4j as SESSION nodes. This provides several benefits:

1. **Persistence**: Session data survives server restarts
2. **Scalability**: Multiple server instances can access the same session data
3. **Visibility**: Session state can be inspected directly in Neo4j
4. **Consistency**: Unified storage model through graph structure
5. **History Preservation**: Cycle tracking enables maintaining history of step executions

## Key Components

### New Files

- **utils/store_memory.py**: Stores utility function outputs in SESSION nodes
- **utils/resolve_variable.py**: Resolves variable references from SESSION nodes
- **graph_engine.py**: New workflow engine that manages sessions in Neo4j
- **test_graph_session.py**: Test script for the new session management
- **setup_neo4j.cypher**: Neo4j schema setup script

### Updated Files

- **engine.py**: Added get_neo4j_driver function
- **app.py**: Updated to use the new GraphWorkflowEngine
- **utils/generate.py**: Updated to work with graph-based sessions
- **utils/reply.py**: Updated to work with graph-based sessions
- **utils/request.py**: Updated to work with graph-based sessions

## SESSION Node Structure

Each session is represented by a SESSION node with the following properties:

```
{
  id: "unique-session-id",
  memory: {
    "step-id": [
      { /* output from cycle 0 */ },
      { /* output from cycle 1 */ }
    ]
  },
  next_steps: ["step-id-1", "step-id-2"],
  created_at: datetime,
  status: "active|awaiting_input|completed",
  errors: [
    {
      "step_id": "step-id",
      "error": "Error message",
      "timestamp": "ISO datetime"
    }
  ],
  chat_history: [
    {
      "role": "user|assistant",
      "content": "Message content"
    }
  ]
}
```

## Variable Reference System

The new variable reference system uses the format:

```
@{SESSION_ID}.STEP_ID.key[index]|default
```

Where:
- **SESSION_ID**: The unique ID of the session
- **STEP_ID**: The ID of the step that generated the output
- **key**: The property to access in the output
- **index** (optional): The cycle number to access (defaults to latest)
- **default** (optional): Default value if the reference cannot be resolved

## Workflow Execution

1. **Session Initialization**:
   - Generate a unique ID
   - Create a SESSION node with next_steps = ['root']

2. **Workflow Crawling**:
   - Process each step in the next_steps array
   - Store outputs in the SESSION node's memory property
   - Update next_steps based on outgoing relationships

3. **Human-in-the-Loop**:
   - When a request step is encountered, set status = 'awaiting_input'
   - When user input is received, set status = 'active' and continue processing

## Setup Instructions

1. Run the Neo4j schema setup script:
   ```
   cat setup_neo4j.cypher | cypher-shell -u neo4j -p password
   ```

2. Update your .env.local file with Neo4j connection details:
   ```
   NEO4J_URL=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=password
   ```

3. Start the application:
   ```
   python app.py
   ```

## Backward Compatibility

The implementation maintains backward compatibility with the old session management system. Utility functions can work with both the new graph-based sessions and the old in-memory sessions. 