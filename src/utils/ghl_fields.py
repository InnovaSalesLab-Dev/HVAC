"""
Utility functions for GHL custom field key normalization and ID mapping.
GHL requires field IDs (not keys) for updates via API.
"""
from typing import Dict, Any, List, Optional
from src.integrations.ghl import GHLClient
from src.utils.logging import logger


def normalize_ghl_field_key(key: str) -> str:
    """
    Normalize custom field key to GHL format.
    GHL generates keys as "contact.{key}" for contact custom fields.
    
    Args:
        key: Field key (with or without "contact." prefix)
    
    Returns:
        Normalized field key in "contact.{key}" format
    """
    if key.startswith("contact."):
        return key
    return f"contact.{key}"


# Cache for field ID mappings (field key -> field ID)
_field_id_cache: Dict[str, str] = {}


async def get_custom_field_ids(ghl_client: Optional[GHLClient] = None) -> Dict[str, str]:
    """
    Get mapping of field keys to field IDs from GHL.
    GHL API requires field IDs (not keys) for updates.
    
    Args:
        ghl_client: Optional GHLClient instance (creates new if not provided)
    
    Returns:
        Dictionary mapping field keys to field IDs
    """
    global _field_id_cache
    
    # Return cache if available
    if _field_id_cache:
        return _field_id_cache
    
    try:
        if not ghl_client:
            ghl_client = GHLClient()
        
        fields = await ghl_client.get_custom_fields()
        
        # Build mapping: fieldKey -> id
        for field in fields:
            field_key = field.get("fieldKey") or field.get("key", "")
            field_id = field.get("id", "")
            if field_key and field_id:
                _field_id_cache[field_key] = field_id
        
        logger.info(f"✅ Cached {len(_field_id_cache)} custom field ID mappings")
        return _field_id_cache
    except Exception as e:
        logger.warning(f"⚠️  Failed to fetch custom field IDs: {e}")
        return {}


async def build_custom_fields_array(fields: Dict[str, Any], use_field_ids: bool = True) -> List[Dict[str, Any]]:
    """
    Build GHL custom fields array format from dictionary.
    
    GHL API requires field IDs (not keys) for updates:
    {"id": "fieldId", "value": "value"}
    
    Falls back to field keys if IDs not available:
    {"field": "contact.field", "value": "value"}
    
    Args:
        fields: Dictionary of field keys and values
        use_field_ids: If True, try to use field IDs (more reliable)
    
    Returns:
        Array of custom field objects in GHL format
    """
    custom_fields_array = []
    
    # Try to get field IDs if requested
    field_id_map = {}
    if use_field_ids:
        try:
            field_id_map = await get_custom_field_ids()
        except:
            pass
    
    for key, value in fields.items():
        normalized_key = normalize_ghl_field_key(key)
        
        # Try to use field ID first (most reliable)
        field_id = field_id_map.get(normalized_key)
        if field_id:
            custom_fields_array.append({
                "id": field_id,
                "value": str(value) if value is not None else ""
            })
        else:
            # Fallback to field key
            custom_fields_array.append({
                "field": normalized_key,
                "value": str(value) if value is not None else ""
            })
    
    return custom_fields_array


def _normalize_field_alias(key: str) -> Optional[str]:
    """
    Generate a normalized alias for a custom field key/name.
    Produces lowercase snake_case without the ``contact.`` prefix.
    """
    if not key:
        return None
    normalized = key.strip()
    if not normalized:
        return None
    normalized = normalized.lower()
    # Remove common prefixes
    if normalized.startswith("contact."):
        normalized = normalized[len("contact.") :]
    normalized = normalized.replace(" ", "_").replace("-", "_").replace("/", "_")
    normalized = normalized.replace("__", "_")
    return normalized


def _store_field(result: Dict[str, Any], key: str, value: Any):
    """
    Store a custom field value under multiple aliases for easier lookups.
    """
    if not key:
        return
    normalized = _normalize_field_alias(key)
    # Preserve original key
    result[key] = value
    # Ensure contact.{key} alias exists for plain keys
    if not key.startswith("contact.") and normalized:
        contact_key = f"contact.{normalized}"
        result.setdefault(contact_key, value)
    # Store normalized alias
    if normalized:
        result.setdefault(normalized, value)
        result.setdefault(f"contact.{normalized}", value)


async def custom_fields_to_dict(custom_fields_raw: Any) -> Dict[str, Any]:
    """
    Convert GHL customFields payloads (list/dict) into a normalized dict.
    
    The returned dict contains multiple aliases per field so callers can look up
    values using either ``contact.lead_source`` or ``lead_source`` etc.
    """
    result: Dict[str, Any] = {}
    if not custom_fields_raw:
        return result
    
    reverse_id_map: Dict[str, str] = {}
    try:
        field_id_map = await get_custom_field_ids()
        reverse_id_map = {field_id: key for key, field_id in field_id_map.items()}
    except Exception as e:
        logger.debug(f"Could not build reverse field ID map: {e}")
    
    if isinstance(custom_fields_raw, dict):
        for key, value in custom_fields_raw.items():
            _store_field(result, key, value)
        return result
    
    if isinstance(custom_fields_raw, list):
        for field in custom_fields_raw:
            if not isinstance(field, dict):
                continue
            value = (
                field.get("value") or
                field.get("field_value") or
                field.get("fieldValue") or
                field.get("valueText") or
                field.get("fieldValueText")
            )
            possible_keys = [
                field.get("key"),
                field.get("fieldKey"),
                field.get("name"),
                field.get("label"),
                reverse_id_map.get(field.get("id") or field.get("customFieldId"))
            ]
            for candidate in possible_keys:
                if candidate:
                    _store_field(result, candidate, value)
        return result
    
    return result

