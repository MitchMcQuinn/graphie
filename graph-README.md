# Workflow Graph Ontology
## SESSION node
```json
{
    "id": "UUID",                    // Unique identifier for the session
    "memory": {},                    // JSON object storing step outputs indexed by step_id
    "next_steps": [],                // Array of step IDs to process next
    "created_at": "datetime",        // Session creation timestamp
    "status": "active|awaiting_input", // Current session status
    "errors": [],                    // Array of error objects with step_id, cycle, error, and timestamp
    "chat_history": []               // Array of chat messages with role and content
}
```

## STEP node
id: string                         // Unique identifier
utility: [module].[function]       // Pointer to a function in the utility directory
input: 

    ```json
    input: {
        "[property]": " @{SESSION_ID}.generate-answer.followup |default-value ",     // JSON that defines inputs for the utility function
    }
    ```

## NEXT relationship
id: string                         // Unique identifier
condition: ['@{SESSION_ID}.generate-answer.followup'] // An array of values expected to be boolean
operator: String ('AND' or 'OR')


