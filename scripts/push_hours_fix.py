#!/usr/bin/env python3
"""
Push hours/availability fix to Vapi:
  1. Re-upload company-info.txt and voice-style-and-templates.txt
  2. Update query_tool knowledgeBases with new file IDs
  3. Update inbound assistant system prompt
  4. Update outbound assistant system prompt
"""
import httpx
import json
import sys
import os

API_KEY = "bee0337d-41cd-49c2-9038-98cd0e18c75b"
BASE = "https://api.vapi.ai"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

INBOUND_ASSISTANT_ID = "d61d0517-4a65-496e-b97f-d3ad220f684e"
OUTBOUND_ASSISTANT_ID = "d6c74f74-de2a-420d-ae59-aab8fa7cbabe"
QUERY_TOOL_ID = "e1c6fb6d-2ea0-44f4-8ca2-54991d41e4c9"

# Old file IDs to replace
OLD_COMPANY_INFO_FILE = "6b602032-bb6b-4878-895f-f0b4b3b71dc6"
OLD_VOICE_STYLE_FILE = "5c86a6f9-dc19-4825-b728-c2228b3d102f"

# Other KB file IDs (unchanged)
PRICING_FILE = "5ee4fe5d-0a2c-4c26-a654-0ffc6020158b"
CALENDAR_FILE = "41d36dfc-6362-4e22-88c6-cc22ee39e249"
SERVICES_FILE = "4519db73-f920-4722-ada8-b62c46325209"
SERVICE_AREA_FILE = "6f9ff8df-e6a3-42e5-97d9-5cde1f5ece8b"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def upload_file(filepath: str, name: str) -> str:
    """Upload a file to Vapi and return the new file ID."""
    url = f"{BASE}/file"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "text/plain")}
        resp = httpx.post(url, headers=headers, files=files, timeout=30)
    if resp.status_code in (200, 201):
        data = resp.json()
        file_id = data.get("id")
        print(f"  ✅ Uploaded {name} → file ID: {file_id}")
        return file_id
    else:
        print(f"  ❌ Upload {name} failed ({resp.status_code}): {resp.text[:300]}")
        return None


def delete_file(file_id: str, name: str):
    """Delete an old file from Vapi."""
    url = f"{BASE}/file/{file_id}"
    resp = httpx.delete(url, headers=HEADERS, timeout=15)
    if resp.status_code in (200, 204):
        print(f"  🗑  Deleted old {name} ({file_id})")
    else:
        print(f"  ⚠️  Could not delete old {name} ({resp.status_code}): {resp.text[:200]}")


def update_query_tool(company_file_id: str, voice_file_id: str) -> bool:
    """Update query_tool knowledgeBases with new file IDs."""
    url = f"{BASE}/tool/{QUERY_TOOL_ID}"
    payload = {
        "function": {
            "name": "query_tool",
            "description": "Search the Valley View HVAC knowledge base for policies, pricing, services, booking rules, service area, company info, and voice style guidance. MUST call before answering any policy, pricing, service-area, scheduling, or company question. Follow retrieved content exactly."
        },
        "knowledgeBases": [
            {
                "provider": "google",
                "name": "pricing-and-discounts",
                "description": "Diagnostic fees, install/replacement price ranges, discount tiers (senior, veteran, educator, first responder), stacking rules, emergency/weekend pricing, out-of-area fees, and required pricing language.",
                "fileIds": [PRICING_FILE]
            },
            {
                "provider": "google",
                "name": "calendar-and-booking-rules",
                "description": "Mandatory tool sequence for booking, curated availability contract, 2-hour appointment windows, availability presentation rules, caller-requested time handling, existing appointment logic, reconfirmation requirements, SMS confirmation rules, same-day/after-hours considerations, no-slot handling.",
                "fileIds": [CALENDAR_FILE]
            },
            {
                "provider": "google",
                "name": "services-and-capabilities",
                "description": "Residential and commercial service types, what Valley View HVAC does NOT service (radiant, geothermal, hydro/steam, boilers), appointment types and typical durations.",
                "fileIds": [SERVICES_FILE]
            },
            {
                "provider": "google",
                "name": "service-area",
                "description": "Primary 20-25 mile service radius from Salem OR, extended coverage to Portland/Eugene/Corvallis, full Salem/West Salem coverage, surrounding towns served by direction.",
                "fileIds": [SERVICE_AREA_FILE]
            },
            {
                "provider": "google",
                "name": "company-info",
                "description": "Company identity (Valley View HVAC), office address, phone answering hours (twenty-four seven), technician dispatch hours (8-4:30), financing (Enhancify), payment methods, cancellation policy, preferred brands, staff directory for warm transfers.",
                "fileIds": [company_file_id]
            },
            {
                "provider": "google",
                "name": "voice-style-and-templates",
                "description": "Time and number pronunciation rules, 24/7 pronunciation (twenty-four seven), team language rules (never say AI), SMS confirmation notes, real-person script, wrong-name correction script, phrasing variations.",
                "fileIds": [voice_file_id]
            }
        ]
    }
    resp = httpx.patch(url, headers=HEADERS, json=payload, timeout=15)
    if resp.status_code == 200:
        print("  ✅ query_tool updated with new file IDs")
        return True
    else:
        print(f"  ❌ query_tool update failed ({resp.status_code}): {resp.text[:300]}")
        return False


