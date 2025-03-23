"""
core/workflow/migrations/manager.py
----------------
This module provides a migration manager to handle running database migrations.
"""

import logging
from typing import List, Callable, Tuple
from neo4j import Driver

from .initial_schema import migrate as migrate_001
from .initial_schema import rollback as rollback_001
from .update_workflow_data import migrate as migrate_002
from .update_workflow_data import rollback as rollback_002

logger = logging.getLogger(__name__)

class MigrationManager:
    """
    Manages database migrations for the workflow engine.
    """
    
    def __init__(self, driver: Driver):
        """
        Initialize the MigrationManager.
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
        self.migrations: List[Tuple[str, Callable, Callable]] = [
            ("001_initial_schema", migrate_001, rollback_001),
            ("002_update_workflow_data", migrate_002, rollback_002)
        ]
    
    def run_migrations(self) -> bool:
        """
        Run all pending migrations.
        
        Returns:
            bool: True if all migrations were successful, False otherwise
        """
        try:
            for name, migrate, _ in self.migrations:
                logger.info(f"Running migration: {name}")
                if not migrate(self.driver):
                    logger.error(f"Migration failed: {name}")
                    return False
                logger.info(f"Migration successful: {name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error running migrations: {str(e)}")
            return False
    
    def rollback_migrations(self) -> bool:
        """
        Rollback all migrations in reverse order.
        
        Returns:
            bool: True if all rollbacks were successful, False otherwise
        """
        try:
            for name, _, rollback in reversed(self.migrations):
                logger.info(f"Rolling back migration: {name}")
                if not rollback(self.driver):
                    logger.error(f"Rollback failed: {name}")
                    return False
                logger.info(f"Rollback successful: {name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back migrations: {str(e)}")
            return False 