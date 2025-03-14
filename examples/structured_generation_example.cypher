CREATE (generate_recommendation:STEP {
    id: 'generate-recommendation',
    name: 'Generate Product Recommendation',
    description: 'Generate a structured product recommendation based on user requirements',
    function: 'generate.generate',
    input: '{
        "type": "structured", 
        "system": "You are a product recommendation assistant that provides accurate, helpful recommendations based on user requirements. Focus only on providing the structured data without any additional text.", 
        "user": "@{get-requirements}.response", 
        "model": "gpt-4-turbo",
        "temperature": 0.7,
        "function_name": "recommend_product",
        "function_description": "Generate a product recommendation based on user requirements",
        "response_format": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "The name of the recommended product"
                },
                "category": {
                    "type": "string",
                    "description": "Product category (e.g., laptop, smartphone, camera)"
                },
                "price_range": {
                    "type": "object",
                    "properties": {
                        "min": {
                            "type": "number",
                            "description": "Minimum price in USD"
                        },
                        "max": {
                            "type": "number",
                            "description": "Maximum price in USD"
                        }
                    },
                    "required": ["min", "max"]
                },
                "features": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of key product features"
                },
                "rating": {
                    "type": "number",
                    "description": "Estimated product rating on a scale of 1-5"
                },
                "explanation": {
                    "type": "string",
                    "description": "Explanation of why this product is recommended"
                }
            },
            "required": ["product_name", "category", "price_range", "features", "rating", "explanation"]
        }
    }'
})

CREATE (generate_alternatives:STEP {
    id: 'generate-alternatives',
    name: 'Generate Alternatives',
    description: 'Generate alternative product recommendations',
    function: 'generate.generate',
    input: '{
        "type": "structured",
        "system": "You are a product recommendation assistant. Generate two alternative product recommendations in the same category as the original recommendation.",
        "user": "The user was previously recommended a @{generate-recommendation}.category called \"@{generate-recommendation}.product_name\" with a price range of $@{generate-recommendation}.price_range.min to $@{generate-recommendation}.price_range.max. Please recommend two alternative products in the same category.",
        "model": "gpt-4-turbo",
        "temperature": 0.8,
        "function_name": "generate_alternative_products",
        "function_description": "Generate alternative product recommendations in the same category",
        "response_format": {
            "type": "object",
            "properties": {
                "alternatives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_name": {
                                "type": "string",
                                "description": "The name of the alternative product"
                            },
                            "price": {
                                "type": "number",
                                "description": "Approximate price in USD"
                            },
                            "key_difference": {
                                "type": "string",
                                "description": "Key difference compared to the original recommendation"
                            }
                        },
                        "required": ["product_name", "price", "key_difference"]
                    }
                }
            },
            "required": ["alternatives"]
        }
    }'
}) 