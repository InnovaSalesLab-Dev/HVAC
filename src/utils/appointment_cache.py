"""
In-memory appointment cache to track booked appointments without database.
This cache is populated from:
1. Appointments we create via book_appointment
2. GHL webhooks for appointment.created events
"""
from typing import Dict, Set, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from src.utils.logging import logger

# In-memory cache: {calendar_id: {date_str: Set[time_slots]}}
# Example: {"calendar123": {"2025-11-25": {"09:00", "10:00"}}}
_appointment_cache: Dict[str, Dict[str, Set[str]]] = {}


def add_appointment_to_cache(
    calendar_id: str,
    start_time: str,
    end_time: Optional[str] = None
):
    """
    Add an appointment to the in-memory cache.
    
    Args:
        calendar_id: GHL calendar ID
        start_time: ISO format datetime string (e.g., "2025-11-25T09:00:00-08:00")
        end_time: Optional end time (defaults to 1 hour after start)
    """
    try:
        # Parse start time
        if isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        else:
            start_dt = start_time
        
        # Convert to Pacific Time
        pacific_tz = ZoneInfo("America/Los_Angeles")
        if start_dt.tzinfo:
            start_dt = start_dt.astimezone(pacific_tz)
        else:
            start_dt = start_dt.replace(tzinfo=pacific_tz)
        
        # Get date string (YYYY-MM-DD)
        date_str = start_dt.strftime("%Y-%m-%d")
        
        # Get time slot (HH:MM format)
        time_slot = start_dt.strftime("%H:%M")
        
        # Initialize cache structure if needed
        if calendar_id not in _appointment_cache:
            _appointment_cache[calendar_id] = {}
        if date_str not in _appointment_cache[calendar_id]:
            _appointment_cache[calendar_id][date_str] = set()
        
        # Add time slot to cache
        _appointment_cache[calendar_id][date_str].add(time_slot)
        logger.info(f"✅ Added appointment to cache: {calendar_id} on {date_str} at {time_slot}")
        
        # If end_time provided, add all hourly slots in the range
        if end_time:
            if isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            else:
                end_dt = end_time
            
            if end_dt.tzinfo:
                end_dt = end_dt.astimezone(pacific_tz)
            else:
                end_dt = end_dt.replace(tzinfo=pacific_tz)
            
            # Add all hourly slots between start and end
            current = start_dt
            while current < end_dt:
                time_slot = current.strftime("%H:%M")
                _appointment_cache[calendar_id][date_str].add(time_slot)
                current = current.replace(hour=current.hour + 1) if current.hour < 23 else current.replace(day=current.day + 1, hour=0)
        
    except Exception as e:
        logger.warning(f"⚠️ Error adding appointment to cache: {e}")


def remove_appointment_from_cache(
    calendar_id: str,
    start_time: str
):
    """
    Remove an appointment from the cache (e.g., when cancelled).
    
    Args:
        calendar_id: GHL calendar ID
        start_time: ISO format datetime string
    """
    try:
        # Parse start time
        if isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        else:
            start_dt = start_time
        
        # Convert to Pacific Time
        pacific_tz = ZoneInfo("America/Los_Angeles")
        if start_dt.tzinfo:
            start_dt = start_dt.astimezone(pacific_tz)
        else:
            start_dt = start_dt.replace(tzinfo=pacific_tz)
        
        date_str = start_dt.strftime("%Y-%m-%d")
        time_slot = start_dt.strftime("%H:%M")
        
        if calendar_id in _appointment_cache and date_str in _appointment_cache[calendar_id]:
            _appointment_cache[calendar_id][date_str].discard(time_slot)
            logger.info(f"✅ Removed appointment from cache: {calendar_id} on {date_str} at {time_slot}")
    except Exception as e:
        logger.warning(f"⚠️ Error removing appointment from cache: {e}")


def is_slot_booked_in_cache(
    calendar_id: str,
    slot_start: datetime
) -> bool:
    """
    Check if a time slot is booked in the cache.
    
    Args:
        calendar_id: GHL calendar ID
        slot_start: datetime object for the slot start time
    
    Returns:
        True if slot is booked, False if available
    """
    try:
        # Convert to Pacific Time
        pacific_tz = ZoneInfo("America/Los_Angeles")
        if slot_start.tzinfo:
            slot_start_pacific = slot_start.astimezone(pacific_tz)
        else:
            slot_start_pacific = slot_start.replace(tzinfo=pacific_tz)
        
        date_str = slot_start_pacific.strftime("%Y-%m-%d")
        time_slot = slot_start_pacific.strftime("%H:%M")
        
        # Check cache
        if calendar_id in _appointment_cache:
            if date_str in _appointment_cache[calendar_id]:
                is_booked = time_slot in _appointment_cache[calendar_id][date_str]
                if is_booked:
                    logger.debug(f"📋 Slot {time_slot} on {date_str} is BOOKED in cache")
                return is_booked
        
        return False  # Not in cache = not booked (or we don't know)
    except Exception as e:
        logger.warning(f"⚠️ Error checking cache: {e}")
        return False


def get_cache_stats() -> Dict[str, any]:
    """Get statistics about the cache for debugging."""
    total_appointments = sum(
        len(slots) for calendar in _appointment_cache.values()
        for slots in calendar.values()
    )
    return {
        "calendars": len(_appointment_cache),
        "total_appointments": total_appointments,
        "cache": _appointment_cache
    }

