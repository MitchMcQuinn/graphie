# Graph-Based Agentic Workflow Management

A powerful and flexible workflow management system that uses a graph database (Neo4j) to store and execute conversational workflows. This system enables the creation of complex, stateful workflows with conditional branching and looping, data persistence, and real-time updates.

## Features

- **Graph-Based Workflow Engine**: Uses Neo4j to store and manage workflow state, enabling complex branching and conditional execution
- **Session Management**: Maintains isolated workflow sessions with persistent state
- **Variable Resolution**: Supports dynamic variable resolution between workflow steps
- **Real-time Updates**: WebSocket-based real-time updates for workflow state changes
- **GraphQL API**: Modern GraphQL interface for interacting with workflows
- **Conditional Branching**: Support for complex workflow paths based on conditions
- **Error Handling**: Comprehensive error tracking and logging
- **Memory Management**: Persistent storage of workflow outputs and chat history
- **Workflow Visualization**: Tools for viewing and understanding workflow structure

## Architecture

### Core Components

- **GraphWorkflowEngine**: The main engine that manages workflow execution and state
- **SessionManager**: Handles session creation and management
- **Database**: Manages Neo4j database connectivity
- **Memory Store**: Handles storage of workflow outputs
- **Variable Resolver**: Manages variable resolution between steps

### Data Model

#### SESSION Node
Represents a workflow session with the following structure:
```json
{
    "id": "UUID",
    "memory": {},
    "next_steps": [],
    "created_at": "datetime",
    "status": "active|awaiting_input",
    "errors": [],
    "chat_history": []
}
```

#### STEP Node
Represents a workflow step with:
- Unique identifier
- Utility function reference
- Input parameters
- Output storage

#### NEXT Relationship
Defines workflow transitions with:
- Conditional logic
- Branching rules
- Error handling

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   cp .env.sample .env.local
   # Edit .env.local with your configuration
   ```

## Usage

### Starting the Application

```bash
python app.py
```

### GraphQL API

The application exposes a GraphQL API for interacting with workflows:

```graphql
query {
  frontendState(sessionId: "your-session-id") {
    awaitingInput
    reply
    statement
    hasPendingSteps
    structuredData
    error
  }
}
```

### Workflow Management

1. Create a new workflow session:
   ```python
   from core.graph_engine import get_graph_workflow_engine
   
   engine = get_graph_workflow_engine()
   session_id = engine.create_session()
   ```

2. Start a workflow:
   ```python
   result = engine.start_workflow(session_id)
   ```

3. Continue workflow with user input:
   ```python
   result = engine.continue_workflow(user_input, session_id)
   ```

## Development

### Project Structure

```
.
├── app.py                 # Main application entry point
├── core/                  # Core workflow engine components
├── utils/                 # Utility functions for workflow steps
├── tools/                 # Development and debugging tools
├── templates/             # Web application templates
├── static/               # Static web assets
├── tests/                # Test suite
└── schema.graphql        # GraphQL schema definition
```

### Adding New Workflow Steps

1. Create a new utility function in the `utils/` directory
2. Define the step in Neo4j with appropriate relationships
3. Configure input/output parameters
4. Add any necessary conditions for branching

## Testing

Run the test suite:
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
