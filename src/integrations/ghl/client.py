import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from src.config import settings
from src.utils.errors import GHLAPIError
from src.utils.logging import logger
import json


class GHLClient:
    def __init__(self):
        self.api_key = settings.get_ghl_api_key()
        self.location_id = settings.ghl_location_id
        self.base_url = settings.ghl_base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
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
            try:
                error_json = e.response.json()
                logger.error(f"GHL API error: {e.response.status_code} - {error_json}")
            except:
                logger.error(f"GHL API error: {e.response.status_code} - {error_text}")
            raise GHLAPIError(
                f"GHL API request failed: {e.response.status_code}",
                status_code=e.response.status_code,
                details={"response": error_text, "url": url, "method": method}
            )
        except httpx.RequestError as e:
            logger.error(f"GHL API request error: {str(e)}")
            raise GHLAPIError(
                f"GHL API request failed: {str(e)}",
                status_code=500
            )
    
    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update contact in GHL"""
        endpoint = f"contacts/"
        payload = {
            "locationId": self.location_id,
            **contact_data
        }
        result = await self._request("POST", endpoint, data=payload)
        # Log response structure for debugging
        logger.debug(f"GHL create_contact response: {result}")
        return result
    
    async def get_contact(self, contact_id: Optional[str] = None, phone: Optional[str] = None, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get contact by ID, phone, or email"""
        if contact_id:
            endpoint = f"contacts/{contact_id}"
            params = {"locationId": self.location_id}
            try:
                return await self._request("GET", endpoint, params=params)
            except GHLAPIError as e:
                logger.error(f"Failed to get contact {contact_id}: {str(e)}")
                return None
        
        if phone or email:
            # GHL API: Search contacts using POST /contacts/search
            # Correct format: query must be a STRING (not object), use pageLimit (not limit)
            endpoint = "contacts/search"
            payload = {
                "locationId": self.location_id,
                "pageLimit": 10
            }
            # Build query string (must be <= 75 characters)
            query_parts = []
            if phone:
                # Clean phone number for search
                phone_clean = phone.replace("+", "").replace("-", "").replace(" ", "")
                query_parts.append(f"phone:{phone_clean}")
            if email:
                query_parts.append(f"email:{email.lower()}")
            
            if query_parts:
                query_string = " ".join(query_parts)
                # Ensure query doesn't exceed 75 characters
                if len(query_string) > 75:
                    # Use only the first query part if too long
                    query_string = query_parts[0][:75]
                payload["query"] = query_string
            
            try:
                result = await self._request("POST", endpoint, data=payload)
                # GHL returns contacts in different formats - handle both
                if isinstance(result, list):
                    contacts = result
                elif isinstance(result, dict):
                    contacts = result.get("contacts", []) or result.get("data", [])
                else:
                    contacts = []
                # Filter for exact match using normalized phone comparison
                if contacts:
                    from src.utils.phone_normalize import phones_match
                    
                    for contact in contacts:
                        if phone:
                            contact_phone = contact.get("phone", "")
                            # Use normalized comparison to handle formatting differences
                            if phones_match(phone, contact_phone):
                                logger.info(f"✅ Found existing contact by phone: {contact.get('id')} ({contact.get('firstName', '')} {contact.get('lastName', '')})")
                                return contact
                        if email:
                            contact_email = str(contact.get("email", "")).lower()
                            if contact_email == email.lower():
                                logger.info(f"✅ Found existing contact by email: {contact.get('id')} ({contact.get('firstName', '')} {contact.get('lastName', '')})")
                                return contact
                    
                    # If no exact match but contacts returned, log for debugging
                    if phone:
                        logger.debug(f"⚠️ Phone search returned {len(contacts)} contacts but none matched exactly")
                        logger.debug(f"   Searching for: {phone}")
                        for contact in contacts[:3]:  # Log first 3 for debugging
                            logger.debug(f"   Found: {contact.get('phone', 'N/A')} ({contact.get('firstName', '')} {contact.get('lastName', '')})")
                    
                    # Don't return first contact if no exact match - this prevents wrong contact updates
                    return None
                return None
            except GHLAPIError as e:
                # If search fails, return None and let create handle duplicate
                logger.warning(f"Contact search failed: {str(e)}")
                return None
        
        return None
    
    async def search_contacts_by_phone(self, phone: str) -> List[Dict[str, Any]]:
        """
        Search for ALL contacts with the given phone number.
        Returns a list of all matching contacts (not just the first one).
        Used for deduplication across multiple contacts with the same phone.
        """
        if not phone:
            return []
        
        endpoint = "contacts/search"
        payload = {
            "locationId": self.location_id,
            "pageLimit": 100  # Get more results to find all matches
        }
        
        # Clean phone number for search
        phone_clean = phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        query_string = f"phone:{phone_clean}"
        
        # Ensure query doesn't exceed 75 characters
        if len(query_string) > 75:
            query_string = query_string[:75]
        
        payload["query"] = query_string
        
        try:
            result = await self._request("POST", endpoint, data=payload)
            # GHL returns contacts in different formats - handle both
            if isinstance(result, list):
                contacts = result
            elif isinstance(result, dict):
                contacts = result.get("contacts", []) or result.get("data", [])
            else:
                contacts = []
            
            # Filter for exact match using normalized phone comparison
            from src.utils.phone_normalize import phones_match
            matching_contacts = []
            
            for contact in contacts:
                contact_phone = contact.get("phone", "")
                if phones_match(phone, contact_phone):
                    matching_contacts.append(contact)
            
            if matching_contacts:
                logger.info(f"📱 Found {len(matching_contacts)} contact(s) with phone {phone}")
            
            return matching_contacts
        except GHLAPIError as e:
            logger.warning(f"Contact search by phone failed: {str(e)}")
            return []
    
    async def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing contact"""
        if not contact_id:
            raise ValueError("contact_id is required for update")
        endpoint = f"contacts/{contact_id}"
        params = {"locationId": self.location_id}
        payload = {
            **contact_data
        }
        return await self._request("PUT", endpoint, data=payload, params=params)
    
    async def add_tags_to_contact(self, contact_id: str, tags: List[str]) -> Dict[str, Any]:
        """
        Add tags to a contact in GHL.
        Tags are added to the existing tags (not replaced).
        
        Args:
            contact_id: The contact ID
            tags: List of tag names to add
        
        Returns:
            Updated contact data
        """
        if not tags:
            return {}
        
        # First, get the contact to see existing tags
        contact = await self.get_contact(contact_id=contact_id)
        if not contact:
            logger.warning(f"Contact {contact_id} not found, cannot add tags")
            return {}
        
        # Get existing tags (can be list or comma-separated string)
        existing_tags = contact.get("tags", [])
        if isinstance(existing_tags, str):
            # If tags is a string, split by comma
            existing_tags = [tag.strip() for tag in existing_tags.split(",") if tag.strip()]
        elif not isinstance(existing_tags, list):
            existing_tags = []
        
        # Combine existing tags with new tags, removing duplicates
        all_tags = list(set(existing_tags + tags))
        
        # Update contact with combined tags
        endpoint = f"contacts/{contact_id}"
        params = {"locationId": self.location_id}
        payload = {"tags": all_tags}
        
        try:
            result = await self._request("PUT", endpoint, data=payload, params=params)
            logger.info(f"✅ Added tags {tags} to contact {contact_id} (total tags: {len(all_tags)})")
            return result
        except GHLAPIError as e:
            logger.error(f"Failed to add tags to contact {contact_id}: {str(e)}")
            return {}
    
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """Get all calendars for location"""
        endpoint = "calendars/"
        params = {"locationId": self.location_id}
        result = await self._request("GET", endpoint, params=params)
        return result.get("calendars", [])
    
    async def get_appointments_for_date_range(
        self,
        calendar_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all appointments from GHL API for a date range.
        
        IMPORTANT: GHL API does NOT support getting appointments by calendar/date directly.
        We MUST use the contact-based endpoint (contacts/{contact_id}/appointments) which WORKS.
        
        Strategy:
        1. Get recent contacts
        2. For each contact, get their appointments using contacts/{contact_id}/appointments
        3. Filter by calendar_id and date range
        4. Return filtered appointments to exclude booked slots
        """
        date_start = start_date.split("T")[0] if "T" in start_date else start_date
        date_end = end_date.split("T")[0] if "T" in end_date else end_date
        
        logger.info(f"🔍 Getting appointments via contacts (calendar endpoints don't work)")
        logger.info(f"   Calendar: {calendar_id} | Date range: {date_start} to {date_end}")
        
        try:
            # Step 1: Get recent contacts
            contacts_endpoint = "contacts"
            contacts_params = {
                "locationId": self.location_id,
                "limit": 100,  # GHL API max is 100
                "sortBy": "date_added"  # Must be "date_added" or "date_updated" (not "dateAdded")
            }
            
            logger.debug(f"📋 Fetching contacts...")
            contacts_result = await self._request("GET", contacts_endpoint, params=contacts_params)
            
            contacts = []
            if isinstance(contacts_result, list):
                contacts = contacts_result
            elif isinstance(contacts_result, dict):
                contacts = contacts_result.get("contacts", []) or contacts_result.get("data", []) or []
            
            if not contacts:
                logger.warning(f"⚠️ No contacts found - cannot fetch appointments")
                return []
            
            logger.info(f"✅ Found {len(contacts)} contacts, fetching their appointments...")
            
            # Step 2: For each contact, get their appointments using the WORKING endpoint
            all_appointments = []
            contacts_checked = 0
            
            for contact in contacts:
                contact_id = contact.get("id")
                if not contact_id:
                    continue
                
                contacts_checked += 1
                try:
                    # Use the WORKING contact-based endpoint: contacts/{contact_id}/appointments
                    contact_appointments = await self.get_contact_appointments(contact_id)
                    
                    if contact_appointments:
                        # Step 3: Filter by calendar_id and date range
                        for apt in contact_appointments:
                            # Log raw appointment data for debugging
                            logger.info(f"   📋 Raw appointment data: {json.dumps(apt, default=str)[:300]}")
                            
                            # Try multiple field names for calendar_id
                            apt_calendar_id = (
                                apt.get("calendarId") or 
                                apt.get("calendar_id") or 
                                apt.get("calendar", {}).get("id") if isinstance(apt.get("calendar"), dict) else None or
                                apt.get("calendarId") or
                                apt.get("calendar")
                            )
                            
                            # Try multiple field names for start time
                            apt_start = (
                                apt.get("startTime") or 
                                apt.get("start_time") or 
                                apt.get("startDate") or
                                apt.get("start") or
                                apt.get("dateTime") or
                                apt.get("appointmentTime")
                            )
                            
                            logger.info(f"   🔍 Appointment calendar_id: {apt_calendar_id} (looking for: {calendar_id})")
                            logger.info(f"   🔍 Appointment start: {apt_start}")
                            
                            # IMPORTANT: Include appointments even if calendar doesn't match
                            # This handles cases where appointments might be on different calendars
                            # but we still want to exclude the time slot to prevent double-booking
                            if apt_calendar_id and apt_calendar_id != calendar_id:
                                logger.info(f"   ⚠️  Calendar mismatch: {apt_calendar_id} != {calendar_id}, but checking date/time anyway")
                            
                            # If no calendar_id in appointment, log it but still check date
                            if not apt_calendar_id:
                                logger.warning(f"   ⚠️  Appointment has no calendar_id, checking date anyway")
                            
                            # Check if appointment is in our date range
                            if apt_start:
                                try:
                                    apt_start_str = str(apt_start)
                                    # Extract date part (YYYY-MM-DD)
                                    if "T" in apt_start_str:
                                        apt_date = apt_start_str.split("T")[0]
                                    elif " " in apt_start_str:
                                        apt_date = apt_start_str.split(" ")[0]
                                    else:
                                        apt_date = apt_start_str[:10]  # First 10 chars should be date
                                    
                                    logger.info(f"   📅 Extracted date: {apt_date} (range: {date_start} to {date_end})")
                                    
                                    # Check if date is in range
                                    if date_start <= apt_date <= date_end:
                                        all_appointments.append(apt)
                                        logger.info(f"   ✅ MATCHED! Adding appointment: {apt_date} {apt_start_str}")
                                    else:
                                        logger.debug(f"   ⏭️  Date out of range: {apt_date} not in [{date_start}, {date_end}]")
                                except Exception as date_error:
                                    logger.warning(f"   ❌ Could not parse appointment date: {date_error}, apt_start: {apt_start}")
                                    continue
                            else:
                                logger.warning(f"   ⚠️  Appointment has no start time: {apt}")
                
                except Exception as e:
                    logger.debug(f"   Error fetching appointments for contact {contact_id}: {e}")
                    continue
                
                # Limit to avoid timeout (check first 100 contacts)
                if contacts_checked >= 100:
                    logger.info(f"   ⏸️  Checked {contacts_checked} contacts (limiting to avoid timeout)")
                    break
            
            if all_appointments:
                logger.info(f"✅ SUCCESS: Found {len(all_appointments)} appointments via contact-based endpoint!")
                logger.info(f"   Checked {contacts_checked} contacts")
                # Log appointment details
                for idx, apt in enumerate(all_appointments[:5], 1):
                    apt_start = apt.get("startTime") or apt.get("start_time") or apt.get("startDate") or "unknown"
                    apt_title = apt.get("title") or apt.get("name") or "Untitled"
                    logger.info(f"   Appointment {idx}: '{apt_title}' at {apt_start}")
                return all_appointments
            else:
                logger.warning(f"⚠️ No appointments found matching calendar {calendar_id} and date range {date_start} to {date_end}")
                logger.warning(f"   Checked {contacts_checked} contacts")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error fetching appointments via contacts: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def check_slot_availability(
        self,
        calendar_id: str,
        slot_start: datetime,
        slot_end: datetime,
        appointments: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if a specific time slot is available (not booked) based on appointment data.
        Returns True if slot is available, False if booked.
        
        Args:
            calendar_id: GHL calendar ID
            slot_start: Slot start datetime
            slot_end: Slot end datetime
            appointments: List of appointments to check against (from API)
        """
        pacific_tz = ZoneInfo("America/Los_Angeles")
        slot_start_pacific = slot_start.astimezone(pacific_tz) if slot_start.tzinfo else slot_start.replace(tzinfo=pacific_tz)
        slot_end_pacific = slot_end.astimezone(pacific_tz) if slot_end.tzinfo else slot_end.replace(tzinfo=pacific_tz)
        
        # Check if any appointment overlaps with this slot
        # Only exclude slots where appointments are actually booked (from GHL API)
        for apt in appointments:
            # Try multiple field names for appointment start/end times
            apt_start = (
                apt.get("startTime") or 
                apt.get("start_time") or 
                apt.get("startDate") or 
                apt.get("start") or
                apt.get("dateTime") or
                apt.get("appointmentTime")
            )
            apt_end = (
                apt.get("endTime") or 
                apt.get("end_time") or 
                apt.get("endDate") or 
                apt.get("end") or
                apt.get("endDateTime")
            )
            
            if not apt_start:
                continue  # Skip appointments without start time
            
            try:
                # Parse appointment start time - handle various formats from GHL API
                apt_start_str = str(apt_start)
                apt_start_dt = None
                
                # Try ISO format first (most common from GHL API)
                try:
                    if apt_start_str.endswith("Z"):
                        apt_start_str = apt_start_str.replace("Z", "+00:00")
                    elif "+" not in apt_start_str and "-" in apt_start_str and "T" in apt_start_str:
                        # ISO format without timezone - assume Pacific Time
                        apt_start_str = apt_start_str + "-08:00"
                    
                    apt_start_dt = datetime.fromisoformat(apt_start_str)
                except (ValueError, AttributeError):
                    # Try GHL's MM-DD-YYYY HH:MM AM/PM format
                    try:
                        # Format: "11-25-2024 4:00 PM"
                        apt_start_dt = datetime.strptime(apt_start_str, "%m-%d-%Y %I:%M %p")
                    except ValueError:
                        try:
                            # Format: "25-Nov-2024 4:00 PM"
                            apt_start_dt = datetime.strptime(apt_start_str, "%d-%b-%Y %I:%M %p")
                        except ValueError:
                            try:
                                # Format: "2024-11-25 16:00:00"
                                apt_start_dt = datetime.strptime(apt_start_str, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                try:
                                    # Format: "2024-11-25T16:00:00"
                                    apt_start_dt = datetime.strptime(apt_start_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                                except ValueError:
                                    logger.warning(f"⚠️ Could not parse appointment start time: {apt_start_str}, skipping appointment")
                                    continue
                
                # Normalize to Pacific Time
                if apt_start_dt:
                    if apt_start_dt.tzinfo:
                        apt_start_dt = apt_start_dt.astimezone(pacific_tz)
                    else:
                        apt_start_dt = apt_start_dt.replace(tzinfo=pacific_tz)
                else:
                    continue  # Skip if we couldn't parse
                
                # Parse appointment end time
                apt_end_dt = None
                if apt_end:
                    apt_end_str = str(apt_end)
                    try:
                        if apt_end_str.endswith("Z"):
                            apt_end_str = apt_end_str.replace("Z", "+00:00")
                        elif "+" not in apt_end_str and "-" in apt_end_str and "T" in apt_end_str:
                            apt_end_str = apt_end_str + "-08:00"
                        apt_end_dt = datetime.fromisoformat(apt_end_str)
                    except (ValueError, AttributeError):
                        try:
                            apt_end_dt = datetime.strptime(apt_end_str, "%m-%d-%Y %I:%M %p")
                        except ValueError:
                            try:
                                apt_end_dt = datetime.strptime(apt_end_str, "%d-%b-%Y %I:%M %p")
                            except ValueError:
                                try:
                                    apt_end_dt = datetime.strptime(apt_end_str, "%Y-%m-%d %H:%M:%S")
                                except ValueError:
                                    try:
                                        apt_end_dt = datetime.strptime(apt_end_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                                    except ValueError:
                                        logger.warning(f"⚠️ Could not parse appointment end time: {apt_end_str}, using 1 hour default")
                                        apt_end_dt = apt_start_dt + timedelta(hours=1)
                    
                    if apt_end_dt:
                        if apt_end_dt.tzinfo:
                            apt_end_dt = apt_end_dt.astimezone(pacific_tz)
                        else:
                            apt_end_dt = apt_end_dt.replace(tzinfo=pacific_tz)
                    else:
                        apt_end_dt = apt_start_dt + timedelta(hours=1)
                else:
                    # Default to 1 hour duration if no end time
                    apt_end_dt = apt_start_dt + timedelta(hours=1)
                
                # Only check appointments on the same date as the slot
                if slot_start_pacific.date() != apt_start_dt.date():
                    continue  # Different date, no conflict
                
                # CRITICAL: Check for overlap: slot is booked if it overlaps with appointment
                # Overlap formula: slot_start < apt_end AND slot_end > apt_start
                # This ensures we exclude any slot that conflicts with a booked appointment
                if slot_start_pacific < apt_end_dt and slot_end_pacific > apt_start_dt:
                    apt_title = apt.get("title") or apt.get("name") or apt.get("subject") or "Untitled"
                    apt_date_str = apt_start_dt.strftime('%Y-%m-%d')
                    apt_time_str = apt_start_dt.strftime('%H:%M')
                    slot_time_str = slot_start_pacific.strftime('%Y-%m-%d %H:%M')
                    logger.warning(f"🚫 EXCLUDING BOOKED SLOT: {slot_time_str}")
                    logger.warning(f"   Appointment: '{apt_title}' on {apt_date_str} from {apt_time_str} to {apt_end_dt.strftime('%H:%M')}")
                    logger.warning(f"   ✅ This slot will NOT be shown to customers (booked)")
                    return False  # Slot is booked - exclude it from available slots
                    
            except Exception as parse_error:
                logger.debug(f"Could not parse appointment time: {parse_error}, appointment data: {apt}")
                continue
        
        # No conflicts found - slot is available
        return True
    
    async def get_calendar_availability(
        self, 
        calendar_id: str, 
        start_date: str, 
        end_date: str,
        calendar_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available appointment slots by checking each slot individually.
        Only returns slots that are confirmed as available (not booked).
        """
        from datetime import datetime, timedelta, time
        
        try:
            date_start = start_date.split("T")[0] if "T" in start_date else start_date
            date_end = end_date.split("T")[0] if "T" in end_date else end_date
            
            # CRITICAL: Fetch all appointments for date range from GHL API, then check each slot
            # This ensures we exclude booked slots based on actual appointment data with date/time
            logger.info(f"🔍 Fetching appointments from GHL API for calendar {calendar_id} from {date_start} to {date_end}")
            logger.info(f"   This is REQUIRED to exclude booked slots from available slots")
            
            # Fetch appointments for the entire date range (one API call)
            # This gets appointments with their date and time so we can exclude those slots
            appointments = await self.get_appointments_for_date_range(
                calendar_id=calendar_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Also check in-memory cache as fallback (for appointments we created)
            from src.utils.appointment_cache import get_cache_stats
            cache_stats = get_cache_stats()
            cache_has_data = calendar_id in cache_stats.get("cache", {})
            
            if appointments:
                logger.info(f"✅ Fetched {len(appointments)} appointments from GHL API - these will be used to EXCLUDE booked slots")
                # Log ALL appointments for debugging (not just first 3)
                for idx, apt in enumerate(appointments, 1):
                    apt_start = apt.get("startTime") or apt.get("start_time") or apt.get("startDate") or apt.get("start") or "unknown"
                    apt_end = apt.get("endTime") or apt.get("end_time") or apt.get("endDate") or apt.get("end") or "unknown"
                    apt_title = apt.get("title") or apt.get("name") or apt.get("subject") or "Untitled"
                    apt_id = apt.get("id") or apt.get("appointmentId") or "no-id"
                    logger.info(f"   📅 Appointment #{idx}: '{apt_title}' | ID: {apt_id} | Start: {apt_start} | End: {apt_end}")
                    logger.info(f"      This appointment will EXCLUDE its time slot from available slots")
            else:
                logger.warning(f"⚠️ No appointments fetched from GHL API")
                logger.warning(f"   Calendar ID: {calendar_id}, Date range: {date_start} to {date_end}")
                logger.warning(f"   ⚠️ WARNING: Cannot exclude booked slots - all slots will appear as available!")
                if cache_has_data:
                    logger.info(f"   📋 Using in-memory cache as fallback to detect booked slots")
                else:
                    logger.error(f"   ❌ CRITICAL: No appointments from API AND no cache data!")
                    logger.error(f"   ⚠️ Cannot detect booked slots - all will appear as available!")
            
            # Parse date range
            start = datetime.fromisoformat(start_date.split("T")[0] if "T" in start_date else start_date).date()
            end = datetime.fromisoformat(end_date.split("T")[0] if "T" in end_date else end_date).date()
            
            # Log the date range we're working with
            logger.info(f"📅 Date range for slot generation: {start} to {end}")
            
            # Don't adjust start date - use the requested date range as-is
            # The calling function (check_calendar_availability) already handles date validation
            if end < start:
                end = start + timedelta(days=7)
                logger.warning(f"⚠️ End date adjusted to {end} (7 days from start)")
            
            # Business hours: 8:00 AM - 4:30 PM (field work hours)
            business_start = time(8, 0)  # 8:00 AM
            business_end = time(16, 30)   # 4:30 PM

            # Generate 1-hour slots
            slot_duration = timedelta(hours=1)
            slots = []
            
            # Set timezone for all datetime operations (Pacific Time)
            pacific_tz = ZoneInfo("America/Los_Angeles")

            current_date = start
            while current_date <= end:
                # Skip weekends (Saturday=5, Sunday=6)
                if current_date.weekday() < 5:  # Monday-Friday
                    current_time = datetime.combine(current_date, business_start).replace(tzinfo=pacific_tz)
                    end_time = datetime.combine(current_date, business_end).replace(tzinfo=pacific_tz)
                    
                    while current_time < end_time:
                        slot_end = current_time + slot_duration
                        if slot_end > end_time:
                            break
                        
                        # Check if this specific slot is available based on fetched appointment data
                        slot_start_str = current_time.isoformat()
                        slot_end_str = slot_end.isoformat()
                        
                        # CRITICAL: Check slot availability against fetched appointments from GHL API
                        # This will exclude slots where appointments are booked (with time/date)
                        # The appointments list contains all booked appointments with their date and time
                        # check_slot_availability will compare each slot against these appointments
                        # and return False if the slot overlaps with any appointment
                        is_available = await self.check_slot_availability(
                            calendar_id=calendar_id,
                            slot_start=current_time,
                            slot_end=slot_end,
                            appointments=appointments  # CRITICAL: Use appointments fetched from GHL API (with time/date) to exclude booked slots
                        )
                        
                        # Only add slot if it's confirmed as available (not booked)
                        # If is_available is False, the slot overlaps with a booked appointment and should be excluded
                        if is_available:
                            slots.append({
                                "startTime": slot_start_str,
                                "endTime": slot_end_str,
                                "available": True
                            })
                            slot_time_str = current_time.strftime("%Y-%m-%d %H:%M")
                            logger.info(f"✅ INCLUDING available slot: {slot_time_str}")
                        else:
                            # Log that we're excluding a booked slot
                            slot_time_str = current_time.strftime("%Y-%m-%d %H:%M")
                            logger.info(f"⏭️ EXCLUDING booked slot: {slot_time_str} (overlaps with appointment from API)")
                        
                        current_time += slot_duration
                
                current_date += timedelta(days=1)
            
            # Calculate total possible slots for logging
            total_possible = 0
            temp_date = start
            while temp_date <= end:
                if temp_date.weekday() < 5:  # Monday-Friday
                    temp_time = datetime.combine(temp_date, business_start).replace(tzinfo=pacific_tz)
                    temp_end = datetime.combine(temp_date, business_end).replace(tzinfo=pacific_tz)
                    while temp_time < temp_end:
                        temp_slot_end = temp_time + slot_duration
                        if temp_slot_end > temp_end:
                            break
                        total_possible += 1
                        temp_time += slot_duration
                temp_date += timedelta(days=1)
            
            excluded_count = total_possible - len(slots)
            logger.info(f"✅ Calendar availability complete: {calendar_id} | {date_start} to {date_end}")
            logger.info(f"   Total possible: {total_possible} | Available: {len(slots)} | Excluded: {excluded_count}")
            
            if not slots:
                logger.warning(f"⚠️ No available slots found for calendar {calendar_id}")
            
            return slots
                
        except Exception as e:
            logger.error(f"Error getting calendar availability: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return empty list as fallback
            return []
    
    async def trigger_appointment_webhook(
        self,
        calendar_id: str,
        contact_id: str,
        start_time: str,
        end_time: str,
        title: str,
        notes: Optional[str] = None,
        service_type: Optional[str] = None,
        urgency: Optional[str] = None,
        service_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger GHL automation via webhook to create appointment.
        Sends appointment data directly to GHL's inbound webhook URL.
        """
        import httpx
        
        # GHL webhook URL for appointment creation automation
        webhook_url = settings.ghl_appointment_webhook_url or "https://services.leadconnectorhq.com/hooks/NHEXwG3xQVwKMO77jAuB/webhook-trigger/4100bff4-698c-4e6f-a771-2678ab7cb48b"
        
        if not webhook_url:
            raise GHLAPIError("GHL appointment webhook URL is not configured", status_code=500)
        
        # Format dates for GHL - convert ISO format to GHL's expected format
        # GHL expects: "MM-DD-YYYY HH:MM AM/PM" (e.g., "11-25-2024 4:00 PM")
        # Salem, OR is in Pacific Time (America/Los_Angeles)
        try:
            # Parse the ISO datetime string
            # Handle different timezone formats
            if "T" in start_time:
                # Check if it has timezone info
                if start_time.endswith("Z"):
                    # UTC timezone
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                elif "+" in start_time or start_time.count("-") >= 3:
                    # Has timezone offset (e.g., -08:00, +05:00)
                    start_dt = datetime.fromisoformat(start_time)
                else:
                    # No timezone - assume it's already in Pacific Time (local time)
                    start_dt = datetime.fromisoformat(start_time)
                    start_dt = start_dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
            else:
                # If no timezone, assume it's in Pacific Time
                start_dt = datetime.fromisoformat(start_time)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
            
            # Convert to Pacific Time if not already
            if start_dt.tzinfo and start_dt.tzinfo != ZoneInfo("America/Los_Angeles"):
                start_dt = start_dt.astimezone(ZoneInfo("America/Los_Angeles"))
            elif start_dt.tzinfo is None:
                # If still no timezone, assume Pacific
                start_dt = start_dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
            
            # Format as "MM-DD-YYYY HH:MM AM/PM" (GHL's required format)
            # GHL is very strict - must be exactly: "MM-DD-YYYY HH:MM AM/PM"
            # Remove leading zeros from hour (12-hour format)
            hour_12 = int(start_dt.strftime("%I"))  # Convert to int to remove leading zero
            minute = start_dt.strftime("%M")
            am_pm = start_dt.strftime("%p")
            start_time_formatted = f"{start_dt.month:02d}-{start_dt.day:02d}-{start_dt.year} {hour_12}:{minute} {am_pm}"
            
            # Also try alternative format "DD-MMM-YYYY HH:MM AM/PM" as backup
            month_name = start_dt.strftime("%b").upper()  # Uppercase month abbreviation
            start_time_formatted_alt = f"{start_dt.day:02d}-{month_name}-{start_dt.year} {hour_12}:{minute} {am_pm}"
            
            # Same for end_time
            if "T" in end_time:
                # Check if it has timezone info
                if end_time.endswith("Z"):
                    # UTC timezone
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                elif "+" in end_time or end_time.count("-") >= 3:
                    # Has timezone offset
                    end_dt = datetime.fromisoformat(end_time)
                else:
                    # No timezone - assume it's already in Pacific Time (local time)
                    end_dt = datetime.fromisoformat(end_time)
                    end_dt = end_dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
            else:
                end_dt = datetime.fromisoformat(end_time)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
            
            # Convert to Pacific Time if not already
            if end_dt.tzinfo and end_dt.tzinfo != ZoneInfo("America/Los_Angeles"):
                end_dt = end_dt.astimezone(ZoneInfo("America/Los_Angeles"))
            elif end_dt.tzinfo is None:
                # If still no timezone, assume Pacific
                end_dt = end_dt.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
            
            # Format end time the same way
            hour_12_end = int(end_dt.strftime("%I"))  # Convert to int to remove leading zero
            minute_end = end_dt.strftime("%M")
            am_pm_end = end_dt.strftime("%p")
            end_time_formatted = f"{end_dt.month:02d}-{end_dt.day:02d}-{end_dt.year} {hour_12_end}:{minute_end} {am_pm_end}"
            
            month_name_end = end_dt.strftime("%b").upper()  # Uppercase month abbreviation
            end_time_formatted_alt = f"{end_dt.day:02d}-{month_name_end}-{end_dt.year} {hour_12_end}:{minute_end} {am_pm_end}"
            
            logger.info(f"📅 Formatted dates - Start: {start_time_formatted} (from {start_time}), End: {end_time_formatted} (from {end_time})")
            logger.info(f"📅 Original datetime - Start: {start_dt}, End: {end_dt}")
        except Exception as e:
            logger.warning(f"⚠️ Date formatting error, using original format: {e}")
            start_time_formatted = start_time
            end_time_formatted = end_time
        
        # Get contact details to include address in appointment
        contact_address = service_address
        if not contact_address:
            try:
                contact = await self.get_contact(contact_id=contact_id)
                if contact:
                    contact_address = (
                        contact.get("address1") or 
                        contact.get("address") or 
                        ""
                    )
                    logger.info(f"📍 Retrieved contact address: {contact_address}")
            except Exception as e:
                logger.warning(f"⚠️ Could not retrieve contact address: {e}")
        
        # Build notes with location included (GHL automation should use this)
        appointment_notes = notes or ""
        if contact_address:
            location_note = f"\n\n📍 Service Address: {contact_address}"
            appointment_notes = appointment_notes + location_note if appointment_notes else location_note.strip()
        
        # Prepare webhook payload with all appointment details
        # GHL webhook expects these field names (matching GHL's internal format)
        # IMPORTANT: Use snake_case for inbound webhook variables in GHL
        webhook_payload = {
            # Primary fields (camelCase for GHL API compatibility)
            "contactId": contact_id,
            "calendarId": calendar_id,
            "startTime": start_time_formatted,  # MM-DD-YYYY format
            "endTime": end_time_formatted,  # MM-DD-YYYY format
            "title": title,
            "notes": appointment_notes,  # Include location in notes
            "description": appointment_notes,  # Also in description field
            "serviceType": service_type or "",
            "urgency": urgency or "",
            "locationId": self.location_id,
            "address": contact_address or "",  # Service address for appointment
            "location": contact_address or "",  # Location field (alternative name)
            "appointment_location": contact_address or "",  # Appointment location field
            "appointmentAddress": contact_address or "",  # camelCase version
            "serviceLocation": contact_address or "",  # Alternative field name
            # Snake_case versions (for GHL inbound webhook variable mapping)
            "contact_id": contact_id,  # Use this in "Find Contact" action
            "calendar_id": calendar_id,
            "start_time": start_time_formatted,  # MM-DD-YYYY format - USE THIS in Book Appointment
            "end_time": end_time_formatted,  # MM-DD-YYYY format
            "start_time_alt": start_time_formatted_alt,  # DD-MMM-YYYY format (alternative)
            "end_time_alt": end_time_formatted_alt,  # DD-MMM-YYYY format (alternative)
            "service_type": service_type or "",
            "service_address": contact_address or "",  # Service address (snake_case)
            "appointment_address": contact_address or "",  # Appointment address (alternative)
            "location_id": self.location_id,
            # Additional fields for Find Contact and address
            "city": "Salem",  # Default city for Salem, OR area
            "state": "OR",
            "country": "US",
            "postal_code": "",  # Will be extracted from address if available
            "created_at": datetime.now().isoformat()
        }
        
        # If contact_address contains full address, try to extract components
        if contact_address:
            # Try to extract city, state, zip from address string
            address_parts = contact_address.split(",")
            if len(address_parts) >= 2:
                # Usually format: "123 Main St, Salem, OR 97301"
                if len(address_parts) >= 3:
                    webhook_payload["city"] = address_parts[-2].strip() if len(address_parts) >= 3 else "Salem"
                    state_zip = address_parts[-1].strip().split()
                    if len(state_zip) >= 1:
                        webhook_payload["state"] = state_zip[0]
                    if len(state_zip) >= 2:
                        webhook_payload["postal_code"] = state_zip[1]
                elif len(address_parts) == 2:
                    # Format: "123 Main St, Salem OR 97301"
                    city_state_zip = address_parts[1].strip().split()
                    if len(city_state_zip) >= 1:
                        webhook_payload["city"] = city_state_zip[0]
                    if len(city_state_zip) >= 2:
                        webhook_payload["state"] = city_state_zip[1]
                    if len(city_state_zip) >= 3:
                        webhook_payload["postal_code"] = city_state_zip[2]
        
        logger.info(f"📤 Sending webhook to GHL: {webhook_url}")
        logger.info(f"📦 Webhook payload: {webhook_payload}")
        
        try:
            # Send webhook to GHL
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook_url,
                    json=webhook_payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json() if response.content else {}
                logger.info(f"✅ Webhook sent to GHL successfully. Response: {result}")
                logger.info(f"✅ Webhook status: {response.status_code}")
                logger.info(f"📋 IMPORTANT: Ensure your GHL automation is configured to:")
                logger.info(f"   1. Find Contact using 'contact_id' from webhook")
                logger.info(f"   2. Create Appointment using 'start_time', 'end_time', 'calendar_id', 'title'")
                logger.info(f"   3. Set appointment Location/Address using 'service_address', 'appointment_location', or 'address' field")
                logger.info(f"   4. Use 'notes' or 'description' field (which includes service address) for appointment description")
                logger.info(f"   5. The appointment should appear in the main calendar view after automation runs")
                logger.info(f"📍 Service Address sent in webhook: {contact_address or 'NOT PROVIDED'}")
                logger.info(f"📝 Notes/Description includes address: {bool(contact_address)}")
        except Exception as e:
            logger.error(f"❌ Failed to send webhook to GHL: {e}")
            raise
        
        # Store additional appointment data in custom fields (for workflow to access)
        try:
            # Update contact with appointment metadata in custom fields
            # This allows the workflow to access title, notes, service_type, urgency, end_time
            from src.utils.ghl_fields import build_custom_fields_array
            # Note: build_custom_fields_array is now async and requires await
            
            custom_fields_dict = {
                "appointment_title": title,
                "appointment_notes": notes or "",
                "appointment_service_type": service_type or "",
                "appointment_urgency": urgency or "",
                "appointment_end_time": end_time,
                "appointment_start_time": start_time,
                "appointment_calendar_id": calendar_id
            }
            custom_fields_array = await build_custom_fields_array(custom_fields_dict, use_field_ids=True)
            await self.update_contact(contact_id, {"customFields": custom_fields_array})
            logger.info(f"✅ Updated contact custom fields with appointment metadata")
        except Exception as field_error:
            logger.warning(f"⚠️ Could not update custom fields (non-critical): {field_error}")
        
        # Try to create timeline note for visibility (non-blocking)
        try:
            note_text = (
                f"📅 APPOINTMENT REQUEST (Webhook Sent)\n\n"
                f"Title: {title}\n"
                f"Start Time: {start_time}\n"
                f"End Time: {end_time}\n"
                f"Calendar ID: {calendar_id}\n"
                f"Service Type: {service_type or 'Not specified'}\n"
                f"Urgency: {urgency or 'Standard'}\n"
                f"Notes: {notes or 'None'}\n\n"
                f"✅ Appointment details sent via webhook to GHL automation."
            )
            await self.add_timeline_note(contact_id, note_text)
        except Exception as note_error:
            # Don't fail if note creation fails - webhook was successful
            logger.warning(f"⚠️ Could not create timeline note (non-critical): {note_error}")
        
        return {
            "id": f"webhook-{calendar_id}-{contact_id}-{int(datetime.now().timestamp())}",
            "status": "webhook_triggered",
            "message": "Appointment creation triggered via GHL webhook automation",
            "contactId": contact_id,
            "calendarId": calendar_id,
            "startTime": start_time,
            "endTime": end_time,
            "title": title,
            "webhook_triggered": True
        }
    
    async def book_appointment(
        self,
        calendar_id: str,
        contact_id: str,
        start_time: str,
        end_time: str,
        title: str,
        notes: Optional[str] = None,
        assigned_user_id: Optional[str] = None,
        service_address: Optional[str] = None,
        reschedule_appointment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Book appointment in GHL calendar - tries direct API first, then webhook fallback"""
        # If rescheduling, cancel the existing appointment first
        if reschedule_appointment_id:
            logger.info(f"🔄 Rescheduling: Cancelling appointment {reschedule_appointment_id} before booking new one")
            cancel_result = await self.cancel_appointment(reschedule_appointment_id, contact_id)
            if cancel_result.get("success"):
                logger.info(f"✅ Cancelled existing appointment {reschedule_appointment_id}")
            else:
                logger.warning(f"⚠️ Could not cancel appointment via API, but proceeding with new booking")
        
        # CRITICAL: Try direct API creation first (for calendar view visibility)
        logger.info(f"📅 Attempting direct API appointment creation for calendar view...")
        
        try:
            # Format dates for GHL API
            pacific_tz = ZoneInfo("America/Los_Angeles")
            
            # Parse start_time
            if "T" in start_time:
                if start_time.endswith("Z"):
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                else:
                    start_dt = datetime.fromisoformat(start_time)
            else:
                start_dt = datetime.fromisoformat(start_time)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=pacific_tz)
            
            if start_dt.tzinfo != pacific_tz:
                start_dt = start_dt.astimezone(pacific_tz)
            
            # Parse end_time
            if "T" in end_time:
                if end_time.endswith("Z"):
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                else:
                    end_dt = datetime.fromisoformat(end_time)
            else:
                end_dt = datetime.fromisoformat(end_time)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=pacific_tz)
            
            if end_dt.tzinfo != pacific_tz:
                end_dt = end_dt.astimezone(pacific_tz)
            
            # Format for GHL API (ISO format with timezone)
            start_time_iso = start_dt.isoformat()
            end_time_iso = end_dt.isoformat()
            
            # Try multiple GHL API endpoints for appointment creation
            endpoints_to_try = [
                f"calendars/events/appointments",
                f"calendars/{calendar_id}/events/appointments",
                f"calendars/events",
                f"calendars/{calendar_id}/events",
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    payload = {
                        "locationId": self.location_id,
                        "calendarId": calendar_id,
                        "contactId": contact_id,
                        "startTime": start_time_iso,
                        "endTime": end_time_iso,
                        "title": title,
                        "notes": notes or "",
                        "description": notes or "",
                    }
                    
                    # Add address/location if provided
                    if service_address:
                        payload["address"] = service_address
                        payload["location"] = service_address
                        payload["appointmentLocation"] = service_address
                    
                    # Add assigned user if provided
                    if assigned_user_id:
                        payload["assignedUserId"] = assigned_user_id
                    
                    logger.info(f"📅 Trying endpoint: {endpoint}")
                    logger.info(f"📦 Payload: {json.dumps(payload, default=str)}")
                    
                    result = await self._request("POST", endpoint, data=payload)
                    
                    # Check if appointment was created successfully
                    appointment_id = result.get("id") or result.get("appointmentId") or result.get("eventId")
                    if appointment_id:
                        logger.info(f"✅ SUCCESS: Appointment created via API! ID: {appointment_id}")
                        logger.info(f"✅ Appointment will appear in calendar view immediately")
                        
                        # Add to cache
                        from src.utils.appointment_cache import add_appointment_to_cache
                        try:
                            add_appointment_to_cache(
                                calendar_id=calendar_id,
                                start_time=start_time,
                                end_time=end_time
                            )
                        except Exception as cache_error:
                            logger.warning(f"⚠️ Could not add appointment to cache: {cache_error}")
                        
                        return {
                            "id": appointment_id,
                            "status": "created",
                            "message": "Appointment created successfully via API",
                            "contactId": contact_id,
                            "calendarId": calendar_id,
                            "startTime": start_time,
                            "endTime": end_time,
                            "title": title,
                            "api_created": True,
                            "webhook_triggered": False
                        }
                except GHLAPIError as api_error:
                    if api_error.status_code == 404:
                        # Endpoint doesn't exist, try next one
                        logger.debug(f"Endpoint {endpoint} not available (404), trying next...")
                        continue
                    elif api_error.status_code in [400, 422]:
                        # Bad request - endpoint exists but payload is wrong, try next
                        logger.debug(f"Endpoint {endpoint} rejected payload (400/422), trying next...")
                        continue
                    else:
                        # Other error, log and try next
                        logger.debug(f"Endpoint {endpoint} error: {api_error}, trying next...")
                        continue
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} exception: {e}, trying next...")
                    continue
            
            logger.warning(f"⚠️ Direct API creation failed for all endpoints, falling back to webhook method")
        except Exception as api_error:
            logger.warning(f"⚠️ Direct API creation attempt failed: {api_error}, falling back to webhook method")
        
        # Fallback to webhook trigger approach
        logger.info(f"📤 Falling back to webhook trigger for appointment creation")
        
        # Add appointment to in-memory cache immediately (before webhook)
        from src.utils.appointment_cache import add_appointment_to_cache
        try:
            add_appointment_to_cache(
                calendar_id=calendar_id,
                start_time=start_time,
                end_time=end_time
            )
            logger.info(f"✅ Added appointment to in-memory cache: {calendar_id} at {start_time}")
        except Exception as cache_error:
            logger.warning(f"⚠️ Could not add appointment to cache: {cache_error}")
        
        return await self.trigger_appointment_webhook(
            calendar_id=calendar_id,
            contact_id=contact_id,
            start_time=start_time,
            end_time=end_time,
            title=title,
            notes=notes,
            service_address=service_address
        )
    
    async def update_custom_fields(self, contact_id: str, custom_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update contact custom fields"""
        endpoint = f"contacts/{contact_id}/custom-fields"
        payload = {
            "locationId": self.location_id,
            **custom_fields
        }
        return await self._request("PUT", endpoint, data=payload)
    
    async def get_contact_appointments(self, contact_id: str) -> List[Dict[str, Any]]:
        """
        Get existing appointments for a contact.
        Returns list of appointments or empty list if none found or API unavailable.
        """
        appointments = []
        endpoints_to_try = [
            f"contacts/{contact_id}/appointments",
            "appointments",
        ]
        
        for endpoint in endpoints_to_try:
            try:
                params = {
                    "locationId": self.location_id,
                    "contactId": contact_id
                }
                result = await self._request("GET", endpoint, params=params)
                
                if isinstance(result, list):
                    appointments = result
                    logger.info(f"✅ Found {len(appointments)} appointments for contact {contact_id}")
                    break
                elif isinstance(result, dict):
                    appointments = result.get("appointments", []) or result.get("data", []) or result.get("events", [])
                    if appointments:
                        logger.info(f"✅ Found {len(appointments)} appointments for contact {contact_id}")
                        break
            except GHLAPIError as e:
                if e.status_code == 404:
                    # Expected - GHL appointment endpoints are often not available
                    continue
                else:
                    logger.debug(f"Error fetching appointments from {endpoint}: {e}")
                    continue
            except Exception as e:
                logger.debug(f"Unexpected error fetching appointments from {endpoint}: {e}")
                continue
        
        if not appointments:
            logger.debug(f"Could not fetch appointments for contact {contact_id} (GHL API limitation)")
        
        return appointments
    
    async def cancel_appointment(self, appointment_id: str, contact_id: str) -> Dict[str, Any]:
        """
        Cancel an existing appointment in GHL using the official API.
        
        According to GHL API docs: https://marketplace.gohighlevel.com/docs/ghl/calendars/edit-appointment
        Use PUT /calendars/events/appointments/:eventId to update appointment status to cancelled.
        """
        logger.info(f"🔄 Attempting to cancel appointment {appointment_id} for contact {contact_id}")
        
        # First, try to get the appointment to find the eventId if we only have appointmentId
        # GHL API uses eventId for DELETE operations, not appointmentId
        event_id = appointment_id
        try:
            # Try to get appointment details directly
            contact_appointments = await self.get_contact_appointments(contact_id)
            for apt in contact_appointments:
                apt_id = apt.get("id") or apt.get("appointmentId") or apt.get("appointment_id")
                apt_event_id = apt.get("eventId") or apt.get("event_id") or apt.get("eventId")
                
                # Check if this is the appointment we're looking for
                if apt_id == appointment_id or apt.get("id") == appointment_id:
                    if apt_event_id:
                        event_id = apt_event_id
                        logger.info(f"📋 Found eventId {event_id} for appointment {appointment_id}")
                    else:
                        # If no eventId found, the appointment_id might BE the eventId
                        logger.info(f"📋 No eventId found, using appointment_id {appointment_id} as eventId")
                    break
            
            # Also try fetching appointment directly by ID
            if event_id == appointment_id:
                try:
                    # Try GET /calendars/events/appointments/:appointmentId to get eventId
                    get_endpoint = f"calendars/events/appointments/{appointment_id}"
                    params = {"locationId": self.location_id}
                    apt_data = await self._request("GET", get_endpoint, params=params)
                    if apt_data:
                        event_id = apt_data.get("eventId") or apt_data.get("id") or apt_data.get("event_id") or appointment_id
                        logger.info(f"📋 Retrieved eventId {event_id} from appointment details")
                except Exception as get_error:
                    logger.debug(f"Could not fetch appointment details directly: {get_error}")
                    # Continue with appointment_id as eventId
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch appointment details to find eventId: {e}")
            # Continue with original appointment_id - it might be the eventId
        
        try:
            # Method 1: Official GHL API endpoint - DELETE /calendars/events/:eventId
            # According to GHL API docs: https://marketplace.gohighlevel.com/docs/
            # The correct endpoint is DELETE /calendars/events/:eventId (not /calendars/events/appointments/:eventId)
            official_endpoint = f"calendars/events/{event_id}"
            try:
                params = {"locationId": self.location_id}
                logger.info(f"🔍 Trying official DELETE endpoint: DELETE {official_endpoint}")
                result = await self._request("DELETE", official_endpoint, params=params)
                logger.info(f"✅ Successfully cancelled appointment {appointment_id} (eventId: {event_id}) via DELETE {official_endpoint}")
                return {"success": True, "method": "api_delete_official", "result": result}
            except GHLAPIError as e:
                logger.warning(f"⚠️ Official DELETE endpoint failed: {e.status_code} - {e}")
                if e.status_code == 404:
                    logger.info(f"   404 error - event {event_id} not found, trying alternative methods")
                else:
                    logger.warning(f"   Error details: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Unexpected error with official DELETE endpoint: {e}")
            
            # Method 2: Try DELETE with original appointment_id (in case it's the eventId)
            if event_id != appointment_id:
                try:
                    endpoint = f"calendars/events/{appointment_id}"
                    params = {"locationId": self.location_id}
                    logger.info(f"🔍 Trying DELETE with original appointment_id: {endpoint}")
                    result = await self._request("DELETE", endpoint, params=params)
                    logger.info(f"✅ Successfully cancelled appointment {appointment_id} via DELETE {endpoint}")
                    return {"success": True, "method": "api_delete_original_id", "result": result}
                except GHLAPIError as e:
                    logger.warning(f"⚠️ DELETE with original ID failed: {e.status_code} - {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Unexpected error with DELETE original ID: {e}")
            
            # Method 3: Try PUT to update status to cancelled (fallback)
            put_endpoints = [
                f"calendars/events/{event_id}",
                f"calendars/events/appointments/{event_id}",
                f"calendars/events/{appointment_id}",
                f"calendars/events/appointments/{appointment_id}",
            ]
            
            for endpoint in put_endpoints:
                try:
                    payload = {
                        "locationId": self.location_id,
                        "appointmentStatus": "cancelled",
                        "status": "cancelled"
                    }
                    logger.info(f"🔍 Trying PUT method: {endpoint}")
                    result = await self._request("PUT", endpoint, data=payload)
                    logger.info(f"✅ Successfully cancelled appointment {appointment_id} via PUT {endpoint}")
                    return {"success": True, "method": "api_put", "result": result}
                except GHLAPIError as e:
                    if e.status_code == 404:
                        logger.debug(f"   PUT {endpoint} returned 404, trying next")
                        continue
                    else:
                        logger.warning(f"⚠️ PUT {endpoint} failed: {e.status_code} - {e}")
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ Unexpected error with PUT {endpoint}: {e}")
                    continue
            
            # Method 4: Try alternative DELETE endpoints (fallback)
            delete_endpoints = [
                f"calendars/events/appointments/{event_id}",
                f"calendars/events/appointments/{appointment_id}",
                f"appointments/{appointment_id}",
            ]
            
            for endpoint in delete_endpoints:
                try:
                    logger.info(f"🔍 Trying DELETE method: {endpoint}")
                    params = {"locationId": self.location_id}
                    result = await self._request("DELETE", endpoint, params=params)
                    logger.info(f"✅ Successfully cancelled appointment {appointment_id} via DELETE {endpoint}")
                    return {"success": True, "method": "api_delete", "result": result}
                except GHLAPIError as e:
                    if e.status_code == 404:
                        logger.debug(f"   DELETE {endpoint} returned 404, trying next")
                        continue
                    else:
                        logger.warning(f"⚠️ DELETE {endpoint} failed: {e.status_code} - {e}")
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ Unexpected error with DELETE {endpoint}: {e}")
                    continue
            
            # Method 4: Try alternative PUT endpoints (fallback)
            alternative_endpoints = [
                f"appointments/{appointment_id}",
                f"calendars/appointments/{appointment_id}",
                f"contacts/{contact_id}/appointments/{appointment_id}",
            ]
            
            for endpoint in alternative_endpoints:
                try:
                    payload = {
                        "locationId": self.location_id,
                        "appointmentStatus": "cancelled",
                        "status": "cancelled"
                    }
                    logger.info(f"🔍 Trying alternative endpoint: PUT {endpoint}")
                    result = await self._request("PUT", endpoint, data=payload)
                    logger.info(f"✅ Successfully cancelled appointment {appointment_id} via PUT {endpoint}")
                    return {"success": True, "method": "api_alternative", "result": result}
                except GHLAPIError as e:
                    if e.status_code == 404:
                        logger.debug(f"   PUT {endpoint} returned 404, trying next")
                        continue
                    else:
                        logger.warning(f"⚠️ PUT {endpoint} failed: {e.status_code} - {e}")
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ Unexpected error with PUT {endpoint}: {e}")
                    continue
            
            # Method 5: Add timeline note for manual cancellation (fallback)
            logger.warning(f"⚠️ Could not cancel appointment {appointment_id} via any API method, adding timeline note for manual cancellation")
            note_text = (
                f"🔄 APPOINTMENT CANCELLATION REQUEST\n\n"
                f"Appointment ID: {appointment_id}\n"
                f"Event ID: {event_id}\n"
                f"Action Required: Please cancel this appointment in GHL dashboard.\n"
                f"Contact ID: {contact_id}\n"
                f"Status: API cancellation failed - manual cancellation required."
            )
            try:
                await self.add_timeline_note(contact_id, note_text)
                logger.info(f"✅ Added cancellation note for appointment {appointment_id}")
                return {"success": True, "method": "timeline_note", "note": "Cancellation note added - requires manual cancellation in GHL"}
            except Exception as note_error:
                logger.error(f"❌ Could not add cancellation note: {note_error}")
                return {"success": False, "error": f"Could not cancel appointment via API or timeline note. Last error: {str(note_error)}"}
        except Exception as e:
            logger.error(f"❌ Error cancelling appointment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    async def add_timeline_note(self, contact_id: str, note: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Add note to contact timeline - returns success status, never raises"""
        endpoint = f"contacts/{contact_id}/notes"
        payload = {"body": note}
        if user_id:
            payload["userId"] = user_id
        
        params = {"locationId": self.location_id}
        
        try:
            return await self._request("POST", endpoint, data=payload, params=params)
        except GHLAPIError as e:
            # GHL notes API is inconsistent - just log and return failure status
            logger.warning(f"Could not create timeline note (non-critical): {e}")
            return {"id": "skipped", "success": False, "message": str(e)}
        except Exception as e:
            logger.warning(f"Unexpected error creating timeline note (non-critical): {e}")
            return {"id": "skipped", "success": False, "message": str(e)}
    
    async def trigger_automation(self, contact_id: str, automation_id: str) -> Dict[str, Any]:
        """Trigger GHL automation (for SMS/email confirmations)"""
        endpoint = f"contacts/{contact_id}/automations/{automation_id}/trigger"
        payload = {
            "locationId": self.location_id
        }
        return await self._request("POST", endpoint, data=payload)
    
    
    async def get_custom_fields(self) -> List[Dict[str, Any]]:
        """Get all custom fields for location"""
        # Try locations endpoint first
        endpoint = f"locations/{self.location_id}/customFields"
        try:
            result = await self._request("GET", endpoint)
            # GHL might return fields directly or in a nested structure
            if isinstance(result, list):
                return result
            return result.get("customFields", []) or result.get("fields", []) or result.get("data", []) or []
        except GHLAPIError as e:
            # 404 is okay - means no custom fields exist yet
            if e.status_code == 404:
                logger.info("No custom fields found (404) - this is normal if none exist yet")
                return []
            logger.warning(f"Failed to get custom fields: {e}")
            return []
    
    async def create_custom_field(
        self,
        name: str,
        key: str,
        field_type: str,
        object_type: str = "contact",
        options: Optional[List[str]] = None,
        required: bool = False,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a custom field in GHL.
        Uses /locations/:locationId/customFields endpoint.
        
        Args:
            name: Display name of the field
            key: Unique field key (must match exactly - case sensitive)
            field_type: Type of field (text, textarea, dropdown, number, date, checkbox, url)
            object_type: Object type (contact, opportunity, etc.) - default: "contact"
            options: List of options for dropdown fields
            required: Whether field is required
            parent_id: Parent folder ID (not used in this endpoint format)
        
        Returns:
            Created custom field data
        """
        # Use locations endpoint: POST /locations/:locationId/customFields
        # This endpoint DOES support contact custom fields!
        endpoint = f"locations/{self.location_id}/customFields"
        
        # Map our field types to GHL dataType enum values (must be uppercase)
        type_mapping = {
            "text": "TEXT",
            "textarea": "LARGE_TEXT",
            "url": "TEXT",  # URL stored as TEXT
            "number": "NUMERICAL",
            "checkbox": "CHECKBOX",
            "dropdown": "SINGLE_OPTIONS",
            "date": "DATE",
            "email": "EMAIL",
            "phone": "PHONE"
        }
        
        data_type = type_mapping.get(field_type.lower(), "TEXT")
        
        # Build payload for locations/customFields endpoint
        # GHL auto-generates fieldKey as "contact.{name_lowercase_with_underscores}"
        # So we need to name the field to match our desired key
        # If key is "ai_call_summary", name should be "AI Call Summary" or similar
        payload = {
            "name": name,
            "dataType": data_type,
        }
        
        # Add options for dropdown/select fields AND checkbox fields
        # GHL CHECKBOX type requires options array (Yes/No typically)
        if data_type == "CHECKBOX":
            # CHECKBOX requires options - use Yes/No by default
            payload["options"] = ["Yes", "No"]
        elif data_type in ["SINGLE_OPTIONS", "MULTIPLE_OPTIONS"] and options:
            # GHL expects options as array of strings
            payload["options"] = options
        
        try:
            result = await self._request("POST", endpoint, data=payload)
            custom_field = result.get("customField", result)
            field_key = custom_field.get("fieldKey", "")

            expected_key = f"contact.{key}" if not key.startswith("contact.") else key
            if field_key and field_key != expected_key:
                logger.warning(
                    f"Field key mismatch: Expected '{expected_key}', Got '{field_key}'. "
                    f"GHL auto-generated key from name. The system will use '{field_key}'."
                )
            logger.info(f"✅ Created custom field '{name}' with key '{field_key}'")
            return custom_field
        except GHLAPIError as e:
            error_msg = str(e).lower()
            if e.status_code in [400, 409] and ("already exists" in error_msg or "duplicate" in error_msg):
                logger.info(f"Custom field '{key}' already exists, skipping creation")
                # Try to get existing field
                existing_fields = await self.get_custom_fields()
                expected_key = f"contact.{key}" if not key.startswith("contact.") else key
                for field in existing_fields:
                    field_key = field.get("fieldKey") or field.get("key", "")
                    field_name = field.get("name", "").lower()
                    if field_key == expected_key or field_key == key or field_name == name.lower():
                        logger.info(f"Found existing field: {field_key}")
                        return field
                # If we can't find it, that's okay - it exists but we can't retrieve it
                logger.warning(f"Field '{key}' exists but could not be retrieved - this is okay")
                return {"fieldKey": expected_key, "name": name, "exists": True}
            raise


