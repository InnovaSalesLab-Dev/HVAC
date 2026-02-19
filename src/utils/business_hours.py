"""
Business hours utility for Valley View HVAC.
Returns technician dispatch hours (8:00 AM - 4:30 PM, Monday-Friday, Pacific Time)
and always clarifies that phone/call answering is available twenty-four seven.
"""
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, Set, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _load_zone(key: str) -> ZoneInfo:
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            f"Time zone data for '{key}' not found. Install the 'tzdata' package."
        ) from exc


PACIFIC_TZ = _load_zone("America/Los_Angeles")
UTC_TZ = _load_zone("UTC")


@dataclass(frozen=True)
class OfficeHours:
    start: time
    end: time
    
    def contains(self, dt: datetime) -> bool:
        """Check if datetime falls within these hours"""
        local_time = dt.time()
        return self.start <= local_time <= self.end


# Scott Valley HVAC Business Hours: 8:00 AM - 4:30 PM, Monday-Friday
# Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
WEEKDAY_HOURS: Dict[int, OfficeHours] = {
    0: OfficeHours(start=time(hour=8, minute=0), end=time(hour=16, minute=30)),  # Monday
    1: OfficeHours(start=time(hour=8, minute=0), end=time(hour=16, minute=30)),  # Tuesday
    2: OfficeHours(start=time(hour=8, minute=0), end=time(hour=16, minute=30)),  # Wednesday
    3: OfficeHours(start=time(hour=8, minute=0), end=time(hour=16, minute=30)),  # Thursday
    4: OfficeHours(start=time(hour=8, minute=0), end=time(hour=16, minute=30)),  # Friday
}

# Holidays when business is closed
HOLIDAYS: Set[str] = {
    # Format: YYYY-MM-DD
    "2025-01-01",  # New Year's Day
    "2025-07-04",  # Independence Day
    "2025-12-25",  # Christmas Day
    "2026-01-01",  # New Year's Day
    "2026-07-04",  # Independence Day
    "2026-12-25",  # Christmas Day
}


def get_current_time_pacific() -> datetime:
    """Return aware datetime in Pacific Time (Salem, OR timezone)."""
    return datetime.now(tz=UTC_TZ).astimezone(PACIFIC_TZ)


def _ensure_pacific(reference_time: datetime) -> datetime:
    """Normalize a datetime to Pacific Time."""
    if reference_time.tzinfo is None:
        # Assume reference time is already Pacific if naive
        return reference_time.replace(tzinfo=PACIFIC_TZ)
    return reference_time.astimezone(PACIFIC_TZ)


def check_business_hours(reference_time: Optional[datetime] = None) -> Dict[str, any]:
    """
    Determine if a given time falls within business hours.
    
    Args:
        reference_time: Optional datetime to check. Defaults to current Pacific time.
    
    Returns:
        dict containing:
            - isBusinessHours (bool): Whether it's currently business hours
            - message (str): Human-readable message about business status
            - day (str): Day of week name
            - timezone (str): Timezone used
            - currentTime (str): Current time in Pacific Time
            - currentDate (str): Current date (YYYY-MM-DD)
            - businessHoursToday (str): Business hours for today
    """
    current_time = _ensure_pacific(reference_time) if reference_time else get_current_time_pacific()
    day_of_week = current_time.weekday()  # Monday=0, Sunday=6
    current_date_str = current_time.strftime("%Y-%m-%d")
    current_time_str = current_time.strftime("%I:%M %p").lstrip("0")
    
    # Check if it's a holiday
    if current_date_str in HOLIDAYS:
        return {
            "isBusinessHours": False,
            "message": "Our technicians are off today for a holiday, but our team answers calls twenty-four seven. Technician dispatch resumes next business day at 8 AM Pacific.",
            "day": current_time.strftime("%A"),
            "timezone": "America/Los_Angeles",
            "currentTime": current_time_str,
            "currentDate": current_date_str,
            "currentYear": str(current_time.year),
            "businessHoursToday": "Technician dispatch closed (Holiday). Calls answered 24/7.",
        }
    
    # Check if it's a weekday
    if day_of_week not in WEEKDAY_HOURS:
        return {
            "isBusinessHours": False,
            "message": "Technicians are off on weekends, but our team answers calls twenty-four seven. Technician dispatch resumes Monday at 8 AM Pacific. Emergency service may be available case-by-case.",
            "day": current_time.strftime("%A"),
            "timezone": "America/Los_Angeles",
            "currentTime": current_time_str,
            "currentDate": current_date_str,
            "currentYear": str(current_time.year),
            "businessHoursToday": "Technician dispatch closed (Weekend). Calls answered 24/7.",
        }
    
    office_hours = WEEKDAY_HOURS[day_of_week]
    
    if office_hours.contains(current_time):
        end_display = office_hours.end.strftime("%I:%M %p").lstrip("0")
        start_display = office_hours.start.strftime("%I:%M %p").lstrip("0")
        return {
            "isBusinessHours": True,
            "message": f"Technicians are available now until {end_display} Pacific Time. Our team answers calls twenty-four seven.",
            "day": current_time.strftime("%A"),
            "timezone": "America/Los_Angeles",
            "currentTime": current_time_str,
            "currentDate": current_date_str,
            "currentYear": str(current_time.year),
            "businessHoursToday": f"Technician dispatch {start_display} - {end_display}. Calls answered 24/7.",
        }
    
    # Outside technician dispatch hours
    start_display = office_hours.start.strftime("%I:%M %p").lstrip("0")
    end_display = office_hours.end.strftime("%I:%M %p").lstrip("0")
    
    # Determine next technician dispatch window
    if current_time.time() < office_hours.start:
        next_dispatch = f"today at {start_display}"
    else:
        if day_of_week == 4:  # Friday
            next_dispatch = "Monday at 8:00 AM"
        else:
            next_dispatch = f"tomorrow at {start_display}"
    
    return {
        "isBusinessHours": False,
        "message": f"Technician dispatch is currently closed (hours: {start_display} to {end_display} Pacific). Next dispatch window: {next_dispatch}. Our team answers calls twenty-four seven — you can always reach us.",
        "day": current_time.strftime("%A"),
        "timezone": "America/Los_Angeles",
        "currentTime": current_time_str,
        "currentDate": current_date_str,
        "currentYear": str(current_time.year),
        "businessHoursToday": f"Technician dispatch {start_display} - {end_display}. Calls answered 24/7.",
    }


def get_current_date_pacific() -> str:
    """Get current date in Pacific Time (YYYY-MM-DD format)."""
    return get_current_time_pacific().strftime("%Y-%m-%d")


def get_current_datetime_pacific() -> datetime:
    """Get current datetime in Pacific Time."""
    return get_current_time_pacific()

