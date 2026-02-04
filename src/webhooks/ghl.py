from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional, Dict, Any
import json
import asyncio
from datetime import datetime, timedelta
from src.models import GHLWebhookEvent
from src.integrations.vapi import VapiClient
from src.integrations.ghl import GHLClient
from src.integrations.twilio import TwilioService
from src.utils.logging import logger
from src.utils.validation import validate_phone_number
from src.utils.webhook_security import verify_ghl_webhook_signature
from src.utils.ghl_fields import build_custom_fields_array, custom_fields_to_dict
from src.utils.errors import VapiAPIError
from src.config import settings
from src.utils.phone_normalize import normalize_phone_for_comparison

router = APIRouter()

# In-memory locks per phone number to prevent concurrent SMS sends
# Key: normalized phone number, Value: asyncio.Lock
_sms_locks: Dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()  # Lock to protect the _sms_locks dict itself

# In-memory locks per contact ID to prevent concurrent call initiation
# Key: contact_id, Value: asyncio.Lock
_contact_locks: Dict[str, asyncio.Lock] = {}
_contact_locks_lock = asyncio.Lock()  # Lock to protect the _contact_locks dict itself

# In-memory locks per phone number to prevent concurrent call initiation
# Key: normalized phone number, Value: asyncio.Lock
_phone_call_locks: Dict[str, asyncio.Lock] = {}
_phone_call_locks_lock = asyncio.Lock()  # Lock to protect the _phone_call_locks dict itself

# Track call IDs that have already triggered SMS (to prevent duplicates)
# Key: call_id, Value: True
_sms_triggered_call_ids: Dict[str, bool] = {}
_sms_triggered_lock = asyncio.Lock()  # Lock to protect the _sms_triggered_call_ids dict

# Track phone numbers that are currently checking SMS eligibility (to prevent duplicate checks)
# Key: normalized phone number, Value: Set of call_ids currently checking
_phone_sms_checking: Dict[str, set] = {}
_phone_sms_checking_lock = asyncio.Lock()  # Lock to protect the _phone_sms_checking dict

async def get_phone_lock(phone: str) -> asyncio.Lock:
    """Get or create a lock for a specific phone number"""
    phone_normalized = normalize_phone_for_comparison(phone)
    if not phone_normalized:
        # If we can't normalize, create a unique lock per call (not ideal but safe)
        return asyncio.Lock()
    
    async with _locks_lock:
        if phone_normalized not in _sms_locks:
            _sms_locks[phone_normalized] = asyncio.Lock()
        return _sms_locks[phone_normalized]

async def get_contact_lock(contact_id: str) -> asyncio.Lock:
    """Get or create a lock for a specific contact ID to prevent concurrent call initiation"""
    if not contact_id:
        return asyncio.Lock()
    
    async with _contact_locks_lock:
        if contact_id not in _contact_locks:
            _contact_locks[contact_id] = asyncio.Lock()
        return _contact_locks[contact_id]

async def get_phone_call_lock(phone: str) -> asyncio.Lock:
    """Get or create a lock for a specific phone number to prevent concurrent call initiation"""
    phone_normalized = normalize_phone_for_comparison(phone)
    if not phone_normalized:
        return asyncio.Lock()
    
    async with _phone_call_locks_lock:
        if phone_normalized not in _phone_call_locks:
            _phone_call_locks[phone_normalized] = asyncio.Lock()
        return _phone_call_locks[phone_normalized]


