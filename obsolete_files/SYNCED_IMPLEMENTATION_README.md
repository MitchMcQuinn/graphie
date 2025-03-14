# Synced Workflow Implementation

This implementation enhances the fixed parallel workflow with improved variable synchronization to handle dependencies between parallel paths.

## Key Features

1. **Indefinite Variable Readiness Checks**: The engine will keep trying to resolve variables as long as the session is active, rather than giving up after a few attempts.

2. **Deferred Step Processing**: Steps that reference unavailable variables are automatically deferred and retried later, allowing the workflow to continue with other paths.

3. **Non-Blocking Architecture**: Uses threading to manage retries without blocking the main execution path, ensuring responsive UI.

4. **Enhanced Debugging**: Provides additional endpoints to monitor variable availability and deferred steps.

5. **Session Management**: Properly tracks whether a session is active to avoid unnecessary processing.

## How It Works

### Variable Resolution Process

1. When a workflow step is processed, the engine first checks if all required variables are available.
2. If variables are missing, the step is marked as "deferred" and queued for later processing.
3. A background thread is scheduled to retry the step after a delay.
4. The retry process continues indefinitely as long as the session remains active.
5. Once all variables become available, the deferred step is processed, and the workflow continues.

### Example Scenario

Consider a workflow with parallel paths:
- Path A: Analyzes sentiment (slow operation)
- Path B: Extracts entities (fast operation)
- Path C: Summarizes both results (depends on A and B)

With the synced engine:
1. Paths A and B start executing in parallel
2. Path B completes quickly and updates the session with entity data
3. Path C tries to execute but needs data from Path A, so it's deferred
4. Path A eventually completes and updates the session with sentiment data
5. The deferred Path C is automatically retried, finds all variables available, and completes successfully

## Benefits Over the Fixed Implementation

1. **Resilience**: No more "missing variable" errors when one path completes before another.

2. **Efficiency**: The system doesn't waste resources constantly polling; it uses event-driven retries.

3. **Visibility**: Detailed monitoring of deferred steps and missing variables enables easier debugging.

4. **Simplicity**: No need to manually define dependencies between steps; they're inferred from variable references.

## Usage

### Starting the Application

```bash
# Make the setup script executable
chmod +x setup_synced_implementation.sh

# Run the setup script
./setup_synced_implementation.sh
```

### Debugging Endpoints

- `/debug_workflow`: Overview of workflow state, paths, and deferred steps
- `/debug_variables`: Detailed view of variable availability and what deferred steps are waiting for
- `/stream_log`: Real-time streaming of log events for debugging

## Implementation Details

The synced implementation consists of:

1. **synced_engine.py**: Extends the fixed engine with variable synchronization
2. **app_synced.py**: Flask application using the synced engine
3. **setup_synced_implementation.sh**: Script to set up and run the implementation

### Key Methods

- `_replace_variables`: Enhanced to detect missing variables and return None to trigger deferral
- `_process_step`: Modified to handle variable resolution failures by deferring steps
- `_retry_deferred_step`: New method to manage the retry process for deferred steps
- `mark_session_inactive`: Method to stop retrying when a session ends

## Limitations

1. The current implementation uses a simple thread-based approach for retries, which may not be optimal for very high-concurrency systems.

2. There's no maximum lifetime for deferred steps, which could potentially lead to resource issues in long-running sessions.

3. Variable dependencies are only tracked at the step level, not at the individual variable level, which may lead to unnecessary retries. 