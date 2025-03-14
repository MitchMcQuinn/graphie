CREATE OR REPLACE WORKFLOW COMMANDS:

// Update the generate-followup node to use the unified generate function with followup type
MATCH (n:STEP {id: 'generate-followup'})
SET n.function = 'generate.generate',
    n.input = '{"type": "followup", "system": "You are creating simple, helpful follow-up questions for a conversational assistant. Generate questions that offer to provide more information rather than asking the user for information.", "temperature": 0.7, "model": "gpt-4-turbo"}'
RETURN n;

// Update the generate-answer node to use chat history for context
MATCH (n:STEP {id: 'generate-answer'})
SET n.input = '{"type": "answer", "model": "gpt-4-turbo", "temperature": 0.7, "system": "You are a helpful assistant specializing in explaining topics in a user-friendly way. Provide clear explanations that assume no prior knowledge. Maintain the conversation context and topic throughout your responses.", "user": "@{get-question}.response", "include_history": true}'
RETURN n;
