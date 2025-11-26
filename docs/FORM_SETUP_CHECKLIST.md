# Form Setup Checklist - GoHighLevel

## ✅ Required Form Fields

Your form should have these fields (you already have most):
- ✅ **First Name** (required)
- ✅ **Last Name** (required)
- ✅ **Phone** (required) - You have this marked with *
- ✅ **Email** (required) - You have this marked with *
- ✅ **Address** fields (optional but recommended)

**Your form looks good!** All required fields are present.

---

## 🔧 Critical Settings to Configure

### **Step 1: Go to "Settings" Tab**

1. Click **"Settings"** tab at the top of your form
2. Configure these settings:

**Form Settings:**
- ✅ **"Add to Contacts"** - MUST be enabled (this creates the contact in GHL)
- ✅ **"Show on Mobile"** - Enable for mobile users
- ✅ **"Show Thank You Message"** - Enable
- ✅ **Thank You Message:** *"Thank you! We'll call you shortly."*

**On Submit Actions:**
- ✅ **"Add to Contacts"** - MUST be enabled
- ✅ **"Add Tag: website"** - Add this tag to mark as website lead
- ✅ **"Set Custom Field: lead_source = website"** - If available, set this custom field

---

### **Step 2: Configure Webhook (CRITICAL)**

**Option A: Use Workflow (Recommended - Already Set Up)**
- If you have "Contact Created" workflow active, it will automatically trigger
- No additional webhook needed in form settings
- **Just make sure "Add to Contacts" is enabled**

**Option B: Add Webhook Directly to Form**
1. In form **"Settings"** → **"On Submit Actions"**
2. Click **"Add Action"** → **"Webhook"**
3. Configure:
   - **URL:** `https://scott-valley-hvac-api.fly.dev/webhooks/ghl`
   - **Method:** `POST`
   - **Custom Data:**
     - `type` → `form.submitted`
     - `locationId` → `NHEXwG3xQVwKMO77jAuB`
     - `contactId` → `{{contact.id}}`

**RECOMMENDATION:** Use Option A (workflow) - it's already set up and prevents duplicates.

---

### **Step 3: SMS Consent Checkbox**

Your form has consent checkboxes. Make sure:

1. **Transactional Messages Checkbox:**
   - When checked → Sets `sms_consent = true` in GHL
   - This allows appointment confirmations and service messages

2. **Marketing Checkbox (Optional):**
   - This is for promotional messages
   - Not required for basic functionality

**To connect checkbox to GHL:**
- In form **"Settings"** → **"Field Mapping"**
- Map the consent checkbox to custom field: `sms_consent`
- Or use workflow to set `sms_consent = true` when form is submitted

---

## 📋 Complete Checklist

### **Form Fields:**
- [x] First Name (required)
- [x] Last Name (required)
- [x] Phone (required) ✅
- [x] Email (required) ✅
- [x] Address fields ✅

### **Form Settings:**
- [ ] "Add to Contacts" enabled
- [ ] "Show on Mobile" enabled
- [ ] "Show Thank You Message" enabled
- [ ] Thank you message set

### **On Submit Actions:**
- [ ] "Add to Contacts" enabled
- [ ] "Add Tag: website" configured
- [ ] SMS consent checkbox mapped to `sms_consent` custom field

### **Workflow (Check This):**
- [ ] "Contact Created" workflow is **Published** (not Draft)
- [ ] Only ONE "Contact Created" workflow is active
- [ ] "Form Submitted" workflow is **Paused** or **Deleted** (prevents duplicates)

---

## 🧪 Testing

1. **Submit test form:**
   - Fill out form with test data
   - Use your own phone number for testing
   - Click "Submit"

2. **Check GoHighLevel:**
   - Go to **Contacts** → Find the test contact
   - Verify contact was created
   - Check contact has tag: **"website"**
   - Check custom field: `lead_source = "website"` (if set)

3. **Check Workflow Execution:**
   - Go to **Automation → Execution Logs**
   - Find "Contact Created" workflow
   - Should show "Success" status

4. **Verify Call:**
   - You should receive an outbound call within 30 seconds
   - Check contact custom field: `vapi_called = "true"` after call

---

## ⚠️ Important Notes

1. **Only ONE workflow should trigger:**
   - Use "Contact Created" workflow (recommended)
   - OR use "Form Submitted" workflow
   - **NOT BOTH** - this causes duplicate calls

2. **SMS Consent:**
   - If consent checkbox is checked → `sms_consent = true`
   - If not checked → `sms_consent = false` (no SMS will be sent)
   - For transactional messages (appointment confirmations), consent is usually required

3. **Lead Source Tagging:**
   - Website forms → Tag: `website`
   - This helps identify where the lead came from
   - Backend uses this to determine if outbound call should be made

---

## 🚨 Troubleshooting

**Form submits but no call:**
- Check "Add to Contacts" is enabled
- Check workflow is Published (not Draft)
- Check Execution Logs for errors
- Verify contact was created in GHL

**Getting duplicate calls:**
- Check only ONE workflow is active
- Pause "Form Submitted" if "Contact Created" is active
- Check backend logs: `flyctl logs -a scott-valley-hvac-api`

**SMS not working:**
- Verify consent checkbox is mapped to `sms_consent` field
- Check contact has `sms_consent = true` in custom fields
- Verify Twilio credentials are configured

