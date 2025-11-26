"""
Script to add checkBusinessHours function to existing Vapi assistants.
This updates both inbound and outbound assistants with the new business hours function.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.vapi import VapiClient
from src.integrations.vapi.assistants import create_inbound_assistant, create_outbound_assistant
from src.config import settings


async def add_business_hours_function():
    """Add checkBusinessHours function to existing assistants"""
    vapi = VapiClient()
    
    # Get assistant IDs from environment
    inbound_assistant_id = settings.vapi_inbound_assistant_id
    outbound_assistant_id = settings.vapi_outbound_assistant_id
    
    if not inbound_assistant_id or not outbound_assistant_id:
        print("❌ Error: Assistant IDs not found in .env")
        print("\nPlease set in .env:")
        if not inbound_assistant_id:
            print("  VAPI_INBOUND_ASSISTANT_ID=your_inbound_assistant_id")
        if not outbound_assistant_id:
            print("  VAPI_OUTBOUND_ASSISTANT_ID=your_outbound_assistant_id")
        print("\nYou can find these IDs in your Vapi dashboard.")
        return
    
    # Get server URL
    server_url = settings.webhook_base_url or "https://scott-valley-hvac-api.fly.dev"
    
    print("=" * 70)
    print("🔄 ADDING BUSINESS HOURS FUNCTION TO VAPI ASSISTANTS")
    print("=" * 70)
    print(f"\nServer URL: {server_url}")
    print(f"Inbound Assistant ID: {inbound_assistant_id}")
    print(f"Outbound Assistant ID: {outbound_assistant_id}\n")
    
    # Get current assistant configs
    try:
        print("📥 Fetching current assistant configurations...")
        inbound_assistant = await vapi.get_assistant(inbound_assistant_id)
        outbound_assistant = await vapi.get_assistant(outbound_assistant_id)
        print("   ✅ Fetched successfully\n")
    except Exception as e:
        print(f"❌ Error fetching assistants: {e}")
        print("   Make sure assistant IDs are correct in .env")
        return
    
    # Generate new configs with business hours function
    print("📝 Generating updated configurations with business hours function...")
    inbound_config = await create_inbound_assistant(server_url)
    outbound_config = await create_outbound_assistant(server_url)
    
    # Update Inbound Assistant
    print("\n1️⃣  Updating Inbound Assistant...")
    try:
        # Update with new functions array (includes checkBusinessHours)
        update_data = {
            "functions": inbound_config.get("functions", [])
        }
        await vapi.update_assistant(inbound_assistant_id, update_data)
        print("   ✅ Inbound assistant updated successfully!")
        print("   📋 Added function: checkBusinessHours")
        print("   📋 Total functions:", len(inbound_config.get("functions", [])))
    except Exception as e:
        print(f"   ❌ Error updating inbound assistant: {str(e)}")
        print(f"   Error details: {e}")
        return
    
    # Update Outbound Assistant
    print("\n2️⃣  Updating Outbound Assistant...")
    try:
        # Update with new functions array (includes checkBusinessHours)
        update_data = {
            "functions": outbound_config.get("functions", [])
        }
        await vapi.update_assistant(outbound_assistant_id, update_data)
        print("   ✅ Outbound assistant updated successfully!")
        print("   📋 Added function: checkBusinessHours")
        print("   📋 Total functions:", len(outbound_config.get("functions", [])))
    except Exception as e:
        print(f"   ❌ Error updating outbound assistant: {str(e)}")
        print(f"   Error details: {e}")
        return
    
    print("\n" + "=" * 70)
    print("✅ BUSINESS HOURS FUNCTION ADDED SUCCESSFULLY!")
    print("=" * 70)
    print("\n📊 What's Now Available:")
    print("  ✅ checkBusinessHours function in both assistants")
    print("  ✅ Returns current date/time in Pacific Time")
    print("  ✅ Checks if it's business hours (Mon-Fri, 8 AM - 4:30 PM)")
    print("  ✅ Prevents booking appointments in the past")
    print("\n🎯 Next Steps:")
    print("  1. Test a call to verify the function is working")
    print("  2. The assistant should call checkBusinessHours before checking calendar")
    print("  3. Monitor call logs to ensure correct date usage")
    print("\n💡 The assistant will now:")
    print("   • Always get the current date before checking calendar")
    print("   • Use correct dates (no past dates)")
    print("   • Know if it's business hours")


if __name__ == "__main__":
    asyncio.run(add_business_hours_function())

