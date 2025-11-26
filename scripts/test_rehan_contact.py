"""
Test custom fields on Rehan contact with dummy data.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.utils.ghl_fields import build_custom_fields_array
from src.utils.logging import logger


async def test_rehan_contact():
    """Test custom fields on Rehan contact"""
    ghl = GHLClient()
    
    # Contact ID from earlier logs
    contact_id = "di1w41QEIczwQJ6cYoXp"
    
    print("\n" + "="*60)
    print("TESTING CUSTOM FIELDS ON REHAN CONTACT")
    print("="*60)
    
    # Step 1: Get current contact
    print("\n📞 Step 1: Fetching contact...")
    try:
        contact = await ghl.get_contact(contact_id=contact_id)
        if not contact:
            print(f"❌ Contact {contact_id} not found")
            return
        
        if isinstance(contact, dict) and "contact" in contact:
            contact = contact["contact"]
        
        name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
        phone = contact.get("phone") or contact.get("phoneNumber", "N/A")
        email = contact.get("email", "N/A")
        
        print(f"✅ Contact found: {name}")
        print(f"   Phone: {phone}")
        print(f"   Email: {email}")
        
        # Show current custom fields
        custom_fields_raw = contact.get("customFields", [])
        print(f"\n📋 Current custom fields ({len(custom_fields_raw) if isinstance(custom_fields_raw, list) else 'dict'}):")
        
        current_fields = {}
        if isinstance(custom_fields_raw, list):
            for field in custom_fields_raw:
                if isinstance(field, dict):
                    key = field.get("key") or field.get("field") or field.get("name", "")
                    value = field.get("value") or field.get("field_value", "")
                    current_fields[key] = value
        elif isinstance(custom_fields_raw, dict):
            current_fields = custom_fields_raw
        
        if current_fields:
            for key, value in current_fields.items():
                print(f"   • {key}: {value}")
        else:
            print("   (No custom fields set)")
        
    except Exception as e:
        print(f"❌ Error fetching contact: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Prepare dummy test data
    print("\n📝 Step 2: Preparing dummy test data...")
    test_timestamp = datetime.now().isoformat()
    
    dummy_data = {
        "ai_call_summary": f"Test call summary - Dummy data added on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Customer inquired about heating system repair. Scheduled diagnostic appointment.",
        "lead_quality_score": "92",
        "vapi_called": "true",
        "vapi_call_id": "test-call-12345-dummy",
        "sms_consent": "true",
        "equipment_type_tags": "Furnace, Heat Pump, Air Handler",
        "call_duration": "245",
        "sms_fallback_sent": "false",
        "appointment_pending": "true",
        "appointment_start_time": "2025-11-25 10:00 AM",
        "appointment_end_time": "2025-11-25 11:00 AM"
    }
    
    print("   Dummy data to write:")
    for key, value in dummy_data.items():
        print(f"   • {key}: {value[:50]}{'...' if len(str(value)) > 50 else ''}")
    
    # Step 3: Write dummy data
    print("\n💾 Step 3: Writing dummy data to contact...")
    try:
            custom_fields_array = build_custom_fields_array(dummy_data)
            print(f"   Built {len(custom_fields_array)} custom field entries")
            print("\n   Custom fields array format:")
            for field in custom_fields_array[:3]:  # Show first 3
                print(f"     {field}")
            if len(custom_fields_array) > 3:
                print(f"     ... and {len(custom_fields_array) - 3} more")
            
            # Try updating with customFields array
            result = await ghl.update_contact(
                contact_id=contact_id,
                contact_data={
                    "customFields": custom_fields_array
                }
            )
            
            print(f"\n   API Response: {result}")
            print("✅ Custom fields update request sent!")
        
    except Exception as e:
        print(f"❌ Error updating contact: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Verify data was saved
    print("\n🔍 Step 4: Verifying data was saved...")
    await asyncio.sleep(3)  # Wait for GHL to process
    
    try:
        updated_contact = await ghl.get_contact(contact_id=contact_id)
        if isinstance(updated_contact, dict) and "contact" in updated_contact:
            updated_contact = updated_contact["contact"]
        
        updated_fields_raw = updated_contact.get("customFields", [])
        updated_fields = {}
        
        if isinstance(updated_fields_raw, list):
            for field in updated_fields_raw:
                if isinstance(field, dict):
                    key = field.get("key") or field.get("field") or field.get("name", "")
                    value = field.get("value") or field.get("field_value", "")
                    updated_fields[key] = value
        elif isinstance(updated_fields_raw, dict):
            updated_fields = updated_fields_raw
        
        print("\n✅ Verification Results:")
        all_passed = True
        for key, expected_value in dummy_data.items():
            normalized_key = f"contact.{key}"
            actual_value = updated_fields.get(normalized_key) or updated_fields.get(key)
            
            # For text fields, check if value contains expected content
            if key == "ai_call_summary":
                if actual_value and "Test call summary" in str(actual_value):
                    print(f"   ✅ {key}: Saved correctly")
                else:
                    print(f"   ⚠️  {key}: Value mismatch")
                    all_passed = False
            else:
                if str(actual_value) == str(expected_value):
                    print(f"   ✅ {key}: {actual_value}")
                else:
                    print(f"   ⚠️  {key}: expected '{expected_value}', got '{actual_value}'")
                    all_passed = False
        
        if all_passed:
            print("\n🎉 All dummy data saved and verified successfully!")
        else:
            print("\n⚠️  Some fields may not have saved correctly. Check GHL dashboard.")
        
        # Show all updated fields
        print("\n📋 All custom fields on contact now:")
        for key, value in updated_fields.items():
            display_value = str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
            print(f"   • {key}: {display_value}")
        
    except Exception as e:
        print(f"❌ Error verifying: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\n💡 Check GHL dashboard to see the dummy data:")
    print(f"   Contact: {name} (ID: {contact_id})")
    print("   Go to Contacts → Rehan → Custom Fields section")


if __name__ == "__main__":
    asyncio.run(test_rehan_contact())

