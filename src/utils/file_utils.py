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

def get_schema_path():
    """
    Get the path to the database_schemas.json file.
    
    Returns:
        pathlib.Path: Path to the database_schemas.json file
    """
    return get_project_root() / "src" / "data" / "database_schemas.json"

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