"""
File utilities for common file operations.
"""
import os
import json
from pathlib import Path

def get_project_root():
    """
    Get the project root directory.
    
    Returns:
        pathlib.Path: Path to the project root
    """
    # Assuming this file is in src/utils/file_utils.py, go up two levels
    return Path(__file__).parent.parent.parent

def get_schema_path(filename: str = "database_schemas.json"):
    """
    Get the path to a schema JSON file (defaults to database_schemas.json).

    The helper will first look inside the new ``src/data/database`` folder that now
    contains the schema files.  If the target file is not found there (for
    backward-compatibility), it will fall back to the legacy location directly
    under ``src/data``.

    Args:
        filename: The schema file name. Defaults to ``database_schemas.json``.

    Returns:
        pathlib.Path: Resolved path to the requested schema JSON file.
    """
    root = get_project_root()

    # New canonical location – ``src/data/database``
    new_path = root / "src" / "data" / "database" / filename
    if new_path.exists():
        return new_path

    # Fallback to old path for compatibility
    return root / "src" / "data" / filename

def load_schema_data():
    """
    Load the database schema data from database_schemas.json.
    
    Returns:
        dict: Database schema data
    """
    schema_path = get_schema_path()
    with open(schema_path, 'r') as f:
        return json.load(f)

def ensure_dir_exists(directory):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure exists
    
    Returns:
        pathlib.Path: Path to the directory
    """
    dir_path = Path(directory)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path 