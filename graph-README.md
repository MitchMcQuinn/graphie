
# Workflow Graph Ontology
## SESSION node
state:

    ```json
    state: {
        id: "",                      // UUID generated in step 2
        workflow: {
            initialization: "root",  // Starting point of workflow
            error: null,            // Critical workflow-level errors
            pending: {              // Steps blocked on dependencies
                "step_id": ["@{SESSION_ID}.other_step.key", ...],
            }, 
            log: {
              
            }
        },
        data: {
            outputs: {},           // Step outputs (JSONs) indexed by step_id
            messages: []           // Chat history log
        }
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


