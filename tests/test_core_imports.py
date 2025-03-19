"""
Tests for core package imports to ensure the restructuring maintains functionality.
"""

import unittest
from unittest.mock import patch, MagicMock

class TestCoreImports(unittest.TestCase):
    """Test that core module imports work correctly."""

    def test_direct_core_imports(self):
        """Test importing directly from core package."""
        try:
            from core.database import get_neo4j_driver, has_session
            from core.session_manager import get_session_manager, SessionManager
            from core.store_memory import store_memory
            from core.resolve_variable import resolve_variable, process_variables
            from core.graph_engine import get_graph_workflow_engine, GraphWorkflowEngine
            self.assertTrue(True, "All direct imports from core succeeded")
        except ImportError as e:
            self.fail(f"Direct imports from core failed: {e}")
    
    def test_utils_module_imports(self):
        """Test importing utility modules."""
        try:
            import utils.generate
            import utils.request
            import utils.reply
            # structured_generation functionality has been merged into generate.py
            self.assertTrue(True, "All utils module imports succeeded")
        except ImportError as e:
            self.fail(f"Utils module imports failed: {e}")
    
    @patch('core.database.get_neo4j_driver')
    def test_session_manager_with_core_database(self, mock_driver):
        """Test that session_manager correctly uses the core database module."""
        from core.session_manager import get_session_manager
        
        # Set up the mock
        mock_instance = MagicMock()
        mock_driver.return_value = mock_instance
        
        # Call the function
        manager = get_session_manager()
        
        # Verify the database driver was called
        mock_driver.assert_called_once()
        self.assertIsNotNone(manager, "Session manager should be returned")

if __name__ == '__main__':
    unittest.main() 