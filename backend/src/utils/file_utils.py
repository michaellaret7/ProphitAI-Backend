"""
File utilities for common file operations.
"""
import os
import json
from pathlib import Path

def get_project_root():
    """
    Get the project root directory by looking for marker files.
    
    Returns:
        pathlib.Path: Path to the project root
        
    Raises:
        RuntimeError: If project root cannot be found
    """
    # Start from this file's location and traverse up
    current = Path(__file__).resolve()
    
    # Look for common project root markers
    markers = ["requirements.txt", ".git", "package.json", "pyproject.toml"]
    
    for parent in [current] + list(current.parents):
        for marker in markers:
            if (parent / marker).exists():
                return parent
    
    # If no markers found, raise an error instead of failing silently
    raise RuntimeError(
        f"Could not find project root. Searched from {current} up to filesystem root. "
        f"Looking for markers: {markers}"
    )

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
        
    Raises:
        FileNotFoundError: If schema file cannot be found in any location
    """
    try:
        root = get_project_root()
    except RuntimeError as e:
        raise FileNotFoundError(f"Cannot locate schema file: {e}")

    # New canonical location – ``src/data/database``
    new_path = root / "backend" / "src" / "data" / "database" / filename
    if new_path.exists():
        return new_path

    # Fallback to old path for compatibility
    old_path = root / "backend" / "src" / "data" / filename
    if old_path.exists():
        return old_path
        
    # If neither location has the file, raise an error
    raise FileNotFoundError(
        f"Schema file '{filename}' not found in either location:\n"
        f"  Primary: {new_path}\n"
        f"  Fallback: {old_path}"
    )

def load_schema_data(filename: str = "database_schemas.json"):
    """
    Load the database schema data from a JSON file.
    
    Args:
        filename: The schema file name. Defaults to ``database_schemas.json``.
    
    Returns:
        dict: Database schema data
        
    Raises:
        FileNotFoundError: If schema file cannot be found
        ValueError: If JSON content is invalid
        PermissionError: If file cannot be read due to permissions
    """
    try:
        schema_path = get_schema_path(filename)
    except FileNotFoundError:
        # Re-raise with more context
        raise
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in schema file '{schema_path}': {e}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading schema file: {schema_path}")
    except Exception as e:
        # Catch any other unexpected errors
        raise RuntimeError(f"Unexpected error loading schema from '{schema_path}': {e}")

def ensure_dir_exists(directory):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure exists
    
    Returns:
        pathlib.Path: Path to the directory
        
    Raises:
        PermissionError: If directory cannot be created due to permissions
        OSError: If directory creation fails for other reasons
    """
    try:
        dir_path = Path(directory)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path
    except PermissionError:
        raise PermissionError(f"Permission denied creating directory: {directory}")
    except OSError as e:
        raise OSError(f"Failed to create directory '{directory}': {e}") 