@router.post("/ghl")
async def ghl_webhook(
    request: Request,
    x_ghl_signature: Optional[str] = Header(None, alias="X-GHL-Signature")
):
    """
    Handle webhooks from GoHighLevel.
    Triggers outbound calls when new leads are created.
    
    Verifies webhook signature for security if WEBHOOK_SECRET is configured.
    """
    try:
        # Get raw body for signature verification
        body_bytes = await request.body()
        
        # Verify webhook signature if secret is configured
        # Only log warning once per startup, not on every webhook
        if settings.webhook_secret:
            if not verify_ghl_webhook_signature(body_bytes, x_ghl_signature):
                logger.warning("Webhook signature verification failed - rejecting request")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid webhook signature"
                )
            logger.debug("✅ Webhook signature verified successfully")
        # Removed warning - webhook secret is optional for development/testing
        
        # Parse JSON body
        body = json.loads(body_bytes.decode('utf-8'))
        data = body.get("data", {})
        custom_data = body.get("customData", {})
        
        # GHL webhooks can use different field locations depending on source
        # Check multiple possible locations for event type
        event_type = (
            body.get("type") or 
            body.get("event") or 
            custom_data.get("type") or
            ""
        )
        
        # Extract location_id from various possible locations
        location_id = (
            body.get("locationId") or
            body.get("location", {}).get("id") or
            custom_data.get("locationId") or
            data.get("locationId") or
            ""
        )
        
        # Extract contact_id from various possible locations (both camelCase and snake_case)
        contact_id = (
            body.get("contactId") or 
            body.get("contact_id") or
            body.get("contact", {}).get("id") or
            data.get("contact", {}).get("id") or
            custom_data.get("contactId") or
            custom_data.get("contact_id") or
            None
        )
        
        # Log full webhook payload for debugging
        logger.info(f"📥 Webhook received - Full payload: {body}")
        logger.info(f"📥 Webhook event_type: '{event_type}'")
        logger.info(f"📥 Webhook location_id: '{location_id}'")
        logger.info(f"📥 Webhook contact_id: '{contact_id}'")
        
        # Verify location ID matches
        # Log received location ID for debugging
        logger.info(f"Received location_id: '{location_id}', Expected: '{settings.ghl_location_id}'")
        
        # If location_id is empty, try to get it from data or allow it
        if not location_id:
            logger.warning("Location ID not provided in webhook, attempting to extract...")
            # Try to extract from data if available
            if data.get("locationId"):
                location_id = data.get("locationId")
                logger.info(f"Using location_id from data: {location_id}")
            else:
                # For now, allow webhooks without location ID (may be from different GHL setup)
                logger.warning("No location ID found in webhook, allowing to proceed (using configured location)")
                location_id = settings.ghl_location_id  # Use configured location ID
        
        # Verify location ID matches (only if we have one)
        if location_id and location_id != settings.ghl_location_id:
            logger.warning(f"Webhook from different location: received '{location_id}', expected '{settings.ghl_location_id}'")
            return {"status": "ignored", "reason": "location_mismatch"}
        
        logger.info(f"Received GHL webhook: {event_type} for contact {contact_id}")
        
        # Handle different event types
        # Process both contact.created and contact.updated for outbound calls.
        # When the same person resubmits the form, GHL updates the contact (contact.updated).
        # handle_new_lead enforces "outbound" tag and vapi_called so we don't double-call.
        if event_type in ("contact.created", "contact.updated"):
            await handle_new_lead(contact_id, body)  # Pass full body to access contact data if available
        elif event_type == "appointment.created":
            await handle_appointment_created(contact_id, data)
        elif event_type == "form.submitted":
            # Pass the full body, not just data, so we can extract contact_id
            await handle_form_submission(body)
        elif event_type in ["conversation.created", "chat.converted", "webchat.converted"]:
            await handle_chat_conversion(data)
        elif event_type in ["lead.created", "ad.submission", "google.lead", "meta.lead", "facebook.lead"]:
            await handle_ad_lead(data)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
        
        return {"status": "ok", "event": event_type}
    except Exception as e:
        logger.exception(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_new_lead(contact_id: Optional[str], webhook_body: Dict[str, Any]):
    """Trigger outbound call for new lead"""
    if not contact_id:
        logger.warning("No contact ID in webhook data")
        return
    
    ghl = GHLClient()
    vapi = VapiClient()
    
    try:
        # CRITICAL: First, extract phone number BEFORE acquiring locks
        # This allows us to acquire the phone_call_lock FIRST (outermost lock)
        # to prevent multiple contacts with same phone from all proceeding
        #
        # GHL workflow custom data often sends phone inside customData or data, not top-level.
        # Check top-level first, then customData, then data (and data.contact) so we use
        # the form-submitted number and avoid stale contact record.
        def _get_phone_from_dict(d: Optional[Dict[str, Any]]) -> Optional[str]:
            if not d or not isinstance(d, dict):
                return None
            raw = (
                d.get("phone") or d.get("phoneNumber") or d.get("phone_number")
                or d.get("Phone") or d.get("PhoneNumber")
            )
            return (raw and isinstance(raw, str) and raw.strip()) or None

        custom_data = webhook_body.get("customData")
        data = webhook_body.get("data")
        data_contact = data.get("contact") if isinstance(data, dict) else None

        webhook_phone = (
            _get_phone_from_dict(webhook_body)
            or _get_phone_from_dict(custom_data)
            or _get_phone_from_dict(data)
            or _get_phone_from_dict(data_contact)
        )
        phone = webhook_phone
        
        # If not in webhook, we'll need to fetch contact, but do it AFTER acquiring phone lock
        # to minimize lock contention
        
        # Normalize phone number if we have it
        phone_clean = None
        if phone:
            try:
                phone_clean = validate_phone_number(phone)
                logger.info(f"📞 Phone from webhook: {phone} -> normalized: {phone_clean}")
            except Exception as e:
                logger.warning(f"Invalid phone number from webhook: {phone} - {str(e)}")
                phone_clean = None
        
        # CRITICAL: Acquire phone_call_lock FIRST (outermost lock)
        # This ensures only ONE call per phone number across ALL contacts
        # If we don't have phone yet, we'll need to fetch contact first (but still use phone lock)
        if phone_clean:
            phone_call_lock = await get_phone_call_lock(phone_clean)
        else:
            # If no phone in webhook, we need to fetch contact first
            # But we still want to use contact lock to prevent duplicate processing
            phone_call_lock = None
        
        # Acquire contact lock (inner lock) to prevent duplicate processing of same contact
        contact_lock = await get_contact_lock(contact_id)
        
        # Nested locks: phone_call_lock (outer) -> contact_lock (inner)
        # This ensures:
        # 1. Only one call per phone number (phone_call_lock)
        # 2. Only one call per contact (contact_lock)
        async with contact_lock:
            # Fetch contact data INSIDE contact lock to ensure we get fresh status
            contact = None
            if webhook_phone or webhook_body.get("email") or webhook_body.get("first_name"):
                # Webhook contains contact data directly
                logger.info(f"Using contact data from webhook payload for {contact_id}")
                contact = webhook_body
            else:
                # Fetch contact from GHL API (INSIDE lock to get fresh data)
                contact_response = await ghl.get_contact(contact_id=contact_id)
                if not contact_response:
                    logger.warning(f"Contact {contact_id} not found")
                    return
                
                # GHL API can return contact nested in "contact" key or directly
                contact = contact_response.get("contact", contact_response) if isinstance(contact_response, dict) else contact_response
            
            # Extract phone number if not already extracted from webhook
            if not phone_clean:
                phone = None
                if isinstance(contact, dict):
                    # Try direct phone fields first (check all variants)
                    phone_candidates = [
                        contact.get("phone"),
                        contact.get("phoneNumber"),
                        contact.get("phone_number"),
                        contact.get("Phone"),  # Capitalized variant
                        contact.get("PhoneNumber"),  # Capitalized variant
                    ]
                    
                    # Find first non-empty phone value
                    for candidate in phone_candidates:
                        if candidate and isinstance(candidate, str) and candidate.strip():
                            phone = candidate.strip()
                            break
                    
                    # If not found, try phoneNumbers array
                    if not phone and isinstance(contact.get("phoneNumbers"), list) and len(contact.get("phoneNumbers", [])) > 0:
                        phone_array_value = contact.get("phoneNumbers", [{}])[0].get("number", "")
                        if phone_array_value and isinstance(phone_array_value, str) and phone_array_value.strip():
                            phone = phone_array_value.strip()
                
                if not phone or (isinstance(phone, str) and not phone.strip()):
                    logger.warning(f"No valid phone number for contact {contact_id}")
                    return
                
                # Normalize phone number to E.164 format for Vapi
                try:
                    phone_clean = validate_phone_number(phone)
                    logger.info(f"📞 Found phone number for contact {contact_id}: {phone} -> normalized: {phone_clean}")
                except Exception as e:
                    logger.warning(f"Invalid phone number format for contact {contact_id}: {phone} - {str(e)}")
                    return
                
                # Now acquire phone_call_lock with the extracted phone
                phone_call_lock = await get_phone_call_lock(phone_clean)
            
            # CRITICAL: Acquire phone_call_lock (outer lock) BEFORE proceeding
            # This ensures only ONE call per phone number, even if multiple contacts share it
            async with phone_call_lock:
                # Double-check if a call is already in progress for this phone number
                # Search for contacts with this phone number and check their vapi_called status
                try:
                    contacts_with_phone = await ghl.search_contacts_by_phone(phone_clean)
                    if contacts_with_phone:
                        for contact_with_phone in contacts_with_phone:
                            other_contact_id = contact_with_phone.get("id")
                            other_contact_fields = await custom_fields_to_dict(contact_with_phone.get("customFields", []))
                            other_vapi_called = (
                                other_contact_fields.get("vapi_called") or 
                                other_contact_fields.get("contact.vapi_called") or 
                                ""
                            )
                            other_vapi_called_lower = str(other_vapi_called).lower() if other_vapi_called else ""
                            if other_vapi_called_lower in ["true", "calling", "1", "yes"]:
                                logger.info(f"📞 Phone {phone_clean} already has a call in progress (contact {other_contact_id}, status: {other_vapi_called}), skipping duplicate call")
                                return
                except Exception as phone_check_error:
                    logger.warning(f"⚠️  Could not check phone number for existing calls: {phone_check_error}")
                    # Continue anyway - locks should still prevent duplicates
                
                # CRITICAL: Check if contact has "outbound" tag - only trigger calls for outbound leads
                # Inbound callers should NOT receive outbound calls
                contact_tags = contact.get("tags", [])
                if isinstance(contact_tags, str):
                    # If tags is a string, split by comma
                    contact_tags = [tag.strip() for tag in contact_tags.split(",") if tag.strip()]
                elif not isinstance(contact_tags, list):
                    contact_tags = []
                
                # Normalize tags to lowercase for comparison
                contact_tags_lower = [str(tag).lower().strip() for tag in contact_tags if tag]
                
                # Only proceed if contact has "outbound" tag
                if "outbound" not in contact_tags_lower:
                    logger.info(f"📋 Contact {contact_id} does not have 'outbound' tag (tags: {contact_tags}), skipping outbound call. This is likely an inbound caller.")
                    return
                
                # Check if THIS contact already called (prevent duplicate calls) - INSIDE BOTH LOCKS
                # GHL customFields can be list or dict
                custom_fields = await custom_fields_to_dict(contact.get("customFields"))
                
                # Check both formats: "vapi_called" and "contact.vapi_called"
                # Also check for "calling" status to prevent race conditions
                vapi_called = (
                    custom_fields.get("vapi_called") or 
                    custom_fields.get("contact.vapi_called")
                )
                vapi_called_lower = str(vapi_called).lower() if vapi_called else ""
                
                # Skip if already called OR currently calling (prevents race conditions)
                if vapi_called_lower in ["true", "calling", "1", "yes"]:
                    logger.info(f"Contact {contact_id} already called or calling (status: {vapi_called}), skipping duplicate")
                    return
                
                # Mark as "calling" IMMEDIATELY to prevent race conditions
                # This ensures if multiple webhooks arrive simultaneously, only one proceeds
                try:
                    calling_fields = {
                        "vapi_called": "calling"  # Mark as "calling" before making call
                    }
                    calling_fields_update = await build_custom_fields_array(calling_fields, use_field_ids=True)
                    await ghl.update_contact(
                        contact_id=contact_id,
                        contact_data={
                            "customFields": calling_fields_update
                        }
                    )
                    logger.info(f"📞 Marked contact {contact_id} as 'calling' to prevent duplicates")
                except Exception as mark_error:
                    logger.warning(f"⚠️  Could not mark contact as calling (non-fatal): {mark_error}")
                    # Continue anyway - deduplication check above should still work
                
                # Get outbound assistant ID from environment or webhook data
                # Default to the outbound assistant we created
                assistant_id = (
                    webhook_body.get("assistantId") or 
                    settings.vapi_outbound_assistant_id or 
                    "d6c74f74-de2a-420d-ae59-aab8fa7cbabe"  # Default outbound assistant ID (newly created)
                )
                
                if not assistant_id:
                    logger.warning("No assistant ID configured for outbound calls")
                    return
                
                # Get phone number ID (Vapi phone number)
                # If not set, Vapi will use the default phone number from assistant
                phone_number_id = webhook_body.get("phoneNumberId") or settings.vapi_phone_number_id
                
                # Create outbound call via Vapi
                # Vapi requires phoneNumberId or phoneNumber (the number to call FROM)
                call_config = {
                    "assistantId": assistant_id,
                    "customer": {
                        "number": phone_clean  # Customer phone number to call TO
                    }
                }
                
                # Vapi requires either phoneNumberId or phoneNumber (the number to call FROM)
                # Prefer phoneNumberId if available (more reliable)
                if phone_number_id:
                    call_config["phoneNumberId"] = phone_number_id
                else:
                    # If no phoneNumberId, we need to get the assistant's default phone number
                    # For now, log a warning - user should configure VAPI_PHONE_NUMBER_ID
                    logger.warning("⚠️  No phoneNumberId configured. Vapi requires phoneNumberId or phoneNumber to make outbound calls.")
                    logger.warning("   Please set VAPI_PHONE_NUMBER_ID in Fly.io secrets with your Vapi phone number ID.")
                    logger.warning("   Alternatively, configure a default phone number in your Vapi assistant settings.")
                    # Try to get assistant details to find default phone number
                    try:
                        assistant = await vapi.get_assistant(assistant_id)
                        # Check if assistant has a default phone number configured
                        default_phone = assistant.get("phoneNumberId") or assistant.get("phoneNumber")
                        if default_phone:
                            call_config["phoneNumberId"] = default_phone
                            logger.info(f"✅ Using assistant's default phone number: {default_phone}")
                        else:
                            raise ValueError("No phone number configured")
                    except Exception as e:
                        logger.error(f"❌ Could not get assistant phone number: {e}")
                        raise VapiAPIError(
                            "Cannot make outbound call: No phone number configured. Please set VAPI_PHONE_NUMBER_ID or configure a default phone number in your Vapi assistant.",
                            status_code=400
                        )
                
                # CRITICAL: Create call INSIDE both locks to prevent duplicates
                call_result = await vapi.create_call(call_config)
                call_id = call_result.get("id", "")
                
                # Mark contact as called (update from "calling" to "true")
                # GHL API expects customFields array format with "contact.{key}" format
                custom_fields_dict = {
                    "vapi_called": "true",  # Update from "calling" to "true" after call is initiated
                    "vapi_call_id": call_id
                }
                
                # Add lead source if available from webhook body or contact data
                lead_source = (
                    webhook_body.get("leadSource") or
                    webhook_body.get("lead_source") or
                    webhook_body.get("source") or
                    contact.get("leadSource") or
                    contact.get("lead_source") or
                    # Check contact tags for lead source indicators
                    (contact.get("tags", []) if isinstance(contact.get("tags"), list) else [])
                )
                
                # Extract lead source from tags if present
                if isinstance(lead_source, list):
                    # Look for common lead source tags
                    source_tags = ["website", "yelp", "thumbtack", "google", "meta", "facebook", "form", "webchat"]
                    for tag in lead_source:
                        tag_lower = str(tag).lower() if tag else ""
                        for source in source_tags:
                            if source in tag_lower:
                                lead_source = source
                                break
                        if isinstance(lead_source, str):
                            break
                    # If still a list, use first tag or default
                    if isinstance(lead_source, list) and len(lead_source) > 0:
                        lead_source = str(lead_source[0]).lower()
                    elif isinstance(lead_source, list):
                        lead_source = None
                
                # Normalize lead source values
                if lead_source:
                    lead_source_lower = str(lead_source).lower()
                    # Map common variations to standard values
                    source_mapping = {
                        "google": "google_ads",
                        "google ads": "google_ads",
                        "meta": "meta_ads",
                        "facebook": "facebook_ads",
                        "fb": "facebook_ads",
                        "web chat": "webchat",
                        "webchat": "webchat",
                        "chat": "webchat",
                        "form": "form",
                        "website": "website",
                        "valleyviewhvac.com": "website",
                        "yelp": "yelp",
                        "thumbtack": "thumbtack"
                    }
                    lead_source = source_mapping.get(lead_source_lower, lead_source_lower)
                    custom_fields_dict["lead_source"] = lead_source
                    logger.info(f"📋 Lead source identified: {lead_source}")
                
                # Build custom fields array - use field IDs for better reliability
                custom_fields_update = await build_custom_fields_array(custom_fields_dict, use_field_ids=True)
                
                await ghl.update_contact(
                    contact_id=contact_id,
                    contact_data={
                        "customFields": custom_fields_update
                    }
                )
                
                logger.info(f"Outbound call initiated for contact {contact_id}, call ID: {call_id}")
                
                # Set up SMS fallback check (check call status after delay)
                # This happens OUTSIDE the locks (after call is created and marked)
                asyncio.create_task(check_call_and_send_sms_fallback(call_id, contact_id, phone_clean))
    except Exception as e:
        logger.exception(f"Error handling new lead: {str(e)}")


async def check_call_and_send_sms_fallback(call_id: str, contact_id: str, phone: str):
    """
    Check call status after delay and send SMS if call wasn't picked up.
    Waits 45 seconds for call to complete, then checks Vapi call status.
    Sends SMS if call was not answered (no-answer, voicemail, or very short duration).
    """
    # CRITICAL: Check if this call_id has already triggered SMS (prevent duplicates)
    async with _sms_triggered_lock:
        if call_id in _sms_triggered_call_ids:
            logger.info(f"📱 SMS already triggered for call {call_id}, skipping duplicate")
            return
        # Mark as triggered immediately (optimistic locking)
        _sms_triggered_call_ids[call_id] = True
    
    # CRITICAL: Acquire phone lock IMMEDIATELY to prevent multiple SMS tasks from proceeding
    # This ensures only ONE SMS task per phone number can proceed, even if multiple calls exist
    phone_lock = await get_phone_lock(phone)
    phone_normalized = normalize_phone_for_comparison(phone)
    
    # Phase 1: Pre-check if SMS was already sent (under lock to prevent race conditions)
    async with phone_lock:
        ghl = GHLClient()
        sms_already_sent = False
        
        if phone_normalized:
            try:
                contacts_with_phone = await ghl.search_contacts_by_phone(phone)
                if contacts_with_phone:
                    for contact_with_phone in contacts_with_phone:
                        contact_custom_fields = await custom_fields_to_dict(contact_with_phone.get("customFields", []))
                        contact_sms_sent = (
                            contact_custom_fields.get("sms_fallback_sent") or 
                            contact_custom_fields.get("contact.sms_fallback_sent") or 
                            "false"
                        )
                        if str(contact_sms_sent).lower() == "true":
                            logger.info(f"📱 SMS already sent to phone {phone} (contact {contact_with_phone.get('id')}), skipping SMS fallback for call {call_id}")
                            sms_already_sent = True
                            break
                        
                        contact_sms_date = (
                            contact_custom_fields.get("sms_fallback_sent_at") or 
                            contact_custom_fields.get("contact.sms_fallback_sent_at") or
                            contact_custom_fields.get("sms_fallback_date") or 
                            contact_custom_fields.get("contact.sms_fallback_date") or 
                            None
                        )
                        if contact_sms_date:
                            try:
                                last_sent = datetime.fromisoformat(contact_sms_date.replace('Z', '+00:00'))
                                time_diff = datetime.now(last_sent.tzinfo) - last_sent
                                if time_diff < timedelta(minutes=10):
                                    logger.info(f"📱 SMS sent recently to phone {phone} ({time_diff.total_seconds():.0f}s ago), skipping SMS fallback for call {call_id}")
                                    sms_already_sent = True
                                    break
                            except (ValueError, AttributeError):
                                pass
            except Exception as pre_check_error:
                logger.warning(f"⚠️  Could not pre-check SMS status: {pre_check_error}")
        
        if sms_already_sent:
            return
        
        # Mark this call_id as "checking SMS" to prevent other tasks from proceeding
        # This ensures only ONE task per phone number waits and checks
        async with _phone_sms_checking_lock:
            if phone_normalized:
                if phone_normalized not in _phone_sms_checking:
                    _phone_sms_checking[phone_normalized] = set()
                # If another call_id is already checking for this phone, skip this one
                if _phone_sms_checking[phone_normalized]:
                    existing_call_ids = list(_phone_sms_checking[phone_normalized])
                    logger.info(f"📱 Another call ({existing_call_ids}) is already checking SMS eligibility for phone {phone}, skipping call {call_id}")
                    return
                _phone_sms_checking[phone_normalized].add(call_id)
                logger.info(f"📱 Marked call {call_id} as checking SMS for phone {phone}")
    
    # Wait 45 seconds for call to complete or fail (longer wait for better accuracy)
    # Lock is released during wait, but call_id is marked as "checking" to prevent duplicates
    await asyncio.sleep(45)
    
    vapi = VapiClient()
    ghl = GHLClient()
    twilio = TwilioService()
    
    # Use try-finally to ensure checking set is cleaned up even on exceptions
    try:
        # Get call status from Vapi
        call_info = await vapi.get_call(call_id)
        call_status = call_info.get("status", "").lower()
        call_duration = call_info.get("duration", 0)  # Duration in seconds
        ended_reason = call_info.get("endedReason", "").lower() if call_info.get("endedReason") else ""
        
        logger.info(f"📞 Call {call_id} status: {call_status}, duration: {call_duration}s, endedReason: {ended_reason}")
        
        # Determine if call was not picked up (Vapi API endedReason values)
        # CRITICAL: Only send SMS if call was clearly NOT answered
        # Do NOT send SMS if call was answered (even if short duration)
        #
        # Vapi endedReason for unanswered: customer-did-not-answer, customer-busy, voicemail,
        # machine-detected, pipeline-error-*, twilio-failed-to-connect-call (call never reached customer)
        UNANSWERED_ENDED_REASONS = [
            "customer-did-not-answer",   # no answer (rang out)
            "customer-busy",             # declined/busy
            "voicemail",                  # voicemail detected
            "machine-detected",           # voicemail/machine
            "customer-did-not-give-microphone-permission",
            "twilio-failed-to-connect-call",  # Twilio couldn't connect; still send SMS fallback
            "no-answer",                  # legacy
            "busy", "failed", "canceled",
        ]

        def _is_unanswered_reason(reason: str) -> bool:
            if not reason:
                return False
            if reason in UNANSWERED_ENDED_REASONS:
                return True
            if reason.startswith("pipeline-error-"):
                return True
            return False

        # Status values that indicate call wasn't answered
        unanswered_statuses = ["failed", "no-answer", "busy", "canceled", "voicemail"]

        # Call was answered: ended, had meaningful duration, and reason is not an unanswered reason
        call_was_answered = (
            call_status == "ended"
            and call_duration > 0
            and not _is_unanswered_reason(ended_reason)
            and call_duration >= 5  # 5+ seconds likely answered
        )

        # Call was not answered: status or endedReason indicates no answer / failed / voicemail
        call_not_answered = (
            call_status == "failed"
            or call_status in unanswered_statuses
            or _is_unanswered_reason(ended_reason)
            or "voicemail" in call_status
            or (
                call_status == "ended"
                and call_duration < 5
                and _is_unanswered_reason(ended_reason)
            )
        )

        # CRITICAL: If call was answered, do NOT send SMS
        # Clean up the checking set before returning
        if call_was_answered:
            logger.info(f"📞 Call {call_id} was answered (status: {call_status}, duration: {call_duration}s, reason: {ended_reason}). Skipping SMS fallback.")
            # Clean up checking set
            async with _phone_sms_checking_lock:
                if phone_normalized and phone_normalized in _phone_sms_checking:
                    _phone_sms_checking[phone_normalized].discard(call_id)
                    if not _phone_sms_checking[phone_normalized]:
                        del _phone_sms_checking[phone_normalized]
            return
        
        if call_not_answered:
            logger.info(f"📞 Call {call_id} was not answered (reason: {ended_reason}). Sending SMS fallback.")
            
            # CRITICAL: Re-acquire phone lock and verify this call_id is still the one checking
            # This ensures only ONE SMS is sent per phone number, even if multiple contacts share it
            phone_lock = await get_phone_lock(phone)
            
            async with phone_lock:
                # Verify this call_id is still the one checking (prevent race conditions)
                async with _phone_sms_checking_lock:
                    if phone_normalized:
                        checking_calls = _phone_sms_checking.get(phone_normalized, set())
                        if call_id not in checking_calls:
                            existing_call_ids = list(checking_calls) if checking_calls else []
                            logger.info(f"📱 Another call ({existing_call_ids}) is already processing SMS for phone {phone}, skipping call {call_id}")
                            return
                        # Remove this call_id from checking set (we're proceeding)
                        checking_calls.discard(call_id)
                        logger.info(f"📱 Removed call {call_id} from checking set for phone {phone}, proceeding with SMS check")
                        if not checking_calls:
                            del _phone_sms_checking[phone_normalized]
                
                # CRITICAL: Check phone number FIRST (before getting contact) to prevent duplicates
                # This ensures only ONE SMS per phone number across ALL contacts
                phone_normalized = normalize_phone_for_comparison(phone)
                phone_already_sent = False
                if phone_normalized:
                    # Search for ALL contacts with this phone number
                    try:
                        contacts_with_phone = await ghl.search_contacts_by_phone(phone)
                        if contacts_with_phone:
                            # Check if ANY contact with this phone has received SMS recently
                            for contact_with_phone in contacts_with_phone:
                                contact_custom_fields = await custom_fields_to_dict(contact_with_phone.get("customFields", []))
                                
                                # Check both the boolean flag AND date field
                                contact_sms_sent = (
                                    contact_custom_fields.get("sms_fallback_sent") or 
                                    contact_custom_fields.get("contact.sms_fallback_sent") or 
                                    "false"
                                )
                                if str(contact_sms_sent).lower() == "true":
                                    logger.info(f"📱 SMS fallback already sent to phone {phone} (contact {contact_with_phone.get('id')}, flag is true), skipping duplicate")
                                    phone_already_sent = True
                                    break
                                
                                contact_sms_date = (
                                    contact_custom_fields.get("sms_fallback_sent_at") or 
                                    contact_custom_fields.get("contact.sms_fallback_sent_at") or
                                    contact_custom_fields.get("sms_fallback_date") or 
                                    contact_custom_fields.get("contact.sms_fallback_date") or 
                                    None
                                )
                                if contact_sms_date:
                                    try:
                                        last_sent = datetime.fromisoformat(contact_sms_date.replace('Z', '+00:00'))
                                        time_diff = datetime.now(last_sent.tzinfo) - last_sent
                                        # If sent within last 10 minutes, skip duplicate
                                        if time_diff < timedelta(minutes=10):
                                            logger.info(f"📱 SMS fallback sent recently to phone {phone} (contact {contact_with_phone.get('id')}, {time_diff.total_seconds():.0f}s ago), skipping duplicate")
                                            phone_already_sent = True
                                            break
                                    except (ValueError, AttributeError):
                                        pass
                    except Exception as search_error:
                        logger.warning(f"⚠️  Could not search contacts by phone for deduplication: {search_error}")
                
                if phone_already_sent:
                    logger.info(f"📱 SMS fallback already sent to phone {phone} (checked under lock), skipping duplicate")
                    # Clean up checking set before returning
                    async with _phone_sms_checking_lock:
                        if phone_normalized and phone_normalized in _phone_sms_checking:
                            _phone_sms_checking[phone_normalized].discard(call_id)
                            if not _phone_sms_checking[phone_normalized]:
                                del _phone_sms_checking[phone_normalized]
                    return
                
                # Get contact to check SMS consent
                contact_response = await ghl.get_contact(contact_id=contact_id)
                if not contact_response:
                    logger.warning(f"Contact {contact_id} not found for SMS fallback")
                    # Clean up checking set before returning
                    async with _phone_sms_checking_lock:
                        if phone_normalized and phone_normalized in _phone_sms_checking:
                            _phone_sms_checking[phone_normalized].discard(call_id)
                            if not _phone_sms_checking[phone_normalized]:
                                del _phone_sms_checking[phone_normalized]
                    return
                
                contact = contact_response.get("contact", contact_response) if isinstance(contact_response, dict) else contact_response
                custom_fields = await custom_fields_to_dict(contact.get("customFields"))
                
                # CRITICAL: Skip SMS fallback for inbound leads (people who called in)
                # SMS fallback is ONLY for outbound leads (form submissions, ads, web chat, etc.)
                # Inbound callers should NOT receive "we tried to reach you" messages
                lead_source = (
                    custom_fields.get("lead_source") or 
                    custom_fields.get("contact.lead_source") or 
                    None
                )
                
                if lead_source:
                    lead_source_lower = str(lead_source).lower()
                    # If lead source is "inbound", skip SMS fallback (they already called in)
                    if lead_source_lower == "inbound":
                        logger.info(f"📱 Skipping SMS fallback for contact {contact_id} - lead source is 'inbound' (they called in, not an outbound lead)")
                        # Clean up checking set before returning
                        async with _phone_sms_checking_lock:
                            if phone_normalized and phone_normalized in _phone_sms_checking:
                                _phone_sms_checking[phone_normalized].discard(call_id)
                                if not _phone_sms_checking[phone_normalized]:
                                    del _phone_sms_checking[phone_normalized]
                        return
                
                # Check both formats: "sms_consent" and "contact.sms_consent"
                # Default to True (opt-out model) if not explicitly set
                sms_consent_value = (
                    custom_fields.get("sms_consent") or 
                    custom_fields.get("contact.sms_consent") or 
                    None
                )
                
                if sms_consent_value is not None:
                    sms_consent = str(sms_consent_value).lower() in ["true", "1", "yes"]
                else:
                    # Default to allow SMS if consent not set (opt-out model)
                    sms_consent = True
                    logger.info(f"📱 SMS consent not set for contact {contact_id}, defaulting to allow (opt-out model)")
                
                sms_fallback_sent = (
                    custom_fields.get("sms_fallback_sent") or 
                    custom_fields.get("contact.sms_fallback_sent") or 
                    "false"
                )
                sms_fallback_sent = str(sms_fallback_sent).lower() == "true"
                
                # Check if SMS fallback was sent recently (within last 10 minutes) to prevent duplicates
                # Check both field names for compatibility
                sms_fallback_date = (
                    custom_fields.get("sms_fallback_sent_at") or 
                    custom_fields.get("contact.sms_fallback_sent_at") or
                    custom_fields.get("sms_fallback_date") or 
                    custom_fields.get("contact.sms_fallback_date") or 
                    None
                )
                
                recently_sent = False
                if sms_fallback_date:
                    try:
                        last_sent = datetime.fromisoformat(sms_fallback_date.replace('Z', '+00:00'))
                        time_diff = datetime.now(last_sent.tzinfo) - last_sent
                        # If sent within last 10 minutes, consider it recently sent
                        if time_diff < timedelta(minutes=10):
                            recently_sent = True
                            logger.info(f"📱 SMS fallback sent recently ({time_diff.total_seconds():.0f}s ago, {time_diff.seconds//60} minutes), skipping duplicate")
                            return
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"⚠️  Could not parse sms_fallback_date: {e}")
                
                # Send SMS fallback if consent given and not already sent (and not sent recently)
                # Note: phone_already_sent is already checked above under the lock
                if sms_consent and not sms_fallback_sent and not recently_sent and not phone_already_sent:
                    # CRITICAL: Mark as "sending" BEFORE sending SMS (optimistic locking)
                    # This prevents other tasks from sending duplicate SMS while we're sending
                    sms_fallback_fields = {
                        "sms_fallback_sent": "true",  # Mark as sent immediately
                        "sms_fallback_sent_at": datetime.now().isoformat(),
                        "sms_fallback_date": datetime.now().isoformat(),
                        "sms_fallback_reason": call_status
                    }
                    custom_fields_update = await build_custom_fields_array(sms_fallback_fields, use_field_ids=True)
                    
                    # Update THIS contact FIRST (before sending SMS) to prevent duplicates
                    try:
                        await ghl.update_contact(
                            contact_id=contact_id,
                            contact_data={
                                "customFields": custom_fields_update
                            }
                        )
                        logger.info(f"📱 Marked SMS fallback as sent for contact {contact_id} (before sending)")
                    except Exception as mark_error:
                        logger.warning(f"⚠️  Could not mark SMS as sent before sending: {mark_error}")
                    
                    # Get contact name for personalized message
                    first_name = contact.get("firstName", "") or contact.get("first_name", "")
                    name_greeting = f"Hi {first_name}!" if first_name else "Hi!"
                    
                    sms_message = (
                        f"{name_greeting} This is Valley View HVAC. We tried to reach you but couldn't connect. "
                        f"Would you like to schedule a heating or cooling service appointment? "
                        f"Reply YES or call us at 971-712-6763. We're here to help! - Valley View HVAC"
                    )
                    
                    # Note: We're already under the phone_lock, so no need to double-check here
                    # The lock ensures only one task can send SMS to this phone number at a time
                    try:
                        result = twilio.send_sms(to=phone, message=sms_message)
                        logger.info(f"✅ SMS fallback sent to {phone} for failed call {call_id}, SMS SID: {result.get('message_sid')}")
                        
                        # CRITICAL: Also update ALL other contacts with this phone number to prevent duplicates
                        if phone_normalized:
                            try:
                                contacts_with_phone = await ghl.search_contacts_by_phone(phone)
                                if contacts_with_phone:
                                    for contact_with_phone in contacts_with_phone:
                                        other_contact_id = contact_with_phone.get("id")
                                        if other_contact_id and other_contact_id != contact_id:
                                            try:
                                                await ghl.update_contact(
                                                    contact_id=other_contact_id,
                                                    contact_data={
                                                        "customFields": custom_fields_update
                                                    }
                                                )
                                                logger.info(f"📱 Updated SMS fallback flag for contact {other_contact_id} (same phone number)")
                                            except Exception as update_error:
                                                logger.warning(f"⚠️  Could not update contact {other_contact_id}: {update_error}")
                            except Exception as search_error:
                                logger.warning(f"⚠️  Could not search contacts by phone for update: {search_error}")
                    except Exception as sms_error:
                        logger.error(f"Failed to send SMS fallback to {phone}: {str(sms_error)}")
                        # If SMS sending failed, we should unmark the "sent" status
                        # But for now, we'll leave it marked to prevent retry loops
                elif phone_already_sent:
                    logger.info(f"📱 SMS fallback already sent to phone {phone} recently (checked across all contacts), skipping duplicate")
                elif not sms_consent:
                    logger.info(f"SMS consent not given for contact {contact_id}, skipping SMS fallback")
                elif sms_fallback_sent:
                    logger.info(f"SMS fallback already sent for contact {contact_id}, skipping")
        else:
            logger.info(f"Call {call_id} succeeded with status: {call_status}, no SMS fallback needed")
    except Exception as e:
        logger.exception(f"Error in SMS fallback check for call {call_id}: {str(e)}")
    finally:
        # CRITICAL: Always clean up the checking set, even on exceptions or early returns
        # This ensures the phone number is not blocked forever
        async with _phone_sms_checking_lock:
            if phone_normalized and phone_normalized in _phone_sms_checking:
                _phone_sms_checking[phone_normalized].discard(call_id)
                if not _phone_sms_checking[phone_normalized]:
                    del _phone_sms_checking[phone_normalized]
                    logger.info(f"📱 Cleaned up checking set for phone {phone} (call {call_id})")


