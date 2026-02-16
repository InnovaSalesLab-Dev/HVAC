from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CallType(str, Enum):
    SERVICE_REPAIR = "service_repair"
    INSTALL_ESTIMATE = "install_estimate"
    MAINTENANCE = "maintenance"
    APPOINTMENT_CHANGE = "appointment_change"
    OTHER = "other"


class ServiceType(str, Enum):
    REPAIR = "repair"
    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    ESTIMATE = "estimate"


class UrgencyLevel(str, Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    STANDARD = "standard"
    LOW = "low"


# Vapi Function Request/Response Models
class ClassifyCallTypeRequest(BaseModel):
    transcript: str
    conversation_summary: Optional[str] = None


class ClassifyCallTypeResponse(BaseModel):
    call_type: CallType
    confidence: float
    reasoning: Optional[str] = None


class CheckCalendarAvailabilityRequest(BaseModel):
    service_type: ServiceType
    start_date: str
    end_date: str
    calendar_id: Optional[str] = None


class CalendarSlot(BaseModel):
    start_time: str
    end_time: str
    available: bool


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
    businessHoursToday: str


class CheckCalendarAvailabilityResponse(BaseModel):
    slots: List[CalendarSlot]
    calendar_id: str


class BookAppointmentRequest(BaseModel):
    contact_id: str
    calendar_id: str
    start_time: str
    end_time: str
    title: str
    service_type: ServiceType
    notes: Optional[str] = None
    urgency: Optional[UrgencyLevel] = None
    service_address: Optional[str] = None  # Service address for appointment location
    reschedule_appointment_id: Optional[str] = None  # If provided, cancel this appointment before booking new one


class BookAppointmentResponse(BaseModel):
    appointment_id: str
    success: bool
    message: str


class CancelAppointmentRequest(BaseModel):
    contact_id: str
    appointment_id: str


class CancelAppointmentResponse(BaseModel):
    success: bool
    message: str
    method: Optional[str] = None  # "api_delete", "api_update", "timeline_note", "failed", "error"


class CreateContactRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    sms_consent: bool = False
    custom_fields: Optional[Dict[str, Any]] = None


class CreateContactResponse(BaseModel):
    contact_id: str
    success: bool
    is_new: bool


class SendConfirmationRequest(BaseModel):
    contact_id: str
    appointment_id: Optional[str] = None
    message: Optional[str] = None
    method: str = "sms"  # sms or email
    phone: Optional[str] = None  # Override: send to this number instead of contact's number


class SendConfirmationResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    method: str


class InitiateWarmTransferRequest(BaseModel):
    call_sid: str
    staff_phone: str
    context: Optional[str] = None


class InitiateWarmTransferResponse(BaseModel):
    success: bool
    transfer_sid: Optional[str] = None
    message: str


class LogCallSummaryRequest(BaseModel):
    contact_id: str
    transcript: str
    summary: str
    call_duration: Optional[int] = None
    call_type: Optional[CallType] = None
    outcome: Optional[str] = None


class LogCallSummaryResponse(BaseModel):
    success: bool
    note_id: Optional[str] = None


# GHL Webhook Models
class GHLWebhookEvent(BaseModel):
    type: str
    locationId: str
    contactId: Optional[str] = None
    data: Dict[str, Any]


