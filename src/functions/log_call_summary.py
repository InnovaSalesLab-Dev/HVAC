from src.models import LogCallSummaryRequest, LogCallSummaryResponse
from src.integrations.ghl import GHLClient
from src.utils.lead_scoring import calculate_lead_quality_score
from src.utils.ghl_fields import build_custom_fields_array
from src.utils.logging import logger
from datetime import datetime


async def log_call_summary(request: LogCallSummaryRequest) -> LogCallSummaryResponse:
    """
    Save call transcript and AI summary to GHL contact timeline.
    Also updates custom fields with call metadata.
    """
    ghl = GHLClient()
    
    try:
        # Create timeline note with transcript and summary
        note_content = f"""
Call Summary:
{request.summary}

Call Type: {request.call_type.value if request.call_type else 'Unknown'}
Duration: {request.call_duration} seconds
Outcome: {request.outcome or 'N/A'}

Full Transcript:
{request.transcript}
"""
        
        # Add note to timeline
        note_result = await ghl.add_timeline_note(
            contact_id=request.contact_id,
            note=note_content
        )
        
        note_id = note_result.get("id", "")
        
        # Get contact data for lead scoring
        contact_response = await ghl.get_contact(contact_id=request.contact_id)
        contact_data = contact_response.get("contact", contact_response) if isinstance(contact_response, dict) else contact_response
        
        # Calculate lead quality score
        call_data = {
            "outcome": request.outcome,
            "call_duration": request.call_duration,
            "call_timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else None
        }
        lead_score = calculate_lead_quality_score(contact_data or {}, call_data)
        
        # Extract equipment types from transcript/summary if mentioned
        equipment_types = []
        transcript_lower = (request.transcript or "").lower()
        summary_lower = (request.summary or "").lower()
        combined_text = transcript_lower + " " + summary_lower
        
        # Common HVAC equipment keywords
        equipment_keywords = {
            "furnace": ["furnace", "heating system", "heater"],
            "air_conditioner": ["ac", "air conditioner", "air conditioning", "cooling system"],
            "heat_pump": ["heat pump", "heatpump"],
            "ductless": ["ductless", "mini split", "mini-split", "split system"],
            "thermostat": ["thermostat", "nest", "ecobee"],
            "ductwork": ["duct", "ductwork", "air ducts"],
            "air_handler": ["air handler", "airhandler"],
            "evaporator": ["evaporator", "evap coil"],
            "condenser": ["condenser", "condensing unit"]
        }
        
        for equipment_type, keywords in equipment_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                equipment_types.append(equipment_type)
        
        # Update custom fields (GHL API expects customFields array format)
        # GHL uses "contact.{key}" format for field keys
        custom_fields_dict = {
            "ai_call_summary": request.summary,
            "call_transcript_url": request.transcript_url or "",
            "call_duration": str(request.call_duration or 0),
            "call_type": request.call_type.value if request.call_type else "",
            "call_outcome": request.outcome or "",
            "lead_quality_score": str(lead_score),
            "equipment_type_tags": ",".join(equipment_types) if equipment_types else ""
        }
        # Build custom fields array - use field IDs for better reliability
        custom_fields_array = await build_custom_fields_array(custom_fields_dict, use_field_ids=True)
        
        await ghl.update_contact(
            contact_id=request.contact_id,
            contact_data={"customFields": custom_fields_array}
        )
        
        logger.info(f"Updated contact {request.contact_id} with lead score: {lead_score}, equipment types: {equipment_types}")
        
        return LogCallSummaryResponse(
            success=True,
            note_id=note_id
        )
    except Exception as e:
        return LogCallSummaryResponse(
            success=False,
            note_id=None
        )


