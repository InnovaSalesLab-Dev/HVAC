"""
GHL Automation-based custom field updates.
Use this as a fallback when direct API updates fail.
"""
from typing import Dict, Any, Optional
import httpx
from src.config import settings
from src.utils.logging import logger


async def trigger_custom_fields_update_webhook(
    contact_id: str,
    custom_fields: Dict[str, Any],
    webhook_url: Optional[str] = None
) -> bool:
    """
    Trigger GHL automation webhook to update custom fields.
    This is more reliable than direct API updates.
    
    Args:
        contact_id: GHL contact ID
        custom_fields: Dictionary of field keys and values
        webhook_url: GHL inbound webhook URL (if None, uses settings)
    
    Returns:
        True if webhook triggered successfully
    """
    if not webhook_url:
        webhook_url = settings.ghl_custom_fields_webhook_url
    
    if not webhook_url:
        logger.warning("⚠️  GHL custom fields webhook URL not configured")
        return False
    
    try:
        payload = {
            "contact_id": contact_id,
            "location_id": settings.ghl_location_id,
            "custom_fields": custom_fields
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"✅ Custom fields webhook triggered for contact {contact_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to trigger custom fields webhook: {e}")
        return False

