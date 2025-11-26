from src.models import CancelAppointmentRequest, CancelAppointmentResponse
from src.integrations.ghl import GHLClient


async def cancel_appointment(request: CancelAppointmentRequest) -> CancelAppointmentResponse:
    """
    Cancel an existing appointment in GHL.
    
    This function attempts to cancel an appointment via GHL API.
    If API cancellation is not supported, it adds a timeline note for manual cancellation.
    """
    from src.utils.logging import logger
    
    ghl = GHLClient()
    
    try:
        logger.info(f"🔄 Cancelling appointment {request.appointment_id} for contact {request.contact_id}")
        
        # Call GHL client's cancel_appointment method
        cancel_result = await ghl.cancel_appointment(request.appointment_id, request.contact_id)
        
        if cancel_result.get("success"):
            method = cancel_result.get("method", "unknown")
            logger.info(f"✅ Successfully cancelled appointment {request.appointment_id} via {method}")
            
            # Add to cancellation cache so it's filtered out from existing appointments check
            from src.utils.cancellation_cache import add_cancelled_appointment
            add_cancelled_appointment(request.contact_id, request.appointment_id)
            
            # Get appointment details for confirmation message
            appointment_details = ""
            try:
                contact_appointments = await ghl.get_contact_appointments(request.contact_id)
                for apt in contact_appointments:
                    if apt.get("id") == request.appointment_id or apt.get("appointmentId") == request.appointment_id:
                        apt_start = apt.get("startTime") or apt.get("start_time") or apt.get("startDate")
                        apt_title = apt.get("title") or apt.get("name") or "appointment"
                        if apt_start:
                            appointment_details = f" ({apt_title} on {apt_start})"
                        break
            except:
                pass
            
            message = f"Appointment {request.appointment_id}{appointment_details} has been cancelled successfully."
            
            if method == "timeline_note":
                message += " Note: The cancellation has been logged. Please verify in GHL dashboard."
            
            return CancelAppointmentResponse(
                success=True,
                message=message,
                method=method
            )
        else:
            error = cancel_result.get("error", "Unknown error")
            logger.warning(f"⚠️ Could not cancel appointment {request.appointment_id}: {error}")
            return CancelAppointmentResponse(
                success=False,
                message=f"Could not cancel appointment {request.appointment_id}. Error: {error}",
                method="failed"
            )
            
    except Exception as e:
        logger.error(f"❌ Error cancelling appointment: {e}")
        return CancelAppointmentResponse(
            success=False,
            message=f"Failed to cancel appointment: {str(e)}",
            method="error"
        )

