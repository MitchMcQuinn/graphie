# Utils Package

This package contains utility functions that can be used by workflow steps in the graph-based workflow engine.

## Purpose

The `utils` package provides a collection of utility functions that workflow steps can reference. These utilities handle specific tasks that workflow steps might need to perform, such as making requests to users, generating content, or formatting replies.

## Modules

- **generate.py**: Handles OpenAI API integration for text generation with structured outputs.
- **request.py**: Implements human-in-the-loop functionality, pausing the workflow until user input is received.
- **reply.py**: Formats and sends responses to users in the chat interface.
- **generate.py**: Provides specialized functionality for structured content generation.

## Relationship to the Core Package

The `utils` package depends on the `core` package for fundamental infrastructure functionality. While the `core` package provides the engine that powers the workflow system, the `utils` package provides the tools that workflow steps can use to accomplish specific tasks.

All infrastructure components have been moved to the `core` package, and utils now imports these components directly from the core package. This ensures a clear separation of concerns and makes the codebase more maintainable.

## Usage in Workflow Steps

Utility functions from this package are typically referenced in workflow step functions:

```
MATCH (s:STEP {id: 'ask-question'})
SET s.function = 'request.request'
SET s.input = '{"statement": "What would you like to know about?"}'
```

These functions receive a session object and input data and return results that are stored in the session memory:

```python
def some_utility(session, input_data):
    # Process input and perform some action
    result = {"output": "Some result"}
    return result
``` 