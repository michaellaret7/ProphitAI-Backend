"""
Configuration for the ingestion module.
"""

# Extension to handler mapping
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "pdf",
    ".xlsx": "excel",
    ".xls": "excel",
    ".txt": "text",
    ".md": "text",
    ".rst": "text",
    ".json": "text",
    ".csv": "text",
    ".xml": "text",
    ".yaml": "text",
    ".yml": "text",
    ".html": "text",
    ".htm": "text",
    ".log": "text",
    ".ini": "text",
    ".cfg": "text",
    ".conf": "text",
    ".py": "text",
    ".js": "text",
    ".ts": "text",
    ".java": "text",
    ".cpp": "text",
    ".c": "text",
    ".h": "text",
    ".go": "text",
    ".rs": "text",
    ".sql": "text",
}
