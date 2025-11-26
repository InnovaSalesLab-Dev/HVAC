"""
Direct test of custom fields update with different formats.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.utils.logging import logger


async def test_direct_update():
    """Test updating custom fields with different formats"""
    ghl = GHLClient()
    contact_id = "di1w41QEIczwQJ6cYoXp"
    
    print("\n" + "="*60)
    print("DIRECT CUSTOM FIELDS UPDATE TEST")
    print("="*60)
    
    # Test Format 1: Array with key and field_value
    print("\n📝 Test Format 1: Array with key/field_value")
    format1 = [
        {"key": "contact.vapi_called", "field_value": "true"},
        {"key": "contact.sms_consent", "field_value": "true"},
        {"key": "contact.lead_quality_score", "field_value": "85"}
    ]
    
    try:
        result1 = await ghl.update_contact(contact_id, {"customFields": format1})
        print(f"✅ Format 1 sent. Response keys: {list(result1.keys()) if isinstance(result1, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"❌ Format 1 failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test Format 2: Array with field and value
    print("\n📝 Test Format 2: Array with field/value")
    format2 = [
        {"field": "contact.vapi_called", "value": "true"},
        {"field": "contact.sms_consent", "value": "true"},
        {"field": "contact.lead_quality_score", "value": "85"}
    ]
    
    try:
        result2 = await ghl.update_contact(contact_id, {"customFields": format2})
        print(f"✅ Format 2 sent. Response keys: {list(result2.keys()) if isinstance(result2, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"❌ Format 2 failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test Format 3: Direct dict format
    print("\n📝 Test Format 3: Direct dict")
    format3 = {
        "contact.vapi_called": "true",
        "contact.sms_consent": "true",
        "contact.lead_quality_score": "85"
    }
    
    try:
        result3 = await ghl.update_contact(contact_id, {"customFields": format3})
        print(f"✅ Format 3 sent. Response keys: {list(result3.keys()) if isinstance(result3, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"❌ Format 3 failed: {e}")
    
    await asyncio.sleep(3)
    
    # Read back to see which format worked
    print("\n🔍 Reading back contact to see which format worked...")
    contact = await ghl.get_contact(contact_id=contact_id)
    if isinstance(contact, dict) and "contact" in contact:
        contact = contact["contact"]
    
    custom_fields_raw = contact.get("customFields", [])
    print(f"📋 Custom fields format: {type(custom_fields_raw).__name__}")
    
    if isinstance(custom_fields_raw, list):
        print(f"   Found {len(custom_fields_raw)} fields:")
        for field in custom_fields_raw:
            if isinstance(field, dict):
                print(f"     {field}")
    elif isinstance(custom_fields_raw, dict):
        print(f"   Found {len(custom_fields_raw)} fields:")
        for key, value in custom_fields_raw.items():
            print(f"     {key}: {value}")


if __name__ == "__main__":
    asyncio.run(test_direct_update())

