"""
Simple in-memory cache to track recently cancelled appointments.
This helps filter out appointments that were just cancelled (even if only via timeline note)
from the existing appointments check, preventing false positives.
"""
from datetime import datetime, timedelta
from typing import Set, Dict
from src.utils.logging import logger

# In-memory cache: {contact_id: {appointment_id: cancellation_time}}
_cancellation_cache: Dict[str, Dict[str, datetime]] = {}

# How long to keep cancelled appointments in cache (5 minutes)
CACHE_DURATION = timedelta(minutes=5)


def add_cancelled_appointment(contact_id: str, appointment_id: str):
    """Add an appointment to the cancellation cache"""
    if contact_id not in _cancellation_cache:
        _cancellation_cache[contact_id] = {}
    
    _cancellation_cache[contact_id][appointment_id] = datetime.now()
    logger.info(f"📝 Added appointment {appointment_id} to cancellation cache for contact {contact_id}")


def is_recently_cancelled(contact_id: str, appointment_id: str) -> bool:
    """Check if an appointment was recently cancelled (within cache duration)"""
    if contact_id not in _cancellation_cache:
        return False
    
    if appointment_id not in _cancellation_cache[contact_id]:
        return False
    
    cancellation_time = _cancellation_cache[contact_id][appointment_id]
    age = datetime.now() - cancellation_time
    
    if age > CACHE_DURATION:
        # Expired, remove it
        del _cancellation_cache[contact_id][appointment_id]
        if not _cancellation_cache[contact_id]:
            del _cancellation_cache[contact_id]
        return False
    
    logger.debug(f"✅ Appointment {appointment_id} was recently cancelled ({age.total_seconds():.0f}s ago), filtering it out")
    return True


def cleanup_expired():
    """Remove expired entries from cache (called periodically)"""
    now = datetime.now()
    expired_contacts = []
    
    for contact_id, appointments in _cancellation_cache.items():
        expired_appointments = [
            apt_id for apt_id, cancel_time in appointments.items()
            if now - cancel_time > CACHE_DURATION
        ]
        for apt_id in expired_appointments:
            del appointments[apt_id]
        
        if not appointments:
            expired_contacts.append(contact_id)
    
    for contact_id in expired_contacts:
        del _cancellation_cache[contact_id]
    
    if expired_contacts:
        logger.debug(f"🧹 Cleaned up {len(expired_contacts)} expired cancellation cache entries")

