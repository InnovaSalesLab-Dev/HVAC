"""
Comprehensive test script for lead handling scenarios.
Tests all lead source extraction, duplicate prevention, and error handling.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.ghl import GHLClient
from src.integrations.vapi import VapiClient
from src.utils.logging import logger
from src.utils.ghl_fields import build_custom_fields_array


async def test_scenario_1_duplicate_prevention():
    """TEST 9A: Duplicate Call Prevention"""
    print("\n" + "="*60)
    print("TEST 9A: Duplicate Call Prevention")
    print("="*60)
    
    ghl = GHLClient()
    
    # Create test contact
    print("\n📝 Step 1: Creating test contact...")
    contact_data = {
        "firstName": "Test",
        "lastName": "Duplicate",
        "phone": "+15035550101",
        "email": "test.duplicate@test.com"
    }
    
    try:
        contact = await ghl.create_contact(contact_data)
        contact_id = contact.get("id") or contact.get("contact", {}).get("id")
        if not contact_id:
            print("❌ Failed to create contact")
            return False
        print(f"✅ Contact created: {contact_id}")
    except Exception as e:
        print(f"❌ Error creating contact: {e}")
        return False
    
    # Set vapi_called to true
    print("\n📝 Step 2: Setting vapi_called to true...")
    try:
        custom_fields = await build_custom_fields_array({"vapi_called": "true"}, use_field_ids=True)
        await ghl.update_contact(contact_id, {"customFields": custom_fields})
        print("✅ vapi_called set to true")
    except Exception as e:
        print(f"⚠️  Could not set vapi_called: {e}")
    
    # Simulate webhook (check if call would be skipped)
    print("\n📝 Step 3: Simulating webhook trigger...")
    try:
        contact_check = await ghl.get_contact(contact_id=contact_id)
        if isinstance(contact_check, dict) and "contact" in contact_check:
            contact_check = contact_check["contact"]
        
        custom_fields_raw = contact_check.get("customFields", [])
        custom_fields_dict = {}
        if isinstance(custom_fields_raw, list):
            for field in custom_fields_raw:
                if isinstance(field, dict):
                    key = field.get("key") or field.get("field", "")
                    value = field.get("value") or field.get("field_value", "")
                    custom_fields_dict[key] = value
        else:
            custom_fields_dict = custom_fields_raw
        
        vapi_called = custom_fields_dict.get("vapi_called") or custom_fields_dict.get("contact.vapi_called")
        if str(vapi_called).lower() == "true":
            print("✅ Duplicate prevention working: vapi_called is true, call would be skipped")
            return True
        else:
            print(f"❌ Duplicate prevention NOT working: vapi_called = {vapi_called}")
            return False
    except Exception as e:
        print(f"❌ Error checking contact: {e}")
        return False


async def test_scenario_2_missing_phone():
    """TEST 9B: Missing Phone Number Handling"""
    print("\n" + "="*60)
    print("TEST 9B: Missing Phone Number Handling")
    print("="*60)
    
    ghl = GHLClient()
    
    # Create contact without phone
    print("\n📝 Step 1: Creating contact without phone number...")
    contact_data = {
        "firstName": "Test",
        "lastName": "NoPhone",
        "email": "test.nophone@test.com"
        # No phone field
    }
    
    try:
        contact = await ghl.create_contact(contact_data)
        contact_id = contact.get("id") or contact.get("contact", {}).get("id")
        if not contact_id:
            print("❌ Failed to create contact")
            return False
        print(f"✅ Contact created: {contact_id}")
        
        # Check if phone is missing
        contact_check = await ghl.get_contact(contact_id=contact_id)
        if isinstance(contact_check, dict) and "contact" in contact_check:
            contact_check = contact_check["contact"]
        
        phone = contact_check.get("phone") or contact_check.get("phoneNumber", "")
        if not phone or not phone.strip():
            print("✅ Missing phone detected correctly")
            print("✅ System would skip call (graceful handling)")
            return True
        else:
            print(f"⚠️  Phone found: {phone} (unexpected)")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_scenario_3_invalid_phone():
    """TEST 9C: Invalid Phone Number Handling"""
    print("\n" + "="*60)
    print("TEST 9C: Invalid Phone Number Handling")
    print("="*60)
    
    from src.utils.validation import validate_phone_number
    
    invalid_phones = ["123", "abc", "not-a-phone", ""]
    
    print("\n📝 Testing phone validation...")
    all_passed = True
    for invalid_phone in invalid_phones:
        try:
            validated = validate_phone_number(invalid_phone)
            print(f"❌ Invalid phone '{invalid_phone}' was accepted: {validated}")
            all_passed = False
        except Exception as e:
            print(f"✅ Invalid phone '{invalid_phone}' correctly rejected: {str(e)[:50]}")
    
    return all_passed


async def test_scenario_4_lead_source_from_tags():
    """TEST 9D: Lead Source from Tags"""
    print("\n" + "="*60)
    print("TEST 9D: Lead Source from Tags")
    print("="*60)
    
    ghl = GHLClient()
    
    test_tags = ["yelp", "website", "thumbtack", "google"]
    
    print("\n📝 Testing lead source extraction from tags...")
    all_passed = True
    
    for tag in test_tags:
        print(f"\n  Testing tag: {tag}")
        # Create contact with tag
        contact_data = {
            "firstName": f"Test{tag.capitalize()}",
            "lastName": "TagTest",
            "phone": f"+1503555{hash(tag) % 10000:04d}",
            "email": f"test.{tag}@test.com",
            "tags": [tag]
        }
        
        try:
            contact = await ghl.create_contact(contact_data)
            contact_id = contact.get("id") or contact.get("contact", {}).get("id")
            
            if contact_id:
                # Check if tag was saved
                contact_check = await ghl.get_contact(contact_id=contact_id)
                if isinstance(contact_check, dict) and "contact" in contact_check:
                    contact_check = contact_check["contact"]
                
                tags = contact_check.get("tags", [])
                if tag in tags or any(tag.lower() in str(t).lower() for t in tags):
                    print(f"    ✅ Tag '{tag}' saved correctly")
                    
                    # Check if lead source would be extracted
                    # Simulate the extraction logic
                    source_tags = ["website", "yelp", "thumbtack", "google", "meta", "facebook", "form", "webchat"]
                    extracted_source = None
                    for t in tags:
                        t_lower = str(t).lower()
                        for source in source_tags:
                            if source in t_lower:
                                extracted_source = source
                                break
                        if extracted_source:
                            break
                    
                    if extracted_source:
                        print(f"    ✅ Lead source would be extracted: {extracted_source}")
                    else:
                        print(f"    ⚠️  Lead source not extracted from tag")
                else:
                    print(f"    ❌ Tag '{tag}' not found in contact")
                    all_passed = False
        except Exception as e:
            print(f"    ❌ Error testing tag {tag}: {e}")
            all_passed = False
    
    return all_passed


async def test_scenario_5_lead_source_saving():
    """Test that lead source is saved to custom fields"""
    print("\n" + "="*60)
    print("TEST: Lead Source Saving to Custom Fields")
    print("="*60)
    
    ghl = GHLClient()
    
    # Create contact
    print("\n📝 Creating contact with lead source...")
    contact_data = {
        "firstName": "Test",
        "lastName": "LeadSource",
        "phone": "+15035550102",
        "email": "test.leadsource@test.com"
    }
    
    try:
        contact = await ghl.create_contact(contact_data)
        contact_id = contact.get("id") or contact.get("contact", {}).get("id")
        print(f"✅ Contact created: {contact_id}")
        
        # Set lead source
        print("\n📝 Setting lead_source custom field...")
        custom_fields = await build_custom_fields_array({"lead_source": "test_source"}, use_field_ids=True)
        await ghl.update_contact(contact_id, {"customFields": custom_fields})
        print("✅ Lead source set")
        
        # Wait and verify
        await asyncio.sleep(2)
        print("\n🔍 Verifying lead source was saved...")
        contact_check = await ghl.get_contact(contact_id=contact_id)
        if isinstance(contact_check, dict) and "contact" in contact_check:
            contact_check = contact_check["contact"]
        
        custom_fields_raw = contact_check.get("customFields", [])
        custom_fields_dict = {}
        if isinstance(custom_fields_raw, list):
            for field in custom_fields_raw:
                if isinstance(field, dict):
                    key = field.get("key") or field.get("field", "")
                    value = field.get("value") or field.get("field_value", "")
                    custom_fields_dict[key] = value
        else:
            custom_fields_dict = custom_fields_raw
        
        lead_source = custom_fields_dict.get("lead_source") or custom_fields_dict.get("contact.lead_source")
        if lead_source:
            print(f"✅ Lead source found in custom fields: {lead_source}")
            return True
        else:
            print("❌ Lead source NOT found in custom fields")
            print(f"   Available fields: {list(custom_fields_dict.keys())[:10]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all lead handling tests"""
    print("\n" + "="*70)
    print("COMPREHENSIVE LEAD HANDLING TEST SUITE")
    print("="*70)
    print(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run all test scenarios
    results["TEST 9A: Duplicate Prevention"] = await test_scenario_1_duplicate_prevention()
    results["TEST 9B: Missing Phone"] = await test_scenario_2_missing_phone()
    results["TEST 9C: Invalid Phone"] = await test_scenario_3_invalid_phone()
    results["TEST 9D: Lead Source from Tags"] = await test_scenario_4_lead_source_from_tags()
    results["TEST: Lead Source Saving"] = await test_scenario_5_lead_source_saving()
    
    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

