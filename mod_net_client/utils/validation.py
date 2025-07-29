"""Validation utilities for the module registry client."""
from typing import Any, Dict


def validate_metadata(metadata: Dict[str, Any]) -> bool:
    """Validate module metadata format.
    
    Args:
        metadata: Module metadata to validate
        
    Returns:
        bool: True if metadata is valid
    """
    required_fields = {"name", "version", "description"}
    return all(field in metadata for field in required_fields)