async def handle_appointment_created(contact_id: Optional[str], data: Dict[str, Any]):
    """
    Handle appointment.created webhook from GHL.
    Adds appointment to in-memory cache for availability checking.
    """
    logger.info(f"📅 Appointment created webhook received for contact {contact_id}")
    
    # Extract appointment details from webhook data
    try:
        from src.utils.appointment_cache import add_appointment_to_cache
        
        # Try multiple possible field names for appointment data
        appointment_data = (
            data.get("appointment") or
            data.get("data") or
            data
        )
        
        calendar_id = (
            appointment_data.get("calendarId") or
            appointment_data.get("calendar_id") or
            appointment_data.get("calendar") or
            ""
        )
        
        start_time = (
            appointment_data.get("startTime") or
            appointment_data.get("start_time") or
            appointment_data.get("startDate") or
            appointment_data.get("start")
        )
        
        end_time = (
            appointment_data.get("endTime") or
            appointment_data.get("end_time") or
            appointment_data.get("endDate") or
            appointment_data.get("end")
        )
        
        if calendar_id and start_time:
            add_appointment_to_cache(
                calendar_id=calendar_id,
                start_time=start_time,
                end_time=end_time
            )
            logger.info(f"✅ Added appointment to cache from webhook: {calendar_id} at {start_time}")
        else:
            logger.warning(f"⚠️ Appointment webhook missing calendar_id or start_time: {data}")
    except Exception as e:
        logger.warning(f"⚠️ Error processing appointment.created webhook: {e}")


async def handle_form_submission(webhook_body: Dict[str, Any]):
    """Handle form submission event"""
    logger.info("Form submission received")
    # Extract contact_id from webhook body (can be at top level or in customData)
    contact_id = (
        webhook_body.get("contact_id") or
        webhook_body.get("contactId") or
        webhook_body.get("contact", {}).get("id") or
        webhook_body.get("customData", {}).get("contactId") or
        webhook_body.get("customData", {}).get("contact_id") or
        None
    )
    
    if contact_id:
        # CRITICAL: Add "outbound" tag to form submissions before triggering call
        # This ensures form submissions are treated as outbound leads
        ghl = GHLClient()
        try:
            await ghl.add_tags_to_contact(contact_id, ["outbound"])
            logger.info(f"📝 Added 'outbound' tag to contact {contact_id} from form submission")
        except Exception as tag_error:
            logger.warning(f"⚠️  Could not add 'outbound' tag to contact {contact_id}: {tag_error}")
            # Continue anyway - the tag check in handle_new_lead will skip if tag is missing
        
        # Trigger outbound call for form submissions
        logger.info(f"📝 Form submission for contact {contact_id}, triggering outbound call")
        await handle_new_lead(contact_id, webhook_body)
    else:
        logger.warning("No contact ID found in form submission data")
        logger.warning(f"Available keys in webhook body: {list(webhook_body.keys())}")


