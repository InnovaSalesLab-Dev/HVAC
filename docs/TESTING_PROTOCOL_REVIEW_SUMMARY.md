# Testing Protocol Review & Fixes Summary

## Critical Issues Found & Fixed

### 1. **Lead Source Not Captured** ❌ → ✅ FIXED
**Location:** `src/webhooks/ghl.py` line 297
**Problem:** Code used `data.get("leadSource")` but `data` variable doesn't exist in `handle_new_lead` function
**Impact:** Lead source was NEVER saved for any leads (critical bug)
**Fix Applied:**
- Changed to use `webhook_body.get("leadSource")`
- Added contact tags checking
- Added contact custom fields checking
- Added lead source normalization (maps variations to standard values)

### 2. **Website/Yelp/Thumbtack Lead Sources Not Distinguished** ⚠️ → ✅ FIXED
**Problem:** All three use same `contact.created` webhook event, can't distinguish from webhook alone
**Impact:** Lead source tagging was missing for these sources
**Fix Applied:**
- Added tag-based lead source extraction
- System now checks contact tags for "yelp", "website", "thumbtack"
- Maps tag values to standard lead source values

### 3. **Missing Test Scenarios** ⚠️ → ✅ ADDED
**Gaps Found:**
- No test for duplicate call prevention
- No test for missing phone number handling
- No test for invalid phone number validation
- No test for lead source extraction from tags
- No verification that lead source is actually saved to GHL

**Tests Added:**
- TEST 9A: Duplicate Call Prevention
- TEST 9B: Missing Phone Number Handling
- TEST 9C: Invalid Phone Number Handling
- TEST 9D: Lead Source from Tags

## Code Improvements Made

### Lead Source Extraction (Enhanced)
```python
# Now checks multiple sources:
1. webhook_body.get("leadSource")
2. webhook_body.get("lead_source")
3. webhook_body.get("source")
4. contact.get("leadSource")
5. contact.get("lead_source")
6. contact.get("tags") - extracts from tags
```

### Lead Source Normalization
- Maps variations: "google" → "google_ads"
- Maps variations: "facebook" → "facebook_ads"
- Maps variations: "web chat" → "webchat"
- Standardizes all lead sources

### Better Logging
- Logs when lead source is identified
- Logs which source was used (webhook, tag, field)
- Helps with debugging

## Testing Protocol Enhancements

### Added 4 New Test Scenarios:
1. **TEST 9A:** Duplicate Call Prevention
   - Verifies `vapi_called: true` check works
   - Ensures no duplicate calls

2. **TEST 9B:** Missing Phone Number
   - Verifies graceful handling
   - Ensures no crash

3. **TEST 9C:** Invalid Phone Number
   - Verifies validation works
   - Ensures error logged

4. **TEST 9D:** Lead Source from Tags
   - Verifies tag extraction
   - Tests yelp, website, thumbtack tags

### Enhanced Existing Tests:
- TEST 9: Added verification that lead source is saved to GHL custom fields
- TEST 9: Added tag-based lead source testing
- All tests: Added explicit GHL dashboard verification steps

## Verification Checklist

After fixes, verify:

- [ ] Lead source is saved to `contact.lead_source` custom field in GHL
- [ ] Tags are checked for lead source (yelp, website, thumbtack)
- [ ] Duplicate calls are prevented (`vapi_called: true` check works)
- [ ] Missing phone numbers are handled gracefully
- [ ] Invalid phone numbers are validated and rejected
- [ ] All lead sources are normalized correctly

## Next Steps

1. **Deploy the fix** to production
2. **Test each scenario** from TEST 9, 9A, 9B, 9C, 9D
3. **Verify in GHL dashboard** that lead sources are saved
4. **Monitor logs** for lead source identification messages
5. **Check custom fields** in GHL to confirm `lead_source` values

## Expected Behavior After Fix

### For Manual Entry (contact.created):
- If contact has tag "yelp" → `lead_source: yelp`
- If contact has tag "website" → `lead_source: website`
- If contact has tag "thumbtack" → `lead_source: thumbtack`
- Otherwise → `lead_source: inbound` (or not set)

### For Form Submission (form.submitted):
- `lead_source: form` (from webhook or handler)

### For Web Chat (webchat.converted):
- `lead_source: webchat` (from webhook or handler)

### For Ad Leads (google.lead, meta.lead, etc.):
- `lead_source: google_ads` or `meta_ads` or `facebook_ads` (from webhook)

## Testing Commands

```bash
# Test lead source extraction
# 1. Create contact with tag "yelp" in GHL
# 2. Trigger webhook
# 3. Check logs for "Lead source identified: yelp"
# 4. Verify in GHL dashboard: contact.lead_source = "yelp"

# Test duplicate prevention
# 1. Set vapi_called: true in contact custom fields
# 2. Trigger webhook
# 3. Verify no call is made
# 4. Check logs for "Contact already called, skipping"
```

