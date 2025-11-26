"""
Check business hours function for Vapi assistants.
Returns current date, time, and business hours status.
"""
from pydantic import BaseModel
from src.utils.business_hours import check_business_hours, get_current_date_pacific, get_current_datetime_pacific
from typing import Optional


class CheckBusinessHoursRequest(BaseModel):
    """Request model - no parameters needed, uses current time"""
    pass


class CheckBusinessHoursResponse(BaseModel):
    """Response with business hours status and current date/time"""
    isBusinessHours: bool
    message: str
    day: str
    timezone: str
    currentTime: str
    currentDate: str
    currentYear: str
    businessHoursToday: str


async def check_business_hours_function(request: Optional[CheckBusinessHoursRequest] = None) -> CheckBusinessHoursResponse:
    """
    Check if current time is within business hours.
    Returns current date, time, and business hours status.
    
    This should be called BEFORE checking calendar availability to ensure
    we're only booking appointments during business hours and on valid dates.
    """
    result = check_business_hours()
    
    return CheckBusinessHoursResponse(
        isBusinessHours=result["isBusinessHours"],
        message=result["message"],
        day=result["day"],
        timezone=result["timezone"],
        currentTime=result["currentTime"],
        currentDate=result["currentDate"],
        currentYear=result["currentYear"],
        businessHoursToday=result["businessHoursToday"]
    )

