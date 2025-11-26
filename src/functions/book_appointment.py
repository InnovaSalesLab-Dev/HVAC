from src.models import BookAppointmentRequest, BookAppointmentResponse
from src.integrations.ghl import GHLClient


async def book_appointment(request: BookAppointmentRequest) -> BookAppointmentResponse:
    """
    Book appointment in GHL calendar via webhook trigger.
    
    This function sends appointment data to GHL via custom fields,
    which triggers a GHL automation to create the appointment.
    """
    from src.utils.logging import logger
    
    ghl = GHLClient()
    
    # If rescheduling, cancel the existing appointment first
    if request.reschedule_appointment_id:
        try:
            logger.info(f"🔄 Rescheduling appointment {request.reschedule_appointment_id} for contact {request.contact_id}")
            # Try to cancel the existing appointment via GHL API
            cancel_result = await ghl.cancel_appointment(request.reschedule_appointment_id, request.contact_id)
            if cancel_result.get("success"):
                method = cancel_result.get("method", "unknown")
                # Add to cancellation cache so it's filtered out from existing appointments check
                from src.utils.cancellation_cache import add_cancelled_appointment
                add_cancelled_appointment(request.contact_id, request.reschedule_appointment_id)
                
                if method == "timeline_note":
                    logger.warning(f"⚠️ Cancellation only added timeline note (API cancellation failed), but proceeding with rescheduling")
                    logger.warning(f"   The old appointment may still appear in GHL until manually cancelled")
                else:
                    logger.info(f"✅ Cancelled existing appointment {request.reschedule_appointment_id} via {method}")
            else:
                error = cancel_result.get("error", "Unknown error")
                logger.warning(f"⚠️ Could not cancel appointment via API: {error}")
                logger.warning(f"   Proceeding with new booking anyway - old appointment may need manual cancellation")
                # Still add to cache even if cancellation failed, so it's filtered out
                from src.utils.cancellation_cache import add_cancelled_appointment
                add_cancelled_appointment(request.contact_id, request.reschedule_appointment_id)
        except Exception as cancel_error:
            logger.warning(f"⚠️ Error cancelling appointment (non-fatal): {cancel_error}")
            # Still add to cache even if error occurred, so it's filtered out
            try:
                from src.utils.cancellation_cache import add_cancelled_appointment
                add_cancelled_appointment(request.contact_id, request.reschedule_appointment_id)
            except:
                pass
            # Continue with booking - the new appointment will be created
    
    # Check if contact already has an appointment scheduled (only if not rescheduling)
    # If rescheduling, we'll filter out the appointment being rescheduled from the check
    existing_appointments = []
    try:
        existing_appointments = await ghl.get_contact_appointments(request.contact_id)
        if existing_appointments:
            # Filter out the appointment being rescheduled (if any)
            if request.reschedule_appointment_id:
                existing_appointments = [
                    apt for apt in existing_appointments
                    if (apt.get("id") != request.reschedule_appointment_id and 
                        apt.get("appointmentId") != request.reschedule_appointment_id and
                        apt.get("appointment_id") != request.reschedule_appointment_id)
                ]
                logger.info(f"🔄 Filtered out rescheduling appointment {request.reschedule_appointment_id} from existing appointments check")
            
            # Only check for existing appointments if not rescheduling
            if not request.reschedule_appointment_id and existing_appointments:
                # Find the most recent/upcoming appointment
                from datetime import datetime
                from zoneinfo import ZoneInfo
                
                upcoming_appointments = []
                # Import cancellation cache to filter out recently cancelled appointments
                from src.utils.cancellation_cache import is_recently_cancelled
                
                for apt in existing_appointments:
                    apt_id = apt.get("id") or apt.get("appointmentId") or ""
                    apt_start = apt.get("startTime") or apt.get("start_time") or apt.get("startDate")
                    apt_title = apt.get("title") or apt.get("name") or "appointment"
                    
                    # Skip recently cancelled appointments (even if only via timeline note)
                    if apt_id and is_recently_cancelled(request.contact_id, apt_id):
                        logger.info(f"🔄 Skipping recently cancelled appointment {apt_id} from existing appointments check")
                        continue
                    
                    # Skip cancelled appointments (if status is available)
                    apt_status = apt.get("status") or apt.get("appointmentStatus") or ""
                    if apt_status and "cancel" in str(apt_status).lower():
                        logger.debug(f"Skipping cancelled appointment {apt_id}")
                        continue
                    
                    if apt_start:
                        try:
                            # Parse appointment time
                            apt_start_str = str(apt_start).replace("Z", "+00:00")
                            apt_start_dt = datetime.fromisoformat(apt_start_str)
                            
                            # Convert to Pacific time for display
                            if apt_start_dt.tzinfo:
                                apt_start_dt = apt_start_dt.astimezone(ZoneInfo("America/Los_Angeles"))
                            else:
                                apt_start_dt = apt_start_dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
                            
                            # Format for display
                            formatted_time = apt_start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
                            upcoming_appointments.append({
                                "id": apt_id,
                                "time": formatted_time,
                                "title": apt_title,
                                "datetime": apt_start_dt
                            })
                        except Exception as parse_error:
                            logger.debug(f"Could not parse appointment time: {parse_error}")
                            # Still include it with raw time
                            upcoming_appointments.append({
                                "id": apt_id,
                                "time": str(apt_start),
                                "title": apt_title,
                                "datetime": None
                            })
                
                # Sort by datetime (most recent/upcoming first)
                if upcoming_appointments:
                    upcoming_appointments.sort(key=lambda x: x["datetime"] if x["datetime"] else datetime.min.replace(tzinfo=ZoneInfo("America/Los_Angeles")))
                    next_appointment = upcoming_appointments[0]
                    
                    existing_appointment_id = next_appointment.get("id", "")
                    logger.warning(f"⚠️ Contact {request.contact_id} already has an appointment: {next_appointment['time']} (ID: {existing_appointment_id})")
                    return BookAppointmentResponse(
                        appointment_id=existing_appointment_id,  # Include appointment_id so AI can use it for rescheduling
                        success=False,
                        message=(
                            f"EXISTING_APPOINTMENT_FOUND: "
                            f"You already have an appointment scheduled for {next_appointment['time']}. "
                            f"Would you like to reschedule your existing appointment, or cancel it and book a new one?"
                        )
                    )
    except Exception as e:
        logger.warning(f"Could not check for existing appointments: {e}")
    
    try:
        result = await ghl.book_appointment(
            calendar_id=request.calendar_id,
            contact_id=request.contact_id,
            start_time=request.start_time,
            end_time=request.end_time,
            title=request.title,
            notes=request.notes,
            service_address=request.service_address,
            reschedule_appointment_id=request.reschedule_appointment_id
        )
        
        appointment_id = result.get("id", "")
        status = result.get("status", "")
        automation_triggered = result.get("automation_triggered", False)
        webhook_triggered = result.get("webhook_triggered", False)
        
        # Check if webhook/automation was triggered
        if webhook_triggered or automation_triggered or status in ["automation_triggered", "webhook_triggered"]:
            return BookAppointmentResponse(
                appointment_id=appointment_id,
                success=True,  # Return success since automation will create it
                message=(
                    f"Appointment scheduling request sent successfully. "
                    f"Your appointment for {request.start_time} has been submitted and will be confirmed shortly. "
                    f"Please note: The appointment will be created by our system within a few moments."
                )
            )
        
        # Check if this is a manual creation response (old format)
        if status == "pending_manual_creation" or appointment_id.startswith("manual-"):
            return BookAppointmentResponse(
                appointment_id=appointment_id,
                success=False,
                message=(
                    f"Appointment scheduling initiated. "
                    f"Note: GHL API doesn't support direct appointment creation. "
                    f"Please create the appointment manually in GHL dashboard: "
                    f"Contact ID: {request.contact_id}, "
                    f"Calendar ID: {request.calendar_id}, "
                    f"Time: {request.start_time}"
                )
            )
        
        return BookAppointmentResponse(
            appointment_id=appointment_id,
            success=True,
            message=f"Appointment booked successfully for {request.start_time}"
        )
    except Exception as e:
        # If booking fails, provide helpful error message
        error_msg = str(e)
        error_details = getattr(e, 'details', {})
        timeline_note_created = error_details.get('timeline_note_created', False)
        
        if "404" in error_msg or "Not Found" in error_msg or "GHL API does not appear to support" in error_msg:
            message = (
                f"⚠️ GHL API does not support direct appointment creation via REST API with API keys. "
                f"Appointment details have been saved to the contact's timeline in GHL. "
            )
            if timeline_note_created:
                message += "Please create the appointment manually in GHL dashboard using the timeline note."
            else:
                message += (
                    f"Please create appointment manually: "
                    f"Contact {request.contact_id}, Calendar {request.calendar_id}, "
                    f"Time {request.start_time} to {request.end_time}, Title: {request.title}"
                )
            
            return BookAppointmentResponse(
                appointment_id="",
                success=False,
                message=message
            )
        
        return BookAppointmentResponse(
            appointment_id="",
            success=False,
            message=f"Failed to book appointment: {error_msg}"
        )


