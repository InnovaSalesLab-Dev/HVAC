"""
Test updating custom fields by merging with existing fields.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.utils.logging import logger


async def test_merge_fields():
    """Test by merging new fields with existing ones"""
    ghl = GHLClient()
    contact_id = "di1w41QEIczwQJ6cYoXp"
    
    print("\n" + "="*60)
    print("TEST: MERGE NEW FIELDS WITH EXISTING")
    print("="*60)
    
    # Get contact with existing fields
    print("\n📞 Step 1: Fetching contact with existing fields...")
    contact = await ghl.get_contact(contact_id=contact_id)
    if isinstance(contact, dict) and "contact" in contact:
        contact = contact["contact"]
    
    existing_fields_raw = contact.get("customFields", [])
    print(f"   Found {len(existing_fields_raw)} existing custom fields")
    
    # Parse existing fields
    existing_fields_dict = {}
    existing_fields_array = []
    if isinstance(existing_fields_raw, list):
        for field in existing_fields_raw:
            if isinstance(field, dict):
                key = field.get("key") or field.get("field", "")
                value = field.get("value") or field.get("field_value", "")
                if key:
                    existing_fields_dict[key] = value
                    existing_fields_array.append({"field": key, "value": value})
    
    print(f"   Parsed {len(existing_fields_array)} existing fields")
    
    # Add new test fields
    print("\n📝 Step 2: Adding new test fields...")
    new_fields = {
        "contact.vapi_called": "true",
        "contact.sms_consent": "true",
        "contact.lead_quality_score": "92",
        "contact.ai_call_summary": "Test summary - Dummy data added successfully!"
    }
    
    # Merge: update existing or add new
    merged_fields = existing_fields_array.copy()
    for key, value in new_fields.items():
        # Check if field already exists
        found = False
        for i, field in enumerate(merged_fields):
            if field.get("field") == key:
                merged_fields[i]["value"] = value
                found = True
                break
        if not found:
            merged_fields.append({"field": key, "value": value})
    
    print(f"   Total fields to send: {len(merged_fields)}")
    print(f"   New/updated fields:")
    for key, value in new_fields.items():
        print(f"     • {key}: {value[:40]}")
    
    # Update with merged fields
    print("\n💾 Step 3: Updating contact with merged fields...")
    try:
        result = await ghl.update_contact(contact_id, {"customFields": merged_fields})
        print(f"✅ Update successful!")
        print(f"   Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"❌ Update failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verify
    print("\n🔍 Step 4: Verifying after 3 seconds...")
    await asyncio.sleep(3)
    
    updated_contact = await ghl.get_contact(contact_id=contact_id)
    if isinstance(updated_contact, dict) and "contact" in updated_contact:
        updated_contact = updated_contact["contact"]
    
    updated_fields_raw = updated_contact.get("customFields", [])
    print(f"   Found {len(updated_fields_raw)} custom fields in response")
    
    # Check our test fields
    print("\n✅ Verification:")
    updated_fields_dict = {}
    if isinstance(updated_fields_raw, list):
        for field in updated_fields_raw:
            if isinstance(field, dict):
                key = field.get("key") or field.get("field", "")
                value = field.get("value") or field.get("field_value", "")
                updated_fields_dict[key] = value
    
    all_passed = True
    for key, expected_value in new_fields.items():
        actual_value = updated_fields_dict.get(key)
        if str(actual_value) == str(expected_value):
            print(f"   ✅ {key}: {actual_value}")
        else:
            print(f"   ❌ {key}: expected '{expected_value}', got '{actual_value}'")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All fields saved and verified successfully!")
    else:
        print("\n⚠️  Some fields didn't save. Check GHL dashboard manually.")
        print("\n📋 All custom fields on contact:")
        for key, value in list(updated_fields_dict.items())[:10]:
            print(f"   • {key}: {value[:50]}")


if __name__ == "__main__":
    asyncio.run(test_merge_fields())

