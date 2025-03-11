#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv('../.env.local')  # Try relative path first
if not os.path.exists('../.env.local'):
    load_dotenv('.env.local')  # Try current directory

# Neo4j connection details
NEO4J_URL = os.getenv('NEO4J_URL')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

if not all([NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD]):
    print("Error: Neo4j connection details are missing.")
    print("Please ensure NEO4J_URL, NEO4J_USERNAME, and NEO4J_PASSWORD are set in .env.local")
    exit(1)

class WorkflowCleaner:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URL, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def find_duplicate_relationships(self):
        """Find duplicate NEXT relationships in the workflow"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (source:STEP)-[r:NEXT]->(target:STEP)
                WITH source, target, COUNT(r) as rel_count
                WHERE rel_count > 1
                RETURN source.id as source_id, target.id as target_id, rel_count
                """
            )
            
            duplicates = []
            for record in result:
                duplicates.append({
                    'source': record['source_id'],
                    'target': record['target_id'],
                    'count': record['rel_count']
                })
            
            return duplicates
    
    def clean_duplicate_relationships(self):
        """Clean duplicate NEXT relationships in the workflow"""
        duplicates = self.find_duplicate_relationships()
        
        if not duplicates:
            print("No duplicate relationships found.")
            return
        
        print(f"Found {len(duplicates)} duplicate relationship types to clean.")
        
        with self.driver.session() as session:
            for duplicate in duplicates:
                source = duplicate['source']
                target = duplicate['target']
                count = duplicate['count']
                
                print(f"Cleaning {count} duplicate relationships from '{source}' to '{target}'")
                
                # Delete all but one relationship
                result = session.run(
                    """
                    MATCH (source:STEP {id: $source_id})-[r:NEXT]->(target:STEP {id: $target_id})
                    WITH r, source, target
                    ORDER BY ID(r) 
                    SKIP 1
                    DELETE r
                    RETURN count(*) as deleted_count
                    """,
                    source_id=source,
                    target_id=target
                )
                
                record = result.single()
                print(f"Deleted {record['deleted_count']} duplicate relationships.")

if __name__ == "__main__":
    print("=== Neo4j Workflow Cleaner ===")
    print(f"Connecting to: {NEO4J_URL}")
    
    cleaner = WorkflowCleaner()
    try:
        cleaner.clean_duplicate_relationships()
        print("Workflow cleaning completed successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        cleaner.close() 