async def handle_chat_conversion(data: Dict[str, Any]):
    """Handle web chat conversion event"""
    logger.info("Chat conversion received")
    # Extract contact_id from chat conversion data
    contact_id = (
        data.get("contactId") or
        data.get("contact", {}).get("id") or
        data.get("conversation", {}).get("contactId") or
        data.get("chat", {}).get("contactId")
    )
    
    if contact_id:
        # CRITICAL: Add "outbound" tag to chat conversions before triggering call
        # This ensures chat conversions are treated as outbound leads
        ghl = GHLClient()
        try:
            await ghl.add_tags_to_contact(contact_id, ["outbound"])
            logger.info(f"💬 Added 'outbound' tag to contact {contact_id} from chat conversion")
        except Exception as tag_error:
            logger.warning(f"⚠️  Could not add 'outbound' tag to contact {contact_id}: {tag_error}")
            # Continue anyway - the tag check in handle_new_lead will skip if tag is missing
        
        logger.info(f"Chat conversion for contact {contact_id}, triggering outbound call")
        await handle_new_lead(contact_id, data)
    else:
        logger.warning("No contact ID found in chat conversion data")


async def handle_ad_lead(data: Dict[str, Any]):
    """Handle Google/Meta ad lead submission"""
    logger.info("Ad lead submission received")
    # Extract contact_id from ad lead data
    contact_id = (
        data.get("contactId") or
        data.get("contact", {}).get("id") or
        data.get("lead", {}).get("contactId") or
        data.get("ad", {}).get("contactId")
    )
    
    # Extract lead source for tracking
    lead_source = (
        data.get("source") or
        data.get("leadSource") or
        data.get("ad", {}).get("platform") or
        "unknown"
    )
    
    if contact_id:
        # CRITICAL: Add "outbound" tag to ad leads before triggering call
        # This ensures ad leads are treated as outbound leads
        ghl = GHLClient()
        try:
            await ghl.add_tags_to_contact(contact_id, ["outbound"])
            logger.info(f"📢 Added 'outbound' tag to contact {contact_id} from ad lead ({lead_source})")
        except Exception as tag_error:
            logger.warning(f"⚠️  Could not add 'outbound' tag to contact {contact_id}: {tag_error}")
            # Continue anyway - the tag check in handle_new_lead will skip if tag is missing
        
        logger.info(f"Ad lead from {lead_source} for contact {contact_id}, triggering outbound call")
        # Add lead source to data for tracking
        if "leadSource" not in data:
            data["leadSource"] = lead_source
        await handle_new_lead(contact_id, data)
    else:
        logger.warning("No contact ID found in ad lead data")


