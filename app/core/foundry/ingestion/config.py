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
    ".rst": "docs",
    ".json": "docs",
    ".csv": "docs",
    ".xml": "docs",
    ".yaml": "docs",
    ".yml": "docs",
    ".html": "docs",
    ".htm": "docs",
    ".log": "docs",
    ".ini": "docs",
    ".cfg": "docs",
    ".conf": "docs",
    ".py": "docs",
    ".js": "docs",
    ".ts": "docs",
    ".java": "docs",
    ".cpp": "docs",
    ".c": "docs",
    ".h": "docs",
    ".go": "docs",
    ".rs": "docs",
    ".sql": "docs",
}