"""
Final test using update_custom_fields method.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.utils.logging import logger


async def test_final():
    """Test using update_custom_fields method"""
    ghl = GHLClient()
    contact_id = "di1w41QEIczwQJ6cYoXp"
    
    print("\n" + "="*60)
    print("FINAL CUSTOM FIELDS TEST - Using update_custom_fields")
    print("="*60)
    
    # Test data
    test_fields = {
        "contact.vapi_called": "true",
        "contact.sms_consent": "true",
        "contact.lead_quality_score": "92",
        "contact.ai_call_summary": "Test summary - Custom fields working!"
    }
    
    print("\n📝 Writing test fields:")
    for key, value in test_fields.items():
        print(f"   • {key}: {value}")
    
    try:
        # Try the dedicated update_custom_fields method
        result = await ghl.update_custom_fields(contact_id, test_fields)
        print(f"\n✅ Update response: {result}")
    except Exception as e:
        print(f"\n❌ update_custom_fields failed: {e}")
        print("\n📝 Trying regular update_contact method...")
        # Fallback to regular update
        from src.utils.ghl_fields import build_custom_fields_array
        custom_fields_array = build_custom_fields_array({
            k.replace("contact.", ""): v for k, v in test_fields.items()
        })
        result = await ghl.update_contact(contact_id, {"customFields": custom_fields_array})
        print(f"✅ Regular update response: {result}")
    
    # Wait and verify
    print("\n🔍 Waiting 3 seconds, then verifying...")
    await asyncio.sleep(3)
    
    contact = await ghl.get_contact(contact_id=contact_id)
    if isinstance(contact, dict) and "contact" in contact:
        contact = contact["contact"]
    
    custom_fields_raw = contact.get("customFields", [])
    print(f"\n📋 Custom fields found: {len(custom_fields_raw) if isinstance(custom_fields_raw, list) else 'dict'}")
    
    if isinstance(custom_fields_raw, list):
        for field in custom_fields_raw:
            if isinstance(field, dict):
                key = field.get("key") or field.get("field", "")
                value = field.get("value") or field.get("field_value", "")
                if key in test_fields or value:
                    print(f"   ✅ {key}: {value}")
    elif isinstance(custom_fields_raw, dict):
        for key, value in custom_fields_raw.items():
            if key in test_fields or value:
                print(f"   ✅ {key}: {value}")


if __name__ == "__main__":
    asyncio.run(test_final())

