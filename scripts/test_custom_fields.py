"""
Test script to verify GHL custom fields are working correctly.
Tests reading, writing, and field key normalization.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.utils.ghl_fields import normalize_ghl_field_key, build_custom_fields_array
from src.utils.logging import logger


async def test_list_custom_fields():
    """Test listing all custom fields in GHL"""
    print("\n" + "="*60)
    print("TEST 1: List All Custom Fields")
    print("="*60)
    
    ghl = GHLClient()
    try:
        fields = await ghl.get_custom_fields()
        print(f"✅ Found {len(fields)} custom fields")
        
        # Expected fields
        expected_fields = [
            "ai_call_summary",
            "call_transcript_url",
            "sms_consent",
            "lead_quality_score",
            "equipment_type_tags",
            "call_duration",
            "vapi_called",
            "vapi_call_id",
            "sms_fallback_sent",
            "sms_fallback_date",
            "sms_fallback_reason",
            "appointment_pending",
            "appointment_start_time",
            "appointment_end_time"
        ]
        
        print("\n📋 Checking for expected fields:")
        found_fields = {}
        for field in fields:
            field_key = field.get("key", "").replace("contact.", "")
            found_fields[field_key] = field
        
        missing_fields = []
        for expected_key in expected_fields:
            normalized = normalize_ghl_field_key(expected_key)
            if normalized in [f.get("key") for f in fields]:
                print(f"  ✅ {expected_key} ({normalized})")
            else:
                print(f"  ❌ {expected_key} - MISSING")
                missing_fields.append(expected_key)
        
        if missing_fields:
            print(f"\n⚠️  Missing {len(missing_fields)} fields: {missing_fields}")
        else:
            print("\n✅ All expected fields found!")
        
        return fields, found_fields
    except Exception as e:
        print(f"❌ Error listing custom fields: {e}")
        return [], {}


async def test_read_custom_fields(contact_id: str):
    """Test reading custom fields from a contact"""
    print("\n" + "="*60)
    print("TEST 2: Read Custom Fields from Contact")
    print("="*60)
    
    ghl = GHLClient()
    try:
        contact = await ghl.get_contact(contact_id=contact_id)
        if not contact:
            print(f"❌ Contact {contact_id} not found")
            return None
        
        # Handle nested contact structure
        if isinstance(contact, dict) and "contact" in contact:
            contact = contact["contact"]
        
        print(f"✅ Contact found: {contact.get('firstName', '')} {contact.get('lastName', '')}")
        
        custom_fields_raw = contact.get("customFields", [])
        print(f"📋 Custom fields format: {type(custom_fields_raw).__name__}")
        
        # Parse custom fields
        custom_fields = {}
        if isinstance(custom_fields_raw, list):
            print("  Parsing as array format...")
            for field in custom_fields_raw:
                if isinstance(field, dict):
                    key = field.get("key") or field.get("field") or field.get("name", "")
                    value = field.get("value") or field.get("field_value", "")
                    custom_fields[key] = value
        elif isinstance(custom_fields_raw, dict):
            print("  Parsing as dict format...")
            custom_fields = custom_fields_raw
        
        print(f"\n📋 Found {len(custom_fields)} custom field values:")
        for key, value in custom_fields.items():
            print(f"  • {key}: {value}")
        
        return custom_fields
    except Exception as e:
        print(f"❌ Error reading custom fields: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_write_custom_fields(contact_id: str):
    """Test writing custom fields to a contact"""
    print("\n" + "="*60)
    print("TEST 3: Write Custom Fields to Contact")
    print("="*60)
    
    ghl = GHLClient()
    try:
        # Test data
        test_fields = {
            "ai_call_summary": "Test call summary - Custom fields test",
            "lead_quality_score": "85",
            "vapi_called": "true",
            "sms_consent": "true"
        }
        
        print(f"📝 Writing test fields to contact {contact_id}:")
        for key, value in test_fields.items():
            print(f"  • {key}: {value}")
        
        # Build custom fields array
        custom_fields_array = build_custom_fields_array(test_fields)
        print(f"\n📦 Built custom fields array ({len(custom_fields_array)} fields):")
        for field in custom_fields_array:
            print(f"  • {field.get('key')}: {field.get('field_value')}")
        
        # Update contact
        result = await ghl.update_contact(
            contact_id=contact_id,
            contact_data={
                "customFields": custom_fields_array
            }
        )
        
        print("\n✅ Custom fields updated successfully!")
        
        # Verify by reading back
        print("\n🔍 Verifying by reading back...")
        await asyncio.sleep(2)  # Wait for GHL to process
        updated_fields = await test_read_custom_fields(contact_id)
        
        # Check if our test values are there
        print("\n✅ Verification:")
        for key, expected_value in test_fields.items():
            normalized_key = normalize_ghl_field_key(key)
            actual_value = updated_fields.get(normalized_key) or updated_fields.get(key)
            if str(actual_value) == str(expected_value):
                print(f"  ✅ {key}: {actual_value} (matches)")
            else:
                print(f"  ⚠️  {key}: expected '{expected_value}', got '{actual_value}'")
        
        return True
    except Exception as e:
        print(f"❌ Error writing custom fields: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_field_normalization():
    """Test field key normalization"""
    print("\n" + "="*60)
    print("TEST 4: Field Key Normalization")
    print("="*60)
    
    test_cases = [
        ("sms_consent", "contact.sms_consent"),
        ("contact.sms_consent", "contact.sms_consent"),
        ("ai_call_summary", "contact.ai_call_summary"),
        ("contact.vapi_called", "contact.vapi_called"),
    ]
    
    print("Testing normalize_ghl_field_key function:")
    all_passed = True
    for input_key, expected_output in test_cases:
        result = normalize_ghl_field_key(input_key)
        if result == expected_output:
            print(f"  ✅ '{input_key}' → '{result}'")
        else:
            print(f"  ❌ '{input_key}' → '{result}' (expected '{expected_output}')")
            all_passed = False
    
    if all_passed:
        print("\n✅ All normalization tests passed!")
    else:
        print("\n❌ Some normalization tests failed!")
    
    return all_passed


async def main():
    """Run all custom field tests"""
    print("\n" + "="*60)
    print("GHL CUSTOM FIELDS TEST SUITE")
    print("="*60)
    
    # Test 1: List custom fields
    fields, found_fields = await test_list_custom_fields()
    
    # Test 4: Field normalization
    await test_field_normalization()
    
    # Test 2 & 3: Read/Write (requires contact ID)
    print("\n" + "="*60)
    print("TEST 2 & 3: Read/Write Custom Fields")
    print("="*60)
    print("⚠️  These tests require a contact ID.")
    print("   You can:")
    print("   1. Provide a contact ID as command line argument")
    print("   2. Create a test contact first")
    print("   3. Use an existing contact ID")
    
    if len(sys.argv) > 1:
        contact_id = sys.argv[1]
        print(f"\n📞 Using contact ID: {contact_id}")
        
        # Test reading
        await test_read_custom_fields(contact_id)
        
        # Test writing
        await test_write_custom_fields(contact_id)
    else:
        print("\n💡 To test read/write, run:")
        print("   python scripts/test_custom_fields.py <contact_id>")
        print("\n   Example:")
        print("   python scripts/test_custom_fields.py di1w41QEIczwQJ6cYoXp")
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

