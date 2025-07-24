import os
import shutil
from typing import List, Any, Dict

def remove_all_files(directory: str):
    """
    Removes all files and subdirectories within a directory.

    Args:
        directory: The path to the directory.
    """
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

def format_response(status: str, message: str, data: Any = None) -> Dict:
    """
    Create a standardized API response format
    
    Args:
        status: Response status (SUCCESS, ERROR, WARNING, etc.)
        message: Human-readable message
        data: Optional data payload
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "status": status,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    return response

def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate that a filename has an allowed extension
    
    Args:
        filename: Name of the file to check
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.docx'])
        
    Returns:
        True if extension is allowed, False otherwise
    """
    if not filename:
        return False
    
    file_ext = os.path.splitext(filename.lower())[1]
    return file_ext in [ext.lower() for ext in allowed_extensions]

def safe_cast(value: Any, target_type: type, default: Any = None):
    """
    Safely cast a value to a target type with a default fallback
    
    Args:
        value: Value to cast
        target_type: Target type to cast to
        default: Default value if casting fails
        
    Returns:
        Casted value or default
    """
    try:
        return target_type(value)
    except (ValueError, TypeError):
        return default

def filter_none_values(data: Dict) -> Dict:
    """
    Remove keys with None values from a dictionary
    
    Args:
        data: Dictionary to filter
        
    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in data.items() if v is not None}