"""
core package
-----------
Core components of the graph-based workflow engine.
"""

from .database import get_neo4j_driver, has_session
from .session_manager import SessionManager
from .store_memory import store_memory
from .resolve_variable import resolve_variable, process_variables 