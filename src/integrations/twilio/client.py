from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException
from typing import Optional, Dict, Any
from src.config import settings
from src.utils.errors import TwilioAPIError
from src.utils.logging import logger


class TwilioService:
    def __init__(self):
        account_sid = settings.get_twilio_account_sid()
        auth_token = settings.twilio_auth_token
        
        if not account_sid or not auth_token:
            logger.warning("⚠️  Twilio credentials not configured")
            self.client = None
            self.phone_number = None
        else:
            self.client = TwilioClient(account_sid, auth_token)
            self.phone_number = settings.twilio_phone_number
            
            if not self.phone_number:
                logger.warning("⚠️  Twilio phone number not configured - SMS sending will fail")
    
    def send_sms(
        self, 
        to: str, 
        message: str,
        from_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send SMS message via Twilio"""
        if not self.client:
            raise TwilioAPIError(
                "Twilio client not initialized. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.",
                status_code=500
            )
        
        from_num = from_number or self.phone_number
        
        if not from_num:
            raise TwilioAPIError(
                "Twilio phone number not configured. Set TWILIO_PHONE_NUMBER environment variable.",
                status_code=500
            )
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=from_num,
                to=to
            )
            logger.info(f"✅ SMS sent to {to}, SID: {message_obj.sid}")
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status
            }
        except TwilioException as e:
            logger.error(f"❌ Twilio API error sending SMS to {to}: {str(e)}")
            raise TwilioAPIError(
                f"HTTP {e.code} error: {str(e)}",
                status_code=e.code or 400,
                details={"twilio_error": str(e), "to": to, "from": from_num}
            )
    
    def initiate_warm_transfer(
        self,
        call_sid: str,
        to: str,
        from_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate warm transfer to staff member"""
        from_num = from_number or self.phone_number
        call = self.client.calls(call_sid).update(
            twiml=f'<Response><Dial><Number>{to}</Number></Dial></Response>'
        )
        logger.info(f"Warm transfer initiated: {call_sid} -> {to}")
        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status
        }
    
    def get_call(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """Get call information"""
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                "sid": call.sid,
                "status": call.status,
                "from": call.from_,
                "to": call.to,
                "duration": call.duration,
                "start_time": call.start_time.isoformat() if call.start_time else None
            }
        except TwilioException as e:
            logger.error(f"Failed to get call {call_sid}: {str(e)}")
            return None