def update_assistant(assistant_id: str, prompt_path: str, name: str, model_config: dict, old_kb_file_ids: list, new_company_id: str) -> bool:
    """Update an assistant's system prompt and knowledgeBase file IDs."""
    with open(prompt_path, "r") as f:
        prompt = f.read()

    # Replace old company-info file ID with new one in the knowledgeBase
    updated_file_ids = []
    for fid in old_kb_file_ids:
        if fid == OLD_COMPANY_INFO_FILE:
            updated_file_ids.append(new_company_id)
        else:
            updated_file_ids.append(fid)

    url = f"{BASE}/assistant/{assistant_id}"
    payload = {
        "model": {
            "provider": model_config["provider"],
            "model": model_config["model"],
            "maxTokens": model_config["maxTokens"],
            "temperature": model_config["temperature"],
            "toolIds": model_config["toolIds"],
            "knowledgeBase": {
                "provider": "google",
                "fileIds": updated_file_ids
            },
            "messages": [
                {"role": "system", "content": prompt}
            ]
        }
    }
    resp = httpx.patch(url, headers=HEADERS, json=payload, timeout=15)
    if resp.status_code == 200:
        print(f"  ✅ {name} assistant updated (prompt + knowledgeBase)")
        return True
    else:
        print(f"  ❌ {name} update failed ({resp.status_code}): {resp.text[:300]}")
        return False


def main():
    print("=" * 60)
    print("Push Hours/Availability Fix to Vapi")
    print("=" * 60)

    # Step 1: Upload new KB files
    print("\n1. Uploading updated KB files...")
    company_path = os.path.join(PROJECT_DIR, "kb", "company-info.txt")
    voice_path = os.path.join(PROJECT_DIR, "kb", "voice-style-and-templates.txt")

    new_company_id = upload_file(company_path, "company-info.txt")
    new_voice_id = upload_file(voice_path, "voice-style-and-templates.txt")

    if not new_company_id or not new_voice_id:
        print("\n❌ File upload failed. Aborting.")
        return 1

    # Step 2: Update query_tool with new file IDs
    print("\n2. Updating query_tool knowledgeBases...")
    if not update_query_tool(new_company_id, new_voice_id):
        print("\n❌ query_tool update failed. Aborting.")
        return 1

    # Step 3: Delete old files
    print("\n3. Cleaning up old files...")
    delete_file(OLD_COMPANY_INFO_FILE, "company-info.txt")
    delete_file(OLD_VOICE_STYLE_FILE, "voice-style-and-templates.txt")

    # Step 4: Update assistant prompts and knowledgeBase
    print("\n4. Updating assistant prompts and knowledgeBase...")
    inbound_path = os.path.join(PROJECT_DIR, "docs", "inbound_system_prompt_2.txt")
    outbound_path = os.path.join(PROJECT_DIR, "docs", "outbound_systemprompt_2.txt")

    inbound_model = {
        "provider": "openai",
        "model": "gpt-5.2",
        "maxTokens": 300,
        "temperature": 0.4,
        "toolIds": [
            "e1c6fb6d-2ea0-44f4-8ca2-54991d41e4c9",
            "4d10d4f1-5f46-4a2b-bbfe-fa1ae5002b09",
            "f943853b-a659-41cd-8cf5-dcb50217e1cf",
            "f051185a-4a26-4ed5-8eda-b7bc5b577593",
            "c571a655-8744-4884-a9cf-fb429822d941",
            "64b64ce3-eacc-407b-8abc-7ec27681d5a3",
            "b2dc35b6-6139-4cb6-aecc-ec116e1b1a16",
            "50f78b63-00fe-452f-b9ed-3e15e61cfc07",
            "380fbfc6-a79c-4d24-a15b-65a310478e56",
            "dec9f599-1750-4a4e-83eb-36704394d8ae",
            "dd8473b9-fb11-4548-870a-e54e854b94ba",
            "0241e8e1-4e65-4d74-b3bd-293f8bd0fda9"
        ]
    }
    inbound_kb_files = [
        "4519db73-f920-4722-ada8-b62c46325209",
        "6f9ff8df-e6a3-42e5-97d9-5cde1f5ece8b",
        OLD_COMPANY_INFO_FILE,
        "5ee4fe5d-0a2c-4c26-a654-0ffc6020158b",
        "41d36dfc-6362-4e22-88c6-cc22ee39e249",
        "74d52ab7-d0f8-47ec-8461-a9495e47602c"
    ]

    outbound_model = {
        "provider": "openai",
        "model": "gpt-5.2",
        "maxTokens": 400,
        "temperature": 0.5,
        "toolIds": [
            "e1c6fb6d-2ea0-44f4-8ca2-54991d41e4c9",
            "4d10d4f1-5f46-4a2b-bbfe-fa1ae5002b09",
            "f943853b-a659-41cd-8cf5-dcb50217e1cf",
            "f051185a-4a26-4ed5-8eda-b7bc5b577593",
            "c571a655-8744-4884-a9cf-fb429822d941",
            "64b64ce3-eacc-407b-8abc-7ec27681d5a3",
            "b2dc35b6-6139-4cb6-aecc-ec116e1b1a16",
            "50f78b63-00fe-452f-b9ed-3e15e61cfc07",
            "380fbfc6-a79c-4d24-a15b-65a310478e56",
            "dec9f599-1750-4a4e-83eb-36704394d8ae",
            "dd8473b9-fb11-4548-870a-e54e854b94ba",
            "0241e8e1-4e65-4d74-b3bd-293f8bd0fda9"
        ]
    }
    outbound_kb_files = [
        "4519db73-f920-4722-ada8-b62c46325209",
        "6f9ff8df-e6a3-42e5-97d9-5cde1f5ece8b",
        OLD_COMPANY_INFO_FILE,
        "5ee4fe5d-0a2c-4c26-a654-0ffc6020158b",
        "41d36dfc-6362-4e22-88c6-cc22ee39e249",
        "74d52ab7-d0f8-47ec-8461-a9495e47602c",
        "d9e005af-9f84-464a-86e9-19c0ec6ef08e"
    ]

    ok1 = update_assistant(INBOUND_ASSISTANT_ID, inbound_path, "Inbound", inbound_model, inbound_kb_files, new_company_id)
    ok2 = update_assistant(OUTBOUND_ASSISTANT_ID, outbound_path, "Outbound", outbound_model, outbound_kb_files, new_company_id)

    # Summary
    print("\n" + "=" * 60)
    if ok1 and ok2:
        print("✅ All updates pushed successfully!")
        print(f"   New company-info file ID: {new_company_id}")
        print(f"   New voice-style file ID:  {new_voice_id}")
    else:
        print("⚠️  Some updates failed. Check output above.")
    print("=" * 60)

    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
