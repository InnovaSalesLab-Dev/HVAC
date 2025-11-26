from src.models import (
    CheckCalendarAvailabilityRequest,
    CheckCalendarAvailabilityResponse,
    CalendarSlot,
    ServiceType
)
from src.integrations.ghl import GHLClient
from src.utils.business_hours import get_current_date_pacific
from src.utils.logging import logger
from datetime import datetime, timedelta
from typing import List


async def check_calendar_availability(
    request: CheckCalendarAvailabilityRequest
) -> CheckCalendarAvailabilityResponse:
    """
    Check available appointment slots in GHL calendar.
    Maps service types to appropriate calendars.
    
    If start_date is not provided or is in the past, uses current date.
    """
    ghl = GHLClient()
    
    # Get current date and time if start_date is not provided or is in the past
    from src.utils.business_hours import get_current_datetime_pacific, check_business_hours
    current_datetime = get_current_datetime_pacific()
    current_date = current_datetime.date()
    current_time = current_datetime.time()
    
    start_date = request.start_date
    end_date = request.end_date
    
    # Validate dates - ensure start_date is not in the past
    # If today is past business hours (after 4:30 PM), start from tomorrow
    try:
        if start_date:
            start_dt = datetime.fromisoformat(start_date.split("T")[0] if "T" in start_date else start_date)
            start_date_obj = start_dt.date()
        else:
            start_date_obj = current_date
        
        # If start date is in the past, use tomorrow
        if start_date_obj < current_date:
            start_date_obj = current_date + timedelta(days=1)
            start_date = start_date_obj.strftime("%Y-%m-%d")
        # If start date is today, check if we're past business hours
        elif start_date_obj == current_date:
            # Business hours end at 4:30 PM (16:30)
            if current_time >= datetime.strptime("16:30", "%H:%M").time():
                # Past business hours, start from tomorrow
                start_date_obj = current_date + timedelta(days=1)
                start_date = start_date_obj.strftime("%Y-%m-%d")
                logger.info(f"⏰ Past business hours ({current_time}), starting availability from tomorrow: {start_date}")
        
        # Ensure end_date is at least 7 days from start_date
        if end_date:
            end_dt = datetime.fromisoformat(end_date.split("T")[0] if "T" in end_date else end_date)
            if end_dt.date() < start_date_obj:
                end_date = (start_date_obj + timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            end_date = (start_date_obj + timedelta(days=7)).strftime("%Y-%m-%d")
    except Exception as e:
        # If date parsing fails, use tomorrow
        logger.warning(f"Date parsing error: {e}, using tomorrow as start date")
        start_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = (current_date + timedelta(days=8)).strftime("%Y-%m-%d")
    
    # Get calendars
    calendars = await ghl.get_calendars()
    
    # Determine which calendar to use based on service type
    calendar_id = request.calendar_id
    if not calendar_id:
        # Map service types to calendar names/IDs
        # Updated to match new calendar names: Diagnostic, Proposal, Repair, Installation
        calendar_name_lower = ""
        if request.service_type in [ServiceType.REPAIR, ServiceType.MAINTENANCE]:
            # Find Diagnostic or Repair calendar
            for cal in calendars:
                calendar_name_lower = cal.get("name", "").lower()
                if any(keyword in calendar_name_lower for keyword in ["diagnostic", "service call", "repair", "service"]):
                    calendar_id = cal.get("id")
                    break
        elif request.service_type == ServiceType.ESTIMATE:
            # Find Proposal/Estimate calendar
            for cal in calendars:
                calendar_name_lower = cal.get("name", "").lower()
                if any(keyword in calendar_name_lower for keyword in ["proposal", "estimate", "sales"]):
                    calendar_id = cal.get("id")
                    break
        elif request.service_type == ServiceType.INSTALLATION:
            # Find Installation calendar
            for cal in calendars:
                calendar_name_lower = cal.get("name", "").lower()
                if "install" in calendar_name_lower:
                    calendar_id = cal.get("id")
                    break
        
        # Fallback to first calendar if not found
        if not calendar_id and calendars:
            calendar_id = calendars[0].get("id")
    
    if not calendar_id:
        return CheckCalendarAvailabilityResponse(
            slots=[],
            calendar_id=""
        )
    
    # Get availability
    # CRITICAL: get_calendar_availability() already excludes booked slots by:
    # 1. Fetching all appointments from GHL API via get_appointments_for_date_range()
    # 2. For each slot, calling check_slot_availability() which compares against appointments
    # 3. Only returning slots where is_available == True (no overlap with booked appointments)
    # Use the adjusted start_date and end_date (not the original request dates)
    availability = await ghl.get_calendar_availability(
        calendar_id=calendar_id,
        start_date=start_date,  # Use adjusted start_date
        end_date=end_date  # Use adjusted end_date
    )
    
    # Convert to our format
    # CRITICAL: Only return slots marked as available=True
    # The system filters out booked slots in get_calendar_availability() via check_slot_availability()
    # This ensures booked appointments are excluded based on GHL API data
    slots = []
    for slot in availability:
        # Double-check: Only include slots explicitly marked as available
        # get_calendar_availability() should only return available slots, but we verify here
        if slot.get("available", False):
            slots.append(CalendarSlot(
                start_time=slot.get("startTime", ""),
                end_time=slot.get("endTime", ""),
                available=True  # All slots here are confirmed available (booked ones already excluded by check_slot_availability)
            ))
        else:
            # Log if we see a slot marked as unavailable (shouldn't happen if logic is working)
            logger.warning(f"⚠️ Found unavailable slot in response: {slot.get('startTime')} - this should have been excluded by get_calendar_availability()")
    
    logger.info(f"✅ Filtered slots: {len(slots)} available slots (booked slots already excluded by get_calendar_availability)")
    
    # CRITICAL: Filter out past slots for TODAY only
    # For future dates, include all slots
    # This prevents the AI from hallucinating past slots as available
    from zoneinfo import ZoneInfo
    pacific_tz = ZoneInfo("America/Los_Angeles")
    
    filtered_slots = []
    logger.info(f"🔍 Filtering {len(slots)} slots. Current time: {current_date} {current_time}")
    for slot in slots:
        try:
            # Parse slot start time
            slot_start_str = slot.start_time
            if "T" in slot_start_str:
                # Handle ISO format with timezone
                if slot_start_str.endswith("Z"):
                    slot_start_str = slot_start_str.replace("Z", "+00:00")
                else:
                    # Check if timezone offset already exists (pattern: +/-HH:MM at end)
                    # Examples: "2025-12-01T08:00:00-08:00" or "2025-12-01T08:00:00+05:00"
                    has_timezone = False
                    if len(slot_start_str) >= 6:
                        last_6 = slot_start_str[-6:]
                        # Check if last 6 chars match timezone pattern: +/-HH:MM
                        if (last_6[0] in ['+', '-'] and 
                            last_6[1:3].isdigit() and 
                            last_6[3] == ':' and 
                            last_6[4:6].isdigit()):
                            has_timezone = True
                    
                    if not has_timezone:
                        # No timezone found - assume Pacific Time
                        slot_start_str = slot_start_str + "-08:00"
                
                slot_start_dt = datetime.fromisoformat(slot_start_str)
                # Normalize to Pacific Time
                if slot_start_dt.tzinfo:
                    slot_start_dt = slot_start_dt.astimezone(pacific_tz)
                else:
                    slot_start_dt = slot_start_dt.replace(tzinfo=pacific_tz)
                
                # Check if slot is today
                slot_date = slot_start_dt.date()
                slot_time = slot_start_dt.time()
                
                # If slot is today, only include if it's in the future
                if slot_date == current_date:
                    # Slot is today - only include if time is after current time
                    if slot_time > current_time:
                        filtered_slots.append(slot)
                        logger.debug(f"   ✅ INCLUDING today slot: {slot_time} (after current time {current_time})")
                    else:
                        logger.debug(f"   ⏭️ EXCLUDING past slot for today: {slot_time} <= {current_time}")
                        # DO NOT add to filtered_slots - this is a past slot
                elif slot_date > current_date:
                    # Slot is in the future - include it
                    filtered_slots.append(slot)
                    logger.debug(f"   ✅ Including future slot: {slot_date} {slot_time}")
                else:
                    # Slot is in the past (shouldn't happen, but log it)
                    logger.warning(f"   ⚠️ Found past slot: {slot_date} {slot_time} (current: {current_date})")
        except Exception as e:
            # If parsing fails, EXCLUDE the slot (safer than showing potentially wrong slots)
            logger.error(f"   ❌ ERROR parsing slot time {slot.start_time}: {e}, EXCLUDING slot")
            # DO NOT add to filtered_slots - exclude slots we can't parse
    
    slots = filtered_slots
    
    # Log summary for debugging
    total_slots_checked = len(availability)
    available_slots_count = len(slots)
    
    # Group slots by time of day for better presentation
    morning_slots = []
    afternoon_slots = []
    evening_slots = []
    
    for slot in slots:
        try:
            start_time = slot.start_time
            if "T" in start_time:
                time_part = start_time.split("T")[1].split("+")[0].split("-")[0]
                hour = int(time_part.split(":")[0])
                if hour < 12:
                    morning_slots.append(slot)
                elif hour < 16:
                    afternoon_slots.append(slot)
                else:
                    evening_slots.append(slot)
        except:
            pass
    
    logger.info(f"📅 Calendar availability: {available_slots_count} available slots out of {total_slots_checked} total slots checked")
    logger.info(f"   Morning (8-11 AM): {len(morning_slots)} slots, Afternoon (12-3 PM): {len(afternoon_slots)} slots, Evening (4-4:30 PM): {len(evening_slots)} slots")
    
    return CheckCalendarAvailabilityResponse(
        slots=slots,
        calendar_id=calendar_id
    )


