from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Vapi.ai
    vapi_api_key: Optional[str] = None
    vapi_inbound_assistant_id: Optional[str] = None
    vapi_outbound_assistant_id: Optional[str] = None
    vapi_phone_number_id: Optional[str] = None
    
    # GoHighLevel (supports both GHL_API_KEY and GHL_API)
    ghl_api_key: str = ""
    ghl_api: str = ""  # Alternative name - preferred
    ghl_location_id: str = ""
    ghl_base_url: str = "https://services.leadconnectorhq.com"
    
    def get_ghl_api_key(self) -> str:
        """Get GHL API key from either ghl_api_key or ghl_api"""
        return self.ghl_api or self.ghl_api_key
    
    # Twilio (supports both twilio_sid and twilio_account_sid)
    twilio_account_sid: Optional[str] = None
    twilio_sid: Optional[str] = None  # Alternative name
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    def get_twilio_account_sid(self) -> Optional[str]:
        """Get Twilio account SID from either twilio_account_sid or twilio_sid"""
        return self.twilio_account_sid or self.twilio_sid
    
    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    environment: str = "development"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override port from environment if PORT is set (for Fly.io)
        import os
        if os.getenv("PORT"):
            self.port = int(os.getenv("PORT"))
    
    # Webhooks
    webhook_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    ghl_appointment_webhook_url: Optional[str] = None
    ghl_custom_fields_webhook_url: Optional[str] = None  # For custom fields automation
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )


settings = Settings()
