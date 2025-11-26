"""
Test custom fields with the actual field keys from GHL.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.utils.logging import logger


async def test_with_actual_keys():
    """Test using actual field keys from GHL"""
    ghl = GHLClient()
    contact_id = "di1w41QEIczwQJ6cYoXp"
    
    print("\n" + "="*60)
    print("TESTING WITH ACTUAL GHL FIELD KEYS")
    print("="*60)
    
    # Get actual field keys
    print("\n📋 Fetching actual custom field keys from GHL...")
    fields = await ghl.get_custom_fields()
    
    # Map expected names to actual keys
    field_mapping = {}
    for field in fields:
        key = field.get("fieldKey") or field.get("key", "")
        name = field.get("name", "").lower()
        
        # Match by name patterns
        if "ai call summary" in name or "call summary" in name:
            if "ai_call_summary" not in field_mapping or "ai" in name:
                field_mapping["ai_call_summary"] = key
        elif "sms consent" in name:
            field_mapping["sms_consent"] = key
        elif "vapi called" in name:
            field_mapping["vapi_called"] = key
        elif "vapi call id" in name or "call id" in name:
            field_mapping["vapi_call_id"] = key
        elif "lead quality" in name:
            field_mapping["lead_quality_score"] = key
        elif "equipment type" in name:
            field_mapping["equipment_type_tags"] = key
        elif "call duration" in name:
            field_mapping["call_duration"] = key
        elif "sms fallback sent" in name:
            field_mapping["sms_fallback_sent"] = key
        elif "appointment pending" in name:
            field_mapping["appointment_pending"] = key
    
    print("\n📋 Found field mappings:")
    for expected, actual in field_mapping.items():
        print(f"   {expected} → {actual}")
    
    if not field_mapping:
        print("❌ No matching fields found. Creating test with common keys...")
        # Use common patterns
        field_mapping = {
            "vapi_called": "contact.contactvapi_called",
            "sms_consent": "contact.contactsms_consent",
            "ai_call_summary": "contact.contactai_call_summary"
        }
    
    # Test data with actual keys
    print("\n📝 Writing dummy data with actual field keys...")
    test_data = [
        {"field": field_mapping.get("vapi_called", "contact.vapi_called"), "value": "true"},
        {"field": field_mapping.get("sms_consent", "contact.sms_consent"), "value": "true"},
        {"field": field_mapping.get("lead_quality_score", "contact.lead_quality_score"), "value": "92"},
        {"field": field_mapping.get("ai_call_summary", "contact.ai_call_summary"), "value": "Test summary - Custom fields working!"}
    ]
    
    # Filter out None values
    test_data = [d for d in test_data if d["field"] and not d["field"].endswith("None")]
    
    print(f"\n   Sending {len(test_data)} fields:")
    for item in test_data:
        print(f"     {item['field']}: {item['value']}")
    
    try:
        result = await ghl.update_contact(contact_id, {"customFields": test_data})
        print(f"\n✅ Update successful! Response: {result.get('succeded', 'N/A')}")
    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        return
    
    # Verify
    print("\n🔍 Verifying after 3 seconds...")
    await asyncio.sleep(3)
    
    contact = await ghl.get_contact(contact_id=contact_id)
    if isinstance(contact, dict) and "contact" in contact:
        contact = contact["contact"]
    
    custom_fields_raw = contact.get("customFields", [])
    print(f"\n📋 Custom fields found: {len(custom_fields_raw) if isinstance(custom_fields_raw, list) else 'dict'}")
    
    if isinstance(custom_fields_raw, list):
        found_count = 0
        for field in custom_fields_raw:
            if isinstance(field, dict):
                key = field.get("key") or field.get("field", "")
                value = field.get("value") or field.get("field_value", "")
                if value and key in [d["field"] for d in test_data]:
                    print(f"   ✅ {key}: {value[:50]}")
                    found_count += 1
        if found_count == 0:
            print("   ⚠️  No matching fields found in response")
            print("   All fields in response:")
            for field in custom_fields_raw[:10]:
                print(f"     {field}")
    else:
        print(f"   Fields: {custom_fields_raw}")


if __name__ == "__main__":
    asyncio.run(test_with_actual_keys())

