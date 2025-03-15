# Principles of the Graphie Framework

Graphie is a conversational workflow engine powered by Neo4j that enables the creation of dynamic conversation flows. The following principles define how Graphie works:

## Core Workflow Principles

- A workflow consists of connected STEP nodes, where each step can have one parent but multiple children (one incoming NEXT relationship but potentially many outgoing ones)
- Each STEP node executes a utility function that processes data and stores results as variables in the session
- The session acts as shared memory — variables created by any step are accessible to all other steps in the workflow
- Steps require all referenced variables to exist before they can execute — if a variable is missing, the step waits until it becomes available
- Workflows can split into multiple parallel paths that run simultaneously, allowing for efficient processing of independent tasks

## Variable Handling

- Variables follow a reference pattern of `@{node-id}.key` to access values from previous workflow steps
- Default values can be specified using the format `@{node-id}.key|default_value`
- When a step references unavailable variables, it's deferred and automatically retried when variables become available
- Variable synchronization enables complex workflows with interdependent steps

## Execution Model

- Multiple workflow branches can execute in parallel, limited by a configurable maximum
- The workflow engine tracks deferred steps and automatically retries them when dependencies are resolved
- Workflow execution continues until all paths are completed or terminated
- Sessions maintain state across the entire conversation flow

## Workflow Design

- Workflows are defined as a graph of connected STEP nodes in Neo4j
- Each STEP specifies a function to execute (e.g., `reply.reply`, `analyze.analyze_input`)
- Conditional branching allows for dynamic conversation paths based on user input
- Loop structures can be created to enable repeated interactions

## Function Integration

- Utility functions are dynamically loaded from modules
- Each function receives session data and input parameters
- Functions store their results in the session for use by other steps
- The framework supports various utility types: analysis, generation, conditional logic, and user interaction