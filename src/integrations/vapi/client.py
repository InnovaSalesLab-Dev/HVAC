import httpx
from typing import Dict, Any, Optional, List
from src.config import settings
from src.utils.errors import VapiAPIError
from src.utils.logging import logger


class VapiClient:
    def __init__(self):
        self.api_key = settings.vapi_api_key
        if not self.api_key:
            logger.error("⚠️  VAPI_API_KEY not configured in environment variables")
            raise VapiAPIError(
                "Vapi API key not configured. Please set VAPI_API_KEY in Fly.io secrets.",
                status_code=500
            )
        
        # Log first 8 chars of key for debugging (without exposing full key)
        key_preview = self.api_key[:8] + "..." if len(self.api_key) > 8 else self.api_key
        logger.info(f"🔑 Using Vapi API key: {key_preview} (length: {len(self.api_key)})")
        
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Vapi API error: {e.response.status_code} - {error_text}")
            
            # Provide helpful error message for 401 (invalid API key)
            if e.response.status_code == 401:
                logger.error("⚠️  Vapi API key is invalid or missing.")
                logger.error("   For server-side API calls (creating outbound calls), you need a PRIVATE API key.")
                logger.error("   Steps to fix:")
                logger.error("   1. Go to https://dashboard.vapi.ai")
                logger.error("   2. Navigate to Settings → API Keys")
                logger.error("   3. Find your PRIVATE API key (not public)")
                logger.error("   4. Copy the full key")
                logger.error("   5. Run: flyctl secrets set VAPI_API_KEY=your_private_key -a scott-valley-hvac-api")
                raise VapiAPIError(
                    "Vapi API key is invalid. For server-side calls, use your PRIVATE API key from Vapi dashboard. See logs for instructions.",
                    status_code=401,
                    details={"response": error_text}
                )
            
            raise VapiAPIError(
                f"Vapi API request failed: {e.response.status_code}",
                status_code=e.response.status_code,
                details={"response": error_text}
            )
        except httpx.RequestError as e:
            logger.error(f"Vapi API request error: {str(e)}")
            raise VapiAPIError(
                f"Vapi API request failed: {str(e)}",
                status_code=500
            )
    
    async def create_assistant(self, assistant_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create Vapi assistant"""
        return await self._request("POST", "assistant", data=assistant_config)
    
    async def get_assistant(self, assistant_id: str) -> Dict[str, Any]:
        """Get assistant details"""
        return await self._request("GET", f"assistant/{assistant_id}")
    
    async def update_assistant(self, assistant_id: str, assistant_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update assistant configuration"""
        return await self._request("PATCH", f"assistant/{assistant_id}", data=assistant_config)
    
    async def create_phone_number(self, phone_number_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create phone number in Vapi"""
        return await self._request("POST", "phone-number", data=phone_number_config)
    
    async def create_call(self, call_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create outbound call"""
        return await self._request("POST", "call", data=call_config)
    
    async def get_call(self, call_id: str) -> Dict[str, Any]:
        """Get call details"""
        return await self._request("GET", f"call/{call_id}")
    
    async def create_tool(self, tool_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a tool in the Tools section"""
        return await self._request("POST", "tool", data=tool_config)
    
    async def get_tool(self, tool_id: str) -> Dict[str, Any]:
        """Get tool details"""
        return await self._request("GET", f"tool/{tool_id}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools"""
        return await self._request("GET", "tool")
    
    async def update_tool(self, tool_id: str, tool_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update tool configuration"""
        return await self._request("PATCH", f"tool/{tool_id}", data=tool_config)
    
    async def delete_tool(self, tool_id: str) -> Dict[str, Any]:
        """Delete a tool"""
        return await self._request("DELETE", f"tool/{tool_id}")
    
    async def list_calls(
        self,
        limit: int = 50,
        status: Optional[str] = None,
        assistant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List calls with optional filters"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        if assistant_id:
            params["assistantId"] = assistant_id
        return await self._request("GET", "call", params=params)
    
    async def get_call_transcript(self, call_id: str) -> Dict[str, Any]:
        """Get call transcript"""
        return await self._request("GET", f"call/{call_id}/transcript")
    
    async def get_call_recording(self, call_id: str) -> Dict[str, Any]:
        """Get call recording URL"""
        return await self._request("GET", f"call/{call_id}/recording")
    
    async def create_conversation(
        self,
        assistant_id: str,
        customer: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a conversation (for testing)"""
        data = {"assistantId": assistant_id}
        if customer:
            data["customer"] = customer
        return await self._request("POST", "conversation", data=data)
    
    async def send_message(
        self,
        conversation_id: str,
        message: str,
        role: str = "user"
    ) -> Dict[str, Any]:
        """Send a message in a conversation"""
        return await self._request(
            "POST",
            f"conversation/{conversation_id}/message",
            data={"message": message, "role": role}
        )
    
    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation details"""
        return await self._request("GET", f"conversation/{conversation_id}")
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        return await self._request("GET", f"conversation/{conversation_id}/messages")


