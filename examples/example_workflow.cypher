// Workflow that uses structured generation
// This workflow asks users a question, processes their response with a structured
// generation that returns a boolean and string, then displays the results

// Create the root node (entry point)
CREATE (root:STEP {
  id: "root-2",
  description: "Starting point for the structured generation workflow",
  function: "reply.reply",
  input: '{"reply": "Welcome to the structured generation workflow! I will analyze your input and provide structured feedback."}'
})

// Create a node to get user input
CREATE (get_input:STEP {
  id: "get-input",
  description: "Ask the user to provide some information",
  function: "request.request",
  input: '{"statement": "Please describe a recent experience you had (good or bad). I\'ll analyze if it was positive and provide feedback."}'
})

// Create a node to generate structured analysis
CREATE (analyze_input:STEP {
  id: "analyze-input",
  description: "Generate structured analysis of user input",
  function: "generate.generate",
  input: '{
    "type": "structured",
    "system": "You are an experience analyzer that determines if a user\'s described experience was positive and provides feedback.",
    "user": "@{get-input}.response",
    "temperature": 0.5,
    "model": "gpt-4-turbo",
    "function_name": "analyze_experience",
    "function_description": "Analyze if the user\'s experience was positive and provide feedback",
    "response_format": {
      "type": "object",
      "properties": {
        "is_positive": {
          "type": "boolean",
          "description": "Whether the described experience was positive or negative"
        },
        "feedback": {
          "type": "string",
          "description": "Constructive feedback or reflection on the experience"
        }
      },
      "required": ["is_positive", "feedback"]
    }
  }'
})

// Create a node to provide the analysis result to the user
CREATE (provide_analysis:STEP {
  id: "provide-analysis",
  description: "Send the structured analysis to the user",
  function: "utils.structured_generation.format_analysis",
  input: '{
    "is_positive": "@{analyze-input}.is_positive",
    "feedback": "@{analyze-input}.feedback"
  }'
})

// Create a node to show the formatted analysis
CREATE (show_analysis:STEP {
  id: "show-analysis",
  description: "Display the formatted analysis to the user",
  function: "reply.reply",
  input: '{
    "reply": "@{provide-analysis}.formatted_result"
  }'
})

// Create a node to ask if user wants to continue
CREATE (continue_question:STEP {
  id: "continue-question",
  description: "Ask if the user wants to analyze another experience",
  function: "request.request",
  input: '{"statement": "Would you like to analyze another experience? (yes/no)"}'
})

// Connect the steps with NEXT relationships
CREATE 
  (root)-[:NEXT {id: "to-input"}]->(get_input),
  (get_input)-[:NEXT {id: "to-analysis"}]->(analyze_input),
  (analyze_input)-[:NEXT {id: "to-provide"}]->(provide_analysis),
  (provide_analysis)-[:NEXT {id: "to-show"}]->(show_analysis),
  (show_analysis)-[:NEXT {id: "to-continue"}]->(continue_question),
  
  // Conditional branch to loop back or end
  (continue_question)-[:NEXT {
    id: "if-yes",
    description: "If the user wants to analyze another experience",
    function: "condition.equals",
    input: '{"value": "@{continue-question}.response", "equals": "yes"}'
  }]->(get_input),
  
  (continue_question)-[:NEXT {
    id: "if-no",
    description: "If the user doesn't want to continue",
    function: "condition.not_equals",
    input: '{"value": "@{continue-question}.response", "equals": "yes"}'
  }]->(end:STEP {
    id: "end",
    description: "End of workflow",
    function: "reply.reply",
    input: '{"reply": "Thank you for using the structured analysis workflow. Goodbye!"}'
  }) 