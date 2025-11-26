from fastapi import FastAPI, HTTPException, Request
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.utils.logging import setup_logging, logger
from src.utils.errors import handle_api_error, APIError
from src.models import (
    ClassifyCallTypeRequest,
    ClassifyCallTypeResponse,
    CheckCalendarAvailabilityRequest,
    CheckCalendarAvailabilityResponse,
    BookAppointmentRequest,
    BookAppointmentResponse,
    CancelAppointmentRequest,
    CancelAppointmentResponse,
    CreateContactRequest,
    CreateContactResponse,
    SendConfirmationRequest,
    SendConfirmationResponse,
    InitiateWarmTransferRequest,
    InitiateWarmTransferResponse,
    LogCallSummaryRequest,
    LogCallSummaryResponse,
    CheckBusinessHoursRequest,
    CheckBusinessHoursResponse,
)
from src.functions import (
    classify_call_type,
    check_calendar_availability,
    book_appointment,
    cancel_appointment,
    create_contact,
    send_confirmation,
    initiate_warm_transfer,
    log_call_summary,
)
from src.functions.check_business_hours import check_business_hours_function
from src.webhooks import router as webhook_router
from src.monitoring import router as monitoring_router
from src.config import settings

# Setup logging
setup_logging()

app = FastAPI(
    title="Scott Valley HVAC Voice Agent API",
    description="API for Vapi.ai voice agent functions and webhooks",
    version="1.0.0"
)


# Global exception handler
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.environment == "development" else "An error occurred"
        }
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include webhook routes
app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])

# Include monitoring routes
app.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Scott Valley HVAC Voice Agent API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Vapi Function Endpoints
@app.post("/functions/classify-call-type", response_model=ClassifyCallTypeResponse)
async def classify_call_type_endpoint(request: ClassifyCallTypeRequest):
    """Classify call type from conversation transcript"""
    return await classify_call_type(request)


@app.post("/functions/check-business-hours", response_model=CheckBusinessHoursResponse)
async def check_business_hours_endpoint(request: Optional[CheckBusinessHoursRequest] = None):
    """Check current business hours status and get current date/time"""
    return await check_business_hours_function(request)


@app.post("/functions/check-calendar-availability", response_model=CheckCalendarAvailabilityResponse)
async def check_calendar_availability_endpoint(request: CheckCalendarAvailabilityRequest):
    """Check available appointment slots"""
    return await check_calendar_availability(request)


@app.post("/functions/book-appointment", response_model=BookAppointmentResponse)
async def book_appointment_endpoint(request: BookAppointmentRequest):
    """Book appointment in GHL calendar"""
    return await book_appointment(request)


@app.post("/functions/cancel-appointment", response_model=CancelAppointmentResponse)
async def cancel_appointment_endpoint(request: CancelAppointmentRequest):
    """Cancel an existing appointment in GHL"""
    return await cancel_appointment(request)


@app.post("/functions/create-contact", response_model=CreateContactResponse)
async def create_contact_endpoint(request: CreateContactRequest):
    """Create or update contact in GHL"""
    return await create_contact(request)


@app.post("/functions/send-confirmation", response_model=SendConfirmationResponse)
async def send_confirmation_endpoint(request: SendConfirmationRequest):
    """Send SMS or email confirmation"""
    return await send_confirmation(request)


@app.post("/functions/initiate-warm-transfer", response_model=InitiateWarmTransferResponse)
async def initiate_warm_transfer_endpoint(request: InitiateWarmTransferRequest):
    """Transfer call to human staff member"""
    return await initiate_warm_transfer(request)


@app.post("/functions/log-call-summary", response_model=LogCallSummaryResponse)
async def log_call_summary_endpoint(request: LogCallSummaryRequest):
    """Save call transcript and summary to GHL"""
    return await log_call_summary(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )


