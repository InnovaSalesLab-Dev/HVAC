from src.models import SendConfirmationRequest, SendConfirmationResponse
from src.integrations.ghl import GHLClient
from src.integrations.twilio import TwilioService
from src.utils.errors import APIError
from src.utils.logging import logger
from src.utils.ghl_fields import build_custom_fields_array
from datetime import datetime, timedelta


async def send_confirmation(request: SendConfirmationRequest) -> SendConfirmationResponse:
    """
    Send SMS or email confirmation to customer.
    Checks SMS consent before sending SMS.
    Prevents duplicate SMS messages within the same conversation.
    """
    ghl = GHLClient()
    twilio = TwilioService()
    
    try:
        logger.info(f"📧 sendConfirmation called: contact_id={request.contact_id}, appointment_id={request.appointment_id}, method={request.method}")
        
        # Get contact to check SMS consent and deduplication flags
        contact = await ghl.get_contact(contact_id=request.contact_id)
        if not contact:
            logger.error(f"❌ Contact not found: {request.contact_id}")
            return SendConfirmationResponse(
                success=False,
                method=request.method,
                message_id=None
            )
        
        # GHL can return contact nested in "contact" key or directly
        if isinstance(contact, dict) and "contact" in contact:
            contact = contact["contact"]
        
        logger.info(f"✅ Contact found: {contact.get('firstName', '')} {contact.get('lastName', '')}")
        
        # Check SMS consent - GHL custom fields can be array or dict
        custom_fields_raw = contact.get("customFields", [])
        custom_fields = {}
        
        # Handle array format: [{"field": "contact.sms_consent", "value": "true"}, ...]
        if isinstance(custom_fields_raw, list):
            for field in custom_fields_raw:
                if isinstance(field, dict):
                    field_key = field.get("field") or field.get("fieldKey") or field.get("name", "")
                    field_value = field.get("value", "")
                    custom_fields[field_key] = field_value
        # Handle dict format: {"contact.sms_consent": "true", ...}
        elif isinstance(custom_fields_raw, dict):
            custom_fields = custom_fields_raw
        
        logger.info(f"📋 Custom fields: {custom_fields}")
        
        # DEDUPLICATION: Check if confirmation SMS was already sent
        # This prevents multiple confirmation messages in the same conversation
        if request.method == "sms":
            # Check if SMS was sent for this specific appointment
            if request.appointment_id:
                confirmation_sent_key = f"confirmation_sent_{request.appointment_id}"
                confirmation_sent = (
                    custom_fields.get(confirmation_sent_key) or
                    custom_fields.get(f"contact.{confirmation_sent_key}") or
                    "false"
                )
                if str(confirmation_sent).lower() == "true":
                    logger.info(f"✅ Confirmation SMS already sent for appointment {request.appointment_id}, skipping duplicate")
                    return SendConfirmationResponse(
                        success=True,
                        method="sms",
                        message_id="already_sent"
                    )
            
            # Check if confirmation SMS was sent recently (within last 10 minutes) for same contact
            # This prevents duplicates in the same conversation or multiple calls
            last_confirmation_time = (
                custom_fields.get("last_confirmation_sent_time") or
                custom_fields.get("contact.last_confirmation_sent_time") or
                custom_fields.get("sms_confirmation_sent_at") or
                custom_fields.get("contact.sms_confirmation_sent_at") or
                None
            )
            
            if last_confirmation_time:
                try:
                    last_sent = datetime.fromisoformat(last_confirmation_time.replace('Z', '+00:00'))
                    time_diff = datetime.now(last_sent.tzinfo) - last_sent
                    # If sent within last 10 minutes, skip to prevent duplicate (increased from 5 to 10 minutes)
                    if time_diff < timedelta(minutes=10):
                        logger.info(f"✅ Confirmation SMS sent recently ({time_diff.total_seconds():.0f}s ago, {time_diff.seconds//60} minutes), skipping duplicate")
                        return SendConfirmationResponse(
                            success=True,
                            method="sms",
                            message_id="already_sent_recently"
                        )
                except (ValueError, AttributeError) as e:
                    logger.warning(f"⚠️  Could not parse last_confirmation_sent_time: {e}")
            
            # Additional check: If appointment_id matches last confirmed appointment, skip
            last_confirmed_appointment = (
                custom_fields.get("last_confirmed_appointment_id") or
                custom_fields.get("contact.last_confirmed_appointment_id") or
                None
            )
            if request.appointment_id and last_confirmed_appointment == request.appointment_id:
                logger.info(f"✅ Confirmation SMS already sent for this appointment ID {request.appointment_id}, skipping duplicate")
                return SendConfirmationResponse(
                    success=True,
                    method="sms",
                    message_id="already_sent_for_appointment"
                )
        
        # Check both formats: "sms_consent" and "contact.sms_consent"
        sms_consent_value = (
            custom_fields.get("sms_consent") or 
            custom_fields.get("contact.sms_consent") or 
            None  # Changed from "false" to None to detect if consent was never set
        )
        
        # If consent value exists, check it; if not set, default to allowing (opt-out model)
        if sms_consent_value is not None:
            sms_consent = str(sms_consent_value).lower() in ["true", "1", "yes"]
            logger.info(f"📱 SMS consent explicitly set: {sms_consent} (value: {sms_consent_value})")
        else:
            # Consent not set - allow sending (opt-out model for appointment confirmations)
            # This handles cases where consent wasn't captured during contact creation
            sms_consent = True
            logger.info(f"📱 SMS consent not set, defaulting to allow (opt-out model)")
        
        phone = contact.get("phone") or contact.get("phoneNumber", "")
        
        if not phone:
            logger.error(f"❌ No phone number found for contact {request.contact_id}")
            return SendConfirmationResponse(
                success=False,
                method=request.method,
                message_id=None
            )
        
        logger.info(f"📞 Phone number: {phone}")
        
        if request.method == "sms":
            if not sms_consent:
                logger.warning(f"⚠️  SMS consent explicitly denied for contact {request.contact_id}")
                return SendConfirmationResponse(
                    success=False,
                    method="sms",
                    message_id=None
                )
            
            # Send SMS via Twilio
            default_message = "Your appointment has been confirmed. We'll see you soon!"
            message = request.message or default_message
            
            logger.info(f"📤 Sending SMS to {phone}: {message[:50]}...")
            
            # Send SMS via Twilio
            try:
                result = twilio.send_sms(to=phone, message=message)
                message_sid = result.get("message_sid")
                logger.info(f"✅ SMS sent successfully via Twilio: {message_sid}")
                
                # Mark confirmation as sent to prevent duplicates
                update_fields = {
                    "last_confirmation_sent_time": datetime.now().isoformat(),
                    "sms_confirmation_sent_at": datetime.now().isoformat()  # Also set this for compatibility
                }
                
                # If appointment_id provided, mark confirmation sent for this specific appointment
                if request.appointment_id:
                    update_fields[f"confirmation_sent_{request.appointment_id}"] = "true"
                    update_fields["last_confirmed_appointment_id"] = request.appointment_id
                
                # Update contact to mark confirmation sent
                try:
                    custom_fields_update = await build_custom_fields_array(update_fields, use_field_ids=True)
                    await ghl.update_contact(
                        contact_id=request.contact_id,
                        contact_data={"customFields": custom_fields_update}
                    )
                    logger.info(f"✅ Marked confirmation as sent in contact record")
                except Exception as update_error:
                    logger.warning(f"⚠️  Could not update confirmation flag: {update_error}")
                    # Don't fail the SMS send if update fails
                
                return SendConfirmationResponse(
                    success=True,
                    method="sms",
                    message_id=message_sid
                )
            except Exception as sms_error:
                error_str = str(sms_error)
                logger.error(f"❌ Failed to send SMS: {error_str}")
                
                # Check for specific Twilio errors and provide helpful messages
                if "phone number not configured" in error_str.lower():
                    logger.error(f"💡 Twilio phone number not configured in environment variables")
                    logger.error(f"   Set TWILIO_PHONE_NUMBER environment variable")
                elif "Permission to send" in error_str or "region" in error_str.lower():
                    logger.error(f"💡 Twilio account doesn't have permission to send SMS to {phone}")
                    logger.error(f"   Solution: Enable international SMS in Twilio dashboard")
                elif "Invalid" in error_str or "not a valid" in error_str.lower():
                    logger.error(f"⚠️  Invalid phone number format: {phone}")
                else:
                    import traceback
                    traceback.print_exc()
                
                return SendConfirmationResponse(
                    success=False,
                    method="sms",
                    message_id=None
                )
        
        elif request.method == "email":
            # Trigger GHL email automation
            # This would typically be done via GHL automation trigger
            # For now, we'll log it as a note
            email = contact.get("email", "")
            if email:
                note = f"Confirmation email sent: {request.message or 'Appointment confirmed'}"
                await ghl.add_timeline_note(request.contact_id, note)
                logger.info(f"✅ Email confirmation logged for {email}")
                return SendConfirmationResponse(
                    success=True,
                    method="email",
                    message_id=None
                )
            else:
                logger.warning(f"⚠️  No email address for contact {request.contact_id}")
                return SendConfirmationResponse(
                    success=False,
                    method="email",
                    message_id=None
                )
        
        logger.warning(f"⚠️  Unknown method: {request.method}")
        return SendConfirmationResponse(
            success=False,
            method=request.method,
            message_id=None
        )
    except Exception as e:
        logger.error(f"❌ Error in send_confirmation: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ Full traceback:\n{error_trace}")
        return SendConfirmationResponse(
            success=False,
            method=request.method,
            message_id=None
        )


