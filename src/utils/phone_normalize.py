"""
Phone number normalization utilities for duplicate detection and comparison.
"""
import re
from typing import Optional


def normalize_phone_for_comparison(phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number for comparison by removing all formatting.
    Returns digits only (no +, spaces, dashes, etc.)
    
    Examples:
    - "+92 303 5699010" -> "923035699010"
    - "+92 30356999010" -> "9230356999010"
    - "(503) 555-1234" -> "5035551234"
    - "+1-503-555-1234" -> "15035551234"
    """
    if not phone:
        return None
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', str(phone))
    
    # Return None for empty strings
    if not digits_only:
        return None
    
    return digits_only


def phones_match(phone1: Optional[str], phone2: Optional[str]) -> bool:
    """
    Check if two phone numbers match (after normalization).
    Returns True if they represent the same number, False otherwise.
    """
    if not phone1 or not phone2:
        return False
    
    normalized1 = normalize_phone_for_comparison(phone1)
    normalized2 = normalize_phone_for_comparison(phone2)
    
    if not normalized1 or not normalized2:
        return False
    
    return normalized1 == normalized2


def is_similar_phone(phone1: Optional[str], phone2: Optional[str], max_diff: int = 1) -> bool:
    """
    Check if two phone numbers are similar (differ by max_diff digits).
    Useful for detecting typos or formatting errors.
    
    Args:
        phone1: First phone number
        phone2: Second phone number
        max_diff: Maximum number of digit differences allowed (default: 1)
    
    Returns:
        True if phones are similar (within max_diff), False otherwise
    """
    if not phone1 or not phone2:
        return False
    
    normalized1 = normalize_phone_for_comparison(phone1)
    normalized2 = normalize_phone_for_comparison(phone2)
    
    if not normalized1 or not normalized2:
        return False
    
    # If exact match, return True
    if normalized1 == normalized2:
        return True
    
    # Check if they differ by max_diff digits (for typo detection)
    if abs(len(normalized1) - len(normalized2)) > max_diff:
        return False
    
    # Use Levenshtein-like comparison for similar numbers
    # Simple approach: count differences
    min_len = min(len(normalized1), len(normalized2))
    max_len = max(len(normalized1), len(normalized2))
    
    # If length difference is more than max_diff, not similar
    if max_len - min_len > max_diff:
        return False
    
    # Count character differences
    differences = 0
    for i in range(min_len):
        if normalized1[i] != normalized2[i]:
            differences += 1
            if differences > max_diff:
                return False
    
    # Add length difference
    differences += (max_len - min_len)
    
    return differences <= max_diff

