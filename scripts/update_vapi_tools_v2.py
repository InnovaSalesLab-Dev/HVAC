#!/usr/bin/env python3
"""
Update all Vapi tool descriptions and parameter descriptions.
Applies prompt engineering best practices: concise, clear, says WHAT + WHEN.
"""
import httpx
import json
import sys

API_KEY = "bee0337d-41cd-49c2-9038-98cd0e18c75b"
BASE = "https://api.vapi.ai"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

TOOL_UPDATES = [
    {
        "id": "e1c6fb6d-2ea0-44f4-8ca2-54991d41e4c9",
        "name": "query_tool",
        "type": "query",
        "payload": {
            "function": {
                "name": "query_tool",
                "description": "Search the Valley View HVAC knowledge base for policies, pricing, services, booking rules, service area, company info, and voice style guidance. MUST call before answering any policy, pricing, service-area, scheduling, or company question. Follow retrieved content exactly."
            },
            "knowledgeBases": [
                {
                    "provider": "google",
                    "name": "pricing-and-discounts",
                    "description": "Diagnostic fees, install/replacement price ranges, discount tiers (senior, veteran, educator, first responder), stacking rules, emergency/weekend pricing, out-of-area fees, and required pricing language.",
                    "fileIds": ["5ee4fe5d-0a2c-4c26-a654-0ffc6020158b"]
                },
                {
                    "provider": "google",
                    "name": "calendar-and-booking-rules",
                    "description": "Mandatory tool sequence for booking, curated availability contract, 2-hour appointment windows, availability presentation rules, caller-requested time handling, existing appointment logic, reconfirmation requirements, SMS confirmation rules, same-day/after-hours considerations, no-slot handling.",
                    "fileIds": ["41d36dfc-6362-4e22-88c6-cc22ee39e249"]
                },
                {
                    "provider": "google",
                    "name": "services-and-capabilities",
                    "description": "Residential and commercial service types, what Valley View HVAC does NOT service (radiant, geothermal, hydro/steam, boilers), appointment types and typical durations.",
                    "fileIds": ["4519db73-f920-4722-ada8-b62c46325209"]
                },
                {
                    "provider": "google",
                    "name": "service-area",
                    "description": "Primary 20-25 mile service radius from Salem OR, extended coverage to Portland/Eugene/Corvallis, full Salem/West Salem coverage, surrounding towns served by direction.",
                    "fileIds": ["6f9ff8df-e6a3-42e5-97d9-5cde1f5ece8b"]
                },
                {
                    "provider": "google",
                    "name": "company-info",
                    "description": "Company identity (Valley View HVAC), office address, business hours, financing (Enhancify), payment methods, cancellation policy, preferred brands, staff directory for warm transfers.",
                    "fileIds": ["6b602032-bb6b-4878-895f-f0b4b3b71dc6"]
                },
                {
                    "provider": "google",
                    "name": "voice-style-and-templates",
                    "description": "Time and number pronunciation rules, SMS confirmation message template, email confirmation template, real-person script, wrong-name correction script.",
                    "fileIds": ["5c86a6f9-dc19-4825-b728-c2228b3d102f"]
                }
            ]
        }
    },
    {
        "id": "380fbfc6-a79c-4d24-a15b-65a310478e56",
        "name": "classifyCallType",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "classifyCallType",
                "description": "Classify the call type from the conversation. Use at the start of every call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": "Conversation transcript so far."},
                        "conversation_summary": {"type": "string", "description": "Brief summary of conversation."}
                    },
                    "required": ["transcript"]
                }
            }
        }
    },
    {
        "id": "c571a655-8744-4884-a9cf-fb429822d941",
        "name": "createContact",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "createContact",
                "description": "Create or update a contact in the CRM. Use after collecting name and phone.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Full name."},
                        "phone": {"type": "string", "description": "Phone in E.164 format (e.g. +15035551234)."},
                        "email": {"type": "string", "description": "Email address (optional)."},
                        "address": {"type": "string", "description": "Service address."},
                        "zip_code": {"type": "string", "description": "ZIP code."},
                        "sms_consent": {"type": "boolean", "description": "True if caller consents to SMS."}
                    },
                    "required": ["name", "phone"]
                }
            }
        }
    },
    {
        "id": "dd8473b9-fb11-4548-870a-e54e854b94ba",
        "name": "checkBusinessHours",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "checkBusinessHours",
                "description": "Check if the business is currently open and get the current Pacific Time. MUST call before checkCalendarAvailability or answering open/closed questions.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    },
    {
        "id": "50f78b63-00fe-452f-b9ed-3e15e61cfc07",
        "name": "checkCalendarAvailability",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "checkCalendarAvailability",
                "description": "Get available 2-hour appointment slots. Use after checkBusinessHours. Returns curated options — offer only 2 at a time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_type": {
                            "type": "string",
                            "enum": ["repair", "installation", "maintenance", "estimate"],
                            "description": "Type of service needed."
                        },
                        "start_date": {"type": "string", "description": "Start date (ISO format, e.g. 2026-02-05)."},
                        "end_date": {"type": "string", "description": "End date (ISO format)."},
                        "calendar_id": {"type": "string", "description": "Calendar ID (optional)."}
                    },
                    "required": ["service_type", "start_date", "end_date"]
                }
            }
        }
    },
    {
        "id": "b2dc35b6-6139-4cb6-aecc-ec116e1b1a16",
        "name": "bookAppointment",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "bookAppointment",
                "description": "Book a 2-hour appointment. Use after caller confirms service type, date/time, and address. Always reconfirm before calling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "string", "description": "CRM contact ID."},
                        "calendar_id": {"type": "string", "description": "Calendar ID."},
                        "start_time": {"type": "string", "description": "Start time (ISO format)."},
                        "end_time": {"type": "string", "description": "End time (ISO format, 2 hours after start)."},
                        "title": {"type": "string", "description": "Appointment title (e.g. 'Furnace Repair - Smith')."},
                        "service_type": {
                            "type": "string",
                            "enum": ["repair", "installation", "maintenance", "estimate"],
                            "description": "Service type."
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["emergency", "urgent", "standard", "low"],
                            "description": "Urgency level."
                        },
                        "notes": {"type": "string", "description": "Additional notes (issue details, access instructions)."}
                    },
                    "required": ["contact_id", "calendar_id", "start_time", "end_time", "title", "service_type"]
                }
            }
        }
    },
    {
        "id": "64b64ce3-eacc-407b-8abc-7ec27681d5a3",
        "name": "cancelAppointment",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "cancelAppointment",
                "description": "Cancel an existing appointment. Use when caller wants to cancel or reschedule (cancel first, then rebook).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "string", "description": "CRM contact ID."},
                        "appointment_id": {"type": "string", "description": "ID of the appointment to cancel."},
                        "reason": {"type": "string", "description": "Reason for cancellation."}
                    },
                    "required": ["contact_id", "appointment_id"]
                }
            }
        }
    },
    {
        "id": "f051185a-4a26-4ed5-8eda-b7bc5b577593",
        "name": "sendConfirmation",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "sendConfirmation",
                "description": "Send SMS or email confirmation after booking. Call exactly ONCE per booking. Include a detailed message with date, time, service, address, and phone (971) 366-2499. If caller asks to send to a different number, pass that number in the phone parameter.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "string", "description": "CRM contact ID."},
                        "appointment_id": {"type": "string", "description": "Booked appointment ID."},
                        "method": {
                            "type": "string",
                            "enum": ["sms", "email"],
                            "description": "SMS (default) or email."
                        },
                        "message": {"type": "string", "description": "Detailed confirmation message with date, time, service, address. See KB for template."},
                        "phone": {"type": "string", "description": "Override phone number in E.164 (e.g. +15035551234). Use only when caller asks to send confirmation to a different number."}
                    },
                    "required": ["contact_id", "method"]
                }
            }
        }
    },
    {
        "id": "f943853b-a659-41cd-8cf5-dcb50217e1cf",
        "name": "initiateWarmTransfer",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "initiateWarmTransfer",
                "description": "Transfer call to staff. Tell the caller who you are connecting them to first. See company-info.md for numbers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "call_sid": {"type": "string", "description": "Current call SID."},
                        "staff_phone": {"type": "string", "description": "Staff phone in E.164 (e.g. +19717126763)."},
                        "context": {"type": "string", "description": "Brief context for staff (issue + caller name)."}
                    },
                    "required": ["call_sid", "staff_phone"]
                }
            }
        }
    },
    {
        "id": "4d10d4f1-5f46-4a2b-bbfe-fa1ae5002b09",
        "name": "logCallSummary",
        "type": "apiRequest",
        "payload": {
            "function": {
                "name": "logCallSummary",
                "description": "Save call transcript and summary to CRM. Use before ending the call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "string", "description": "CRM contact ID."},
                        "transcript": {"type": "string", "description": "Full call transcript."},
                        "summary": {"type": "string", "description": "Brief call summary (1-2 sentences)."},
                        "call_type": {
                            "type": "string",
                            "enum": ["service_repair", "install_estimate", "maintenance", "appointment_change", "other"],
                            "description": "Call type."
                        },
                        "outcome": {"type": "string", "description": "Outcome: booked, transferred, no_booking, message_taken."},
                        "call_duration": {"type": "integer", "description": "Duration in seconds."}
                    },
                    "required": ["contact_id", "transcript", "summary"]
                }
            }
        }
    },
    {
        "id": "dec9f599-1750-4a4e-83eb-36704394d8ae",
        "name": "warmtransfer_tool",
        "type": "transferCall",
        "payload": {
            "function": {
                "name": "warmtransfer_tool",
                "description": "Transfer call to staff. Scott (Owner) 971-712-6763 for pricing/escalations. Tell the caller who you are connecting them to before transferring."
            }
        }
    },
    {
        "id": "0241e8e1-4e65-4d74-b3bd-293f8bd0fda9",
        "name": "end_call_tool",
        "type": "endCall",
        "payload": {
            "function": {
                "name": "end_call_tool",
                "description": "End the call. Use ONLY after: caller confirms no more questions, goodbye exchanged, appointment confirmed (if booked), and logCallSummary called.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    }
]


def update_tool(tool_id: str, name: str, payload: dict) -> bool:
    url = f"{BASE}/tool/{tool_id}"
    resp = httpx.patch(url, headers=HEADERS, json=payload, timeout=15)
    if resp.status_code == 200:
        print(f"  ✅ {name} updated")
        return True
    else:
        print(f"  ❌ {name} failed ({resp.status_code}): {resp.text[:200]}")
        return False


def main():
    print(f"Updating {len(TOOL_UPDATES)} Vapi tools...\n")
    success = 0
    for tool in TOOL_UPDATES:
        ok = update_tool(tool["id"], tool["name"], tool["payload"])
        if ok:
            success += 1
    print(f"\nDone: {success}/{len(TOOL_UPDATES)} tools updated.")
    return 0 if success == len(TOOL_UPDATES) else 1


if __name__ == "__main__":
    sys.exit(main())
