# Lead Handling Issues Found & Fixes

## Issues Identified

### 1. **Lead Source Not Captured Correctly** ❌
**Location:** `src/webhooks/ghl.py` line 297
**Problem:** Code uses `data.get("leadSource")` but `data` is not defined in `handle_new_lead` function
**Impact:** Lead source is never captured for manual entries, website, Yelp, Thumbtack
**Fix:** Changed to use `webhook_body` and added contact tags/fields checking

### 2. **Website/Yelp/Thumbtack Lead Sources Not Distinguished** ⚠️
**Problem:** All three use `contact.created` event, so we can't distinguish them from webhook alone
**Impact:** Lead source tagging may be incorrect or missing
**Solution:** 
- Check contact tags in GHL (should be tagged before webhook)
- Check contact custom fields
- Check webhook payload for source indicators
- Added tag-based detection

### 3. **Missing Test Scenarios** ⚠️
**Testing Protocol Gaps:**
- Doesn't test duplicate call prevention (`vapi_called: true` check)
- Doesn't test phone number validation failures
- Doesn't test missing phone number scenario
- Doesn't test lead source extraction from tags
- Doesn't verify lead source is actually saved to custom fields

### 4. **Lead Source Tagging Logic** ⚠️
**Current:** Only captures lead source if present in webhook `data` object
**Should:** Check multiple sources:
- Webhook payload
- Contact tags
- Contact custom fields
- URL referrer (if available)

## Fixes Applied

1. ✅ Fixed `data.get("leadSource")` → `webhook_body.get("leadSource")`
2. ✅ Added contact tags checking for lead source
3. ✅ Added lead source normalization (maps variations to standard values)
4. ✅ Enhanced logging for lead source identification
5. ✅ Updated testing protocol with missing scenarios

## Testing Requirements

### New Test Scenarios Needed:

1. **TEST 9A: Duplicate Call Prevention**
   - Create contact with `vapi_called: true`
   - Trigger webhook
   - Verify call is NOT initiated (skipped)

2. **TEST 9B: Lead Source from Tags**
   - Create contact with tag "yelp" or "website"
   - Trigger webhook
   - Verify lead source extracted from tag

3. **TEST 9C: Missing Phone Number**
   - Create contact without phone number
   - Trigger webhook
   - Verify call is NOT initiated (graceful skip)

4. **TEST 9D: Invalid Phone Number**
   - Create contact with invalid phone format
   - Trigger webhook
   - Verify call is NOT initiated (validation error logged)

5. **TEST 9E: Lead Source Persistence**
   - After call initiated, verify `lead_source` custom field is saved
   - Check GHL dashboard to confirm field value

