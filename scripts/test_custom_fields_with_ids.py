"""
Test custom fields update using field IDs (correct GHL API format).
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.utils.ghl_fields import build_custom_fields_array, get_custom_field_ids
from src.utils.logging import logger


async def test_with_field_ids():
    """Test updating custom fields using field IDs"""
    ghl = GHLClient()
    contact_id = "di1w41QEIczwQJ6cYoXp"
    
    print("\n" + "="*60)
    print("TEST: CUSTOM FIELDS WITH FIELD IDs (CORRECT FORMAT)")
    print("="*60)
    
    # Step 1: Get field ID mappings
    print("\n📋 Step 1: Fetching custom field IDs from GHL...")
    field_id_map = await get_custom_field_ids(ghl)
    
    if not field_id_map:
        print("❌ No field IDs found. Make sure custom fields exist in GHL.")
        return
    
    print(f"✅ Found {len(field_id_map)} field ID mappings")
    print("\n   Field mappings (first 5):")
    for i, (key, field_id) in enumerate(list(field_id_map.items())[:5]):
        print(f"     {key} → {field_id[:20]}...")
    
    # Step 2: Prepare test data
    print("\n📝 Step 2: Preparing test data...")
    test_fields = {
        "vapi_called": "true",
        "sms_consent": "true",
        "lead_quality_score": "92",
        "ai_call_summary": "Test summary - Using field IDs format"
    }
    
    print("   Test fields to update:")
    for key, value in test_fields.items():
        normalized_key = f"contact.{key}"
        field_id = field_id_map.get(normalized_key, "NOT FOUND")
        print(f"     • {key} ({normalized_key})")
        print(f"       ID: {field_id[:30] if field_id != 'NOT FOUND' else 'NOT FOUND'}")
        print(f"       Value: {value}")
    
    # Step 3: Build custom fields array with IDs
    print("\n💾 Step 3: Building custom fields array with field IDs...")
    custom_fields_array = await build_custom_fields_array(test_fields, use_field_ids=True)
    
    print(f"   Built {len(custom_fields_array)} field entries:")
    for field in custom_fields_array:
        if "id" in field:
            print(f"     ✅ Using ID: {field['id'][:30]}... = {field['value']}")
        else:
            print(f"     ⚠️  Using field key: {field.get('field')} = {field.get('value')}")
    
    # Step 4: Update contact
    print("\n🔄 Step 4: Updating contact via API...")
    try:
        result = await ghl.update_contact(contact_id, {"customFields": custom_fields_array})
        print(f"✅ API update successful!")
        print(f"   Response: {result.get('succeded', 'N/A')}")
    except Exception as e:
        print(f"❌ API update failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Verify
    print("\n🔍 Step 5: Verifying after 3 seconds...")
    await asyncio.sleep(3)
    
    contact = await ghl.get_contact(contact_id=contact_id)
    if isinstance(contact, dict) and "contact" in contact:
        contact = contact["contact"]
    
    custom_fields_raw = contact.get("customFields", [])
    print(f"   Found {len(custom_fields_raw)} custom fields in response")
    
    # Parse response
    updated_fields = {}
    if isinstance(custom_fields_raw, list):
        for field in custom_fields_raw:
            if isinstance(field, dict):
                key = field.get("key") or field.get("field", "")
                value = field.get("value") or field.get("field_value", "")
                if key and value:
                    updated_fields[key] = value
    
    # Verify
    print("\n✅ Verification Results:")
    all_passed = True
    for key, expected_value in test_fields.items():
        normalized_key = f"contact.{key}"
        actual_value = updated_fields.get(normalized_key)
        
        if str(actual_value) == str(expected_value):
            print(f"   ✅ {key}: {actual_value}")
        else:
            print(f"   ❌ {key}: expected '{expected_value}', got '{actual_value}'")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All fields saved successfully using field IDs!")
    else:
        print("\n⚠️  Fields didn't save. This may be a GHL API limitation.")
        print("   💡 Solution: Use GHL automation webhook (see docs/GHL_CUSTOM_FIELDS_AUTOMATION_SETUP.md)")
    
    # Show all fields
    if updated_fields:
        print("\n📋 All custom fields on contact:")
        for key, value in list(updated_fields.items())[:10]:
            display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            print(f"   • {key}: {display_value}")


if __name__ == "__main__":
    asyncio.run(test_with_field_ids())

