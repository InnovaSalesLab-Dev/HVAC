# Complete Workflow Guide - Valley View HVAC

## 🎯 The Complete Flow (How Everything Works)

### **Scenario 1: Website Form Submission (Most Common)**

1. **Customer visits website** → `valleyviewhvac.com`
2. **Fills out contact form** (embedded GHL form)
3. **Form submits** → GHL creates contact automatically
4. **GHL fires TWO events:**
   - `contact.created` (contact was created)
   - `form.submitted` (form was submitted)
5. **Our backend receives webhook** → Checks if already called → Makes ONE outbound call
6. **If call fails** → Sends ONE SMS fallback message

---

## 🔧 Setup Instructions

### **Step 1: Choose ONE Workflow (Prevent Duplicates)**

**IMPORTANT:** You should have ONLY ONE active workflow, not both:

**Option A: Use "Contact Created" Workflow (Recommended)**
- ✅ Catches ALL new contacts (forms, manual entry, imports, etc.)
- ✅ One workflow handles everything
- ✅ Less maintenance

**Option B: Use "Form Submitted" Workflow**
- ✅ Only triggers for form submissions
- ❌ Misses manually entered contacts
- ❌ Requires separate workflow for other lead sources

**RECOMMENDATION: Use "Contact Created" and DELETE/PAUSE "Form Submitted"**

---

### **Step 2: Embed Form on Website**

**Method 1: GHL Hosted Form (Easiest)**
1. Go to `Sites → Forms → [Your Form]`
2. Click **"Share"** or **"Embed"**
3. Copy the **embed code** (iframe or JavaScript)
4. Paste into your website's HTML where you want the form
5. **Done!** Form is live on your site

**Method 2: Custom Form (Advanced)**
- Build custom form on your website
- On submit, POST to GHL API to create contact
- Or use Zapier to connect custom form → GHL

---

### **Step 3: Configure Workflow (Contact Created)**

**Workflow Name:** `Outbound Calls - New Leads`

**Trigger:**
- Type: `Contact Created`
- **NO FILTERS** (we handle filtering in backend)

**Action:**
- Type: `Webhook`
- URL: `https://scott-valley-hvac-api.fly.dev/webhooks/ghl`
- Method: `POST`
- Custom Data:
  - `type` → `contact.created`
  - `locationId` → `NHEXwG3xQVwKMO77jAuB`
  - `contactId` → `{{contact.id}}`

**Publish the workflow**

---

### **Step 4: Test the Flow**

1. **Create test contact manually:**
   - Go to `Contacts → Create Contact`
   - Add name, phone, email
   - Add tag: `website` (to mark as website lead)
   - Save

2. **Check workflow execution:**
   - Go to `Automation → Execution Logs`
   - Find your workflow
   - Should show "Success" status

3. **Check backend logs:**
   - Run: `flyctl logs -a scott-valley-hvac-api`
   - Look for: `📥 Webhook received` and `📞 Found phone number`

4. **Verify call was made:**
   - Check Vapi dashboard for call
   - Check contact custom field `vapi_called` = `true`

---

## 🚫 Fixing Multiple Calls Issue

### **Problem:**
You're getting 2-3 calls for the same contact because:
- Multiple workflows are active (Contact Created + Form Submitted)
- Both fire when form is submitted
- Race condition: both pass `vapi_called` check before either marks it

### **Solution:**

1. **PAUSE or DELETE duplicate workflows:**
   - Keep ONLY "Contact Created" workflow active
   - Pause "Form Submitted" workflow (or delete it)

2. **Backend already has deduplication:**
   - Checks `vapi_called` custom field
   - Skips if already called
   - But needs time to mark as called (race condition)

3. **Improve deduplication (already in code):**
   - Backend checks `vapi_called` BEFORE making call
   - Marks `vapi_called = true` IMMEDIATELY after call starts
   - This prevents duplicates even if multiple webhooks arrive

---

## 📋 Lead Source Tracking

**How backend identifies lead sources:**

1. **Inbound Calls:** `lead_source = "inbound"` (set automatically)
2. **Website Forms:** Tag `website` or custom field `lead_source = "website"`
3. **Facebook Ads:** Tag `facebook` or `lead_source = "facebook_ads"`
4. **Google Ads:** Tag `google` or `lead_source = "google_ads"`
5. **Yelp:** Tag `yelp` or `lead_source = "yelp"`
6. **Thumbtack:** Tag `thumbtack` or `lead_source = "thumbtack"`

**Backend automatically:**
- Skips outbound calls for `lead_source = "inbound"`
- Triggers outbound calls for all other sources
- Sends SMS fallback if call fails (only for outbound leads)

---

## ✅ Checklist

- [ ] Only ONE workflow active (Contact Created)
- [ ] Form embedded on website
- [ ] Workflow webhook URL correct
- [ ] Test with manual contact creation
- [ ] Verify only ONE call per contact
- [ ] Check Execution Logs for errors
- [ ] Verify `vapi_called` field is set after call

---

## 🐛 Troubleshooting

**Multiple calls still happening?**
1. Check how many workflows are active
2. Check Execution Logs - are multiple webhooks firing?
3. Check backend logs - is `vapi_called` check working?
4. Verify contact has `vapi_called = true` after first call

**No calls happening?**
1. Check workflow is Published (not Draft)
2. Check Execution Logs for errors
3. Check backend logs for webhook receipt
4. Verify phone number is valid
5. Check `lead_source` - inbound contacts are skipped

**Form not working?**
1. Verify form is Published
2. Check form has "Add to Contacts" enabled
3. Test form submission manually
4. Check Execution Logs after submission

