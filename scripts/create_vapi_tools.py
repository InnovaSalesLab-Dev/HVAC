"""
Create tools in Vapi Dashboard Tools section.
These tools can then be assigned to assistants.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.vapi import VapiClient
from src.config import settings
from src.utils.logging import logger


def get_tool_definitions(server_url: str):
    """Get all tool definitions as API Request type - properties at top level"""
    return [
        {
            "type": "apiRequest",
            "name": "classifyCallType",
            "description": "Analyze conversation to determine call type (service/repair, install/estimate, maintenance, appointment change)",
            "url": f"{server_url}/functions/classify-call-type",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "transcript": {
                        "type": "string",
                        "description": "Full conversation transcript"
                    },
                    "conversation_summary": {
                        "type": "string",
                        "description": "Summary of conversation so far"
                    }
                },
                "required": ["transcript"]
            }
        },
        {
            "type": "apiRequest",
            "name": "checkCalendarAvailability",
            "description": "Check available appointment slots in calendar",
            "url": f"{server_url}/functions/check-calendar-availability",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "service_type": {
                        "type": "string",
                        "enum": ["repair", "installation", "maintenance", "estimate"],
                        "description": "Type of service needed"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for availability check (ISO format)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for availability check (ISO format)"
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Optional calendar ID"
                    }
                },
                "required": ["service_type", "start_date", "end_date"]
            }
        },
        {
            "type": "apiRequest",
            "name": "bookAppointment",
            "description": "Book an appointment in the calendar",
            "url": f"{server_url}/functions/book-appointment",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "Contact ID in GHL"
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Appointment start time (ISO format)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Appointment end time (ISO format)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Appointment title"
                    },
                    "service_type": {
                        "type": "string",
                        "enum": ["repair", "installation", "maintenance", "estimate"]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["emergency", "urgent", "standard", "low"]
                    },
                    "service_address": {
                        "type": "string",
                        "description": "Service address for appointment location"
                    },
                    "reschedule_appointment_id": {
                        "type": "string",
                        "description": "If rescheduling, the ID of existing appointment to cancel before booking new one"
                    }
                },
                "required": ["contact_id", "calendar_id", "start_time", "end_time", "title", "service_type"]
            }
        },
        {
            "type": "apiRequest",
            "name": "cancelAppointment",
            "description": "Cancel an existing appointment in GHL calendar",
            "url": f"{server_url}/functions/cancel-appointment",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "Contact ID of the person whose appointment to cancel"
                    },
                    "appointment_id": {
                        "type": "string",
                        "description": "ID of the appointment to cancel"
                    }
                },
                "required": ["contact_id", "appointment_id"]
            }
        },
        {
            "type": "apiRequest",
            "name": "createContact",
            "description": "Create or update contact in CRM",
            "url": f"{server_url}/functions/create-contact",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Full name"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Phone number (E.164 format)"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address"
                    },
                    "address": {
                        "type": "string",
                        "description": "Service address"
                    },
                    "zip_code": {
                        "type": "string",
                        "description": "ZIP code"
                    },
                    "sms_consent": {
                        "type": "boolean",
                        "description": "SMS consent flag"
                    }
                },
                "required": ["name", "phone"]
            }
        },
        {
            "type": "apiRequest",
            "name": "sendConfirmation",
            "description": "Send SMS or email confirmation",
            "url": f"{server_url}/functions/send-confirmation",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "Contact ID"
                    },
                    "appointment_id": {
                        "type": "string",
                        "description": "Appointment ID"
                    },
                    "message": {
                        "type": "string",
                        "description": "Custom confirmation message"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["sms", "email"],
                        "description": "Confirmation method"
                    }
                },
                "required": ["contact_id", "method"]
            }
        },
        {
            "type": "apiRequest",
            "name": "initiateWarmTransfer",
            "description": "Transfer call to human staff member. Use appropriate staff: Service Specialist, Manager, or Scott (owner). See prompt for phone numbers and when to use each.",
            "url": f"{server_url}/functions/initiate-warm-transfer",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "call_sid": {
                        "type": "string",
                        "description": "Current call SID"
                    },
                    "staff_phone": {
                        "type": "string",
                        "description": "Staff phone number (E.164 format)"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context about the call for staff"
                    }
                },
                "required": ["call_sid", "staff_phone"]
            }
        },
        {
            "type": "apiRequest",
            "name": "logCallSummary",
            "description": "Save call transcript and summary to CRM",
            "url": f"{server_url}/functions/log-call-summary",
            "method": "POST",
            "body": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "Contact ID"
                    },
                    "transcript": {
                        "type": "string",
                        "description": "Full call transcript"
                    },
                    "summary": {
                        "type": "string",
                        "description": "AI-generated call summary"
                    },
                    "call_duration": {
                        "type": "integer",
                        "description": "Call duration in seconds"
                    },
                    "call_type": {
                        "type": "string",
                        "enum": ["service_repair", "install_estimate", "maintenance", "appointment_change", "other"]
                    },
                    "outcome": {
                        "type": "string",
                        "description": "Call outcome (booked, transferred, no_booking, etc.)"
                    }
                },
                "required": ["contact_id", "transcript", "summary"]
            }
        }
    ]


async def create_all_tools():
    """Create all tools in Vapi Tools section"""
    vapi = VapiClient()
    
    # Get server URL
    server_url = settings.webhook_base_url or "https://scott-valley-hvac-api.fly.dev"
    
    print("=" * 70)
    print("🔧 CREATING TOOLS IN VAPI DASHBOARD")
    print("=" * 70)
    print(f"\nServer URL: {server_url}\n")
    
    # Get tool definitions
    tools = get_tool_definitions(server_url)
    
    # Check existing tools first and delete function-type tools
    try:
        existing_tools = await vapi.list_tools()
        tools_to_delete = []
        existing_api_request_names = set()
        
        for tool in existing_tools:
            if isinstance(tool, dict):
                tool_id = tool.get("id", "")
                tool_type = tool.get("type", "")
                func = tool.get("function", {})
                api_req = tool.get("apiRequest", {})
                
                # Track existing API request tools
                if isinstance(api_req, dict):
                    existing_api_request_names.add(api_req.get("name"))
                
                # Mark function-type tools for deletion
                if tool_type == "function" and isinstance(func, dict):
                    func_name = func.get("name", "")
                    tools_to_delete.append((tool_id, func_name))
        
        # Delete function-type tools
        if tools_to_delete:
            print(f"\n🗑️  Deleting {len(tools_to_delete)} existing function-type tools...")
            for tool_id, tool_name in tools_to_delete:
                try:
                    await vapi.delete_tool(tool_id)
                    print(f"   ✅ Deleted: {tool_name}")
                except Exception as e:
                    print(f"   ⚠️  Could not delete {tool_name}: {str(e)}")
            print()
        
        print(f"Found {len(existing_tools)} existing tools")
    except Exception as e:
        logger.warning(f"Could not list existing tools: {e}")
        existing_api_request_names = set()
    
    created_tools = []
    skipped_tools = []
    
    # Create each tool as API Request type
    for tool_def in tools:
        tool_name = tool_def.get("name", "unknown")
        
        if tool_name in existing_api_request_names:
            print(f"⏭️  Skipping {tool_name} (API Request type already exists)")
            skipped_tools.append(tool_name)
            continue
        
        try:
            print(f"Creating API Request tool: {tool_name}...")
            result = await vapi.create_tool(tool_def)
            tool_id = result.get("id", "")
            created_tools.append((tool_name, tool_id))
            print(f"   ✅ Created! ID: {tool_id}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            logger.exception(f"Error creating tool {tool_name}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"\n✅ Created: {len(created_tools)} tools")
    print(f"⏭️  Skipped: {len(skipped_tools)} tools (already exist)")
    
    if created_tools:
        print("\n📋 Created Tools:")
        for name, tool_id in created_tools:
            print(f"   - {name}: {tool_id}")
    
    print("\n✅ Tools are now available in dashboard.vapi.ai/tools")
    print("\nNext steps:")
    print("1. Go to dashboard.vapi.ai/tools to verify")
    print("2. Assign tools to assistants in assistant settings")
    print()


if __name__ == "__main__":
    asyncio.run(create_all_tools())

