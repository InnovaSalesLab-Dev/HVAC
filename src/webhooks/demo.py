from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
from src.integrations.vapi import VapiClient
from src.integrations.twilio import TwilioService
from src.config import settings
from src.utils.logging import logger
from src.utils.validation import validate_phone_number
from src.utils.errors import VapiAPIError

router = APIRouter()

class DemoCallRequest(BaseModel):
    phone: str
    name: Optional[str] = None
    demo_type: Optional[str] = None # Added for smart routing
    # Allow other fields but ignore them
    class Config:
        extra = "ignore"

@router.post("/demo/handle")
async def handle_demo(request: DemoCallRequest):
    """Smart router: Handles both inbound and outbound based on demo_type"""
    # Log full request for debugging
    logger.info(f"🔀 Smart Router Request: {request.model_dump()}")
    
    # Normalize demo_type
    dtype = (request.demo_type or "").lower().strip()
    
    # Route to Inbound if demo_type contains "inbound", otherwise default to Outbound
    if "inbound" in dtype:
        logger.info(f"👈 Routing to Inbound Logic (Matched: '{dtype}')")
        return await inbound_demo(request)
    else:
        # Default to Outbound
        logger.info(f"👉 Routing to Outbound Logic (Default, received: '{dtype}')")
        return await outbound_demo(request)

@router.post("/demo/outbound")
async def outbound_demo(request: DemoCallRequest):
    """Trigger a simple outbound call for demo purposes"""
    logger.info(f"🚀 Demo Outbound Call requested for {request.phone}")
    
    try:
        phone_clean = validate_phone_number(request.phone)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid phone number: {str(e)}")
        
    vapi = VapiClient()
    
    # Use configured outbound assistant or default
    assistant_id = settings.vapi_outbound_assistant_id or "d6c74f74-de2a-420d-ae59-aab8fa7cbabe"
    
    # Get phone number ID
    phone_number_id = settings.vapi_phone_number_id
    
    # If no phone number ID configured, try to get from assistant
    if not phone_number_id:
        logger.warning("⚠️  No phoneNumberId in settings, trying to get from assistant...")
        try:
            assistant = await vapi.get_assistant(assistant_id)
            phone_number_id = assistant.get("phoneNumberId") or assistant.get("phoneNumber")
            if phone_number_id:
                logger.info(f"✅ Found phone number ID from assistant: {phone_number_id}")
            else:
                logger.error("❌ No phone number found in assistant configuration")
        except Exception as e:
            logger.error(f"❌ Could not fetch assistant details: {e}")
    
    # Validate required fields before making the call
    if not phone_number_id:
        error_msg = "Phone number ID is required. Please set VAPI_PHONE_NUMBER_ID in your .env file or configure it in your Vapi assistant settings."
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    if not assistant_id:
        error_msg = "Assistant ID is required. Please set VAPI_OUTBOUND_ASSISTANT_ID in your .env file."
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Create call configuration
        call_config = {
            "assistantId": assistant_id,
            "customer": {
                "number": phone_clean,
                "name": request.name or "Valued Customer"
            },
            "phoneNumberId": phone_number_id
        }
        
        # Log the configuration (without exposing sensitive data)
        logger.info(f"📞 Call config - Assistant: {assistant_id[:8]}..., Phone ID: {phone_number_id[:8] if phone_number_id else 'None'}..., Customer: {phone_clean}")
        
        result = await vapi.create_call(call_config)
        logger.info(f"✅ Demo call initiated: {result.get('id')}")
        return {"status": "success", "call_id": result.get("id")}
        
    except VapiAPIError as e:
        # Extract detailed error information from Vapi API error
        error_detail = e.message
        if e.details and 'response' in e.details:
            error_detail = f"{error_detail} - {e.details.get('response', '')}"
        logger.error(f"❌ Demo call failed: {error_detail}")
        raise HTTPException(status_code=e.status_code, detail=error_detail)
    except Exception as e:
        # Handle other exceptions
        error_detail = str(e)
        logger.error(f"❌ Demo call failed: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@router.post("/demo/inbound")
async def inbound_demo(request: DemoCallRequest):
    """Trigger an inbound call simulation (AI calls user)"""
    logger.info(f"🚀 Demo Inbound Call requested for {request.phone}")
    
    try:
        phone_clean = validate_phone_number(request.phone)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid phone number: {str(e)}")
        
    vapi = VapiClient()
    
    # Use configured inbound assistant or specific ID provided by user
    assistant_id = settings.vapi_inbound_assistant_id or "d61d0517-4a65-496e-b97f-d3ad220f684e"
    
    # Get phone number ID
    phone_number_id = settings.vapi_phone_number_id
    
    # If no phone number ID configured, try to get from assistant
    if not phone_number_id:
        logger.warning("⚠️  No phoneNumberId in settings, trying to get from assistant...")
        try:
            assistant = await vapi.get_assistant(assistant_id)
            phone_number_id = assistant.get("phoneNumberId") or assistant.get("phoneNumber")
            if phone_number_id:
                logger.info(f"✅ Found phone number ID from assistant: {phone_number_id}")
            else:
                logger.error("❌ No phone number found in assistant configuration")
        except Exception as e:
            logger.error(f"❌ Could not fetch assistant details: {e}")
    
    # Validate required fields before making the call
    if not phone_number_id:
        error_msg = "Phone number ID is required. Please set VAPI_PHONE_NUMBER_ID in your .env file or configure it in your Vapi assistant settings."
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    if not assistant_id:
        error_msg = "Assistant ID is required. Please set VAPI_INBOUND_ASSISTANT_ID in your .env file."
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Create call configuration
        call_config = {
            "assistantId": assistant_id,
            "customer": {
                "number": phone_clean,
                "name": request.name or "Valued Customer"
            },
            "phoneNumberId": phone_number_id
        }
        
        # Log the configuration (without exposing sensitive data)
        logger.info(f"📞 Call config - Assistant: {assistant_id[:8]}..., Phone ID: {phone_number_id[:8] if phone_number_id else 'None'}..., Customer: {phone_clean}")
        
        result = await vapi.create_call(call_config)
        logger.info(f"✅ Demo inbound call initiated: {result.get('id')}")
        return {"status": "success", "call_id": result.get("id")}
        
    except VapiAPIError as e:
        # Extract detailed error information from Vapi API error
        error_detail = e.message
        if e.details and 'response' in e.details:
            error_detail = f"{error_detail} - {e.details.get('response', '')}"
        logger.error(f"❌ Demo inbound call failed: {error_detail}")
        raise HTTPException(status_code=e.status_code, detail=error_detail)
    except Exception as e:
        # Handle other exceptions
        error_detail = str(e)
        logger.error(f"❌ Demo inbound call failed: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)