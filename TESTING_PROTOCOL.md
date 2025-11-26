# 🧪 Scott Valley HVAC - AI Voice Agent Testing Protocol

**Version:** 3.0  
**Last Updated:** November 2025  
**Project:** AI Voice Automation System

---

## 🎯 Test Scenarios

### TEST 1: Inbound Call - Service/Repair Request

**Objective:** Verify AI handles heating/cooling repair requests correctly

#### Step 1: Initiate Call
- Call the business phone number
- Wait for AI greeting

#### Step 2: Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "Hello, my furnace stopped working" | AI greets warmly, expresses empathy, asks for details | ✅ Empathetic, professional tone |
| "My name is John Smith, phone 503-555-0101" | AI confirms name and phone, asks for email/address | ✅ Captures name and phone correctly |
| "My address is 123 Main St, Salem, OR 97301" | AI verifies service area, asks for SMS consent | ✅ Confirms Salem coverage, asks SMS consent |
| "Yes, I'd like text confirmations" | AI acknowledges, checks calendar availability | ✅ SMS consent captured |
| "When can you come out?" | AI offers available appointment times (next 7-14 days) | ✅ Shows available slots, correct calendar |
| "Tomorrow at 2 PM works" | AI books appointment, confirms details | ✅ Appointment booked, details confirmed |
| "Yes, send me a confirmation" | AI sends SMS confirmation | ✅ SMS sent successfully |

#### Step 3: Verification Checklist

- [ ] Contact information saved in CRM: name, phone, email, address, ZIP code
- [ ] Appointment booked in service calendar
- [ ] Customer agreed to receive text confirmations
- [ ] Call summary saved in customer record
- [ ] Text confirmation message received by customer
- [ ] Customer record shows call type and outcome

#### Pass Criteria
✅ **PASS** if all 7 questions answered correctly AND all verification steps pass  
❌ **FAIL** if any question answered incorrectly OR any verification fails

---

### TEST 2: Inbound Call - Installation/Estimate Request

**Objective:** Verify AI handles installation requests and pricing questions correctly

#### Step 1: Initiate Call
- Call the business phone number

#### Step 2: Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "I want to replace my old AC system" | AI asks for details, explains on-site assessment needed | ✅ Explains process, doesn't quote over phone |
| "My name is Sarah Johnson, phone 503-555-0102" | AI confirms, asks for address | ✅ Captures contact info |
| "My address is 456 Oak Ave, Keizer, OR 97303" | AI verifies service area (Keizer covered) | ✅ Confirms Keizer coverage |
| "How much will it cost?" | AI explains pricing ranges ($6,200-$9,400 for AC), emphasizes on-site assessment | ✅ Gives range, pushes for on-site |
| "Can you just give me a quote over the phone?" | AI politely declines, explains why on-site is essential | ✅ Pushes back professionally |
| "When can someone come for an estimate?" | AI checks **Proposal** calendar, offers times | ✅ Uses Proposal calendar (not Diagnostic) |
| "Next Tuesday at 10 AM works" | AI books appointment in Proposal calendar | ✅ Appointment in correct calendar |

#### Step 3: Verification Checklist

- [ ] Contact information saved with all details
- [ ] Appointment booked in estimate/consultation calendar (NOT service calendar)
- [ ] AI correctly identified this as an installation/estimate request
- [ ] AI declined to give exact quote over phone
- [ ] Call summary includes discussion about pricing and on-site assessment

#### Pass Criteria
✅ **PASS** if all 7 questions answered correctly AND appointment in Proposal calendar  
❌ **FAIL** if wrong calendar used OR AI gives exact phone quote

---

### TEST 3: Inbound Call - Emergency Situation

**Objective:** Verify AI recognizes and prioritizes emergencies

#### Step 1: Initiate Call

#### Step 2: Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "My heat is out and I have a 2-month-old baby, it's freezing" | AI recognizes emergency, expresses urgency, prioritizes | ✅ Recognizes health threat, urgent tone |
| "This is an emergency, I need someone today" | AI offers same-day or next available appointment | ✅ Offers immediate availability |
| "My name is Emergency Test, phone 503-555-0104" | AI quickly collects info | ✅ Efficient data collection |
| "My address is 321 Elm St, Salem, OR 97301" | AI confirms, books urgent appointment | ✅ Books with urgency level |

#### Step 3: Verification Checklist

- [ ] Appointment marked as urgent/emergency
- [ ] Appointment scheduled same-day or next available slot
- [ ] Call summary notes health threat (baby mentioned)
- [ ] Customer record reflects high priority

#### Pass Criteria
✅ **PASS** if emergency recognized AND same-day/next-day appointment offered  
❌ **FAIL** if treated as regular appointment OR no urgency noted

---

### TEST 4: Inbound Call - Warm Transfer

**Objective:** Verify AI can transfer calls to human staff

#### Step 1: Initiate Call

#### Step 2: Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "I'd like to speak with the owner about pricing" | AI offers warm transfer to Scott | ✅ Offers transfer appropriately |
| "Yes, please transfer me" | AI initiates transfer to 971-712-6763 | ✅ Transfer initiated correctly |
| [After transfer] | Staff receives call with context | ✅ Call context maintained |

#### Step 3: Verification Checklist

- [ ] AI offered to transfer call
- [ ] Call successfully transferred to staff member (971-712-6763)
- [ ] Transfer recorded in customer record
- [ ] Call summary notes that transfer occurred

#### Pass Criteria
✅ **PASS** if transfer initiated AND staff receives call  
❌ **FAIL** if transfer fails OR wrong number called

---

### TEST 5: Knowledge Base - Service Area Questions

**Objective:** Verify AI answers service area questions accurately with specific town names

#### Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "Do you service Salem?" | Yes, full Salem coverage including West Salem (all zip codes) | ✅ Confirms full Salem coverage |
| "Do you work in Keizer?" | Yes, Keizer (North Salem) is covered | ✅ Confirms Keizer coverage |
| "Do you service West Salem?" | Yes, full Salem coverage including West Salem | ✅ Confirms West Salem |
| "Do you service Independence?" | Yes, Independence is in our service area | ✅ Confirms West area coverage |
| "Do you service Monmouth or Dallas?" | Yes, both Monmouth and Dallas are covered | ✅ Confirms multiple west towns |
| "Do you work in McMinnville?" | Yes, McMinnville is covered | ✅ Confirms north area |
| "Do you service Newberg or Woodburn?" | Yes, both Newberg and Woodburn are covered | ✅ Confirms north towns |
| "Do you work in Silverton or Stayton?" | Yes, both Silverton and Stayton are covered | ✅ Confirms east area |
| "Do you service Portland?" | Extended area 35-42 miles north, case-by-case basis (we keep Portland due to 1,400-1,800 accounts from 2019) | ✅ Explains extended area with context |
| "Do you work in Eugene or Corvallis?" | Case-by-case based on project size and commute costs | ✅ Mentions case-by-case with project size |
| "Do you service Albany?" | Case-by-case, depends on project size | ✅ Mentions case-by-case |
| "What's your service radius?" | 20-25 mile radius from Salem, but extended to 35-42 miles north for Portland area | ✅ States primary and extended radius |

#### Pass Criteria
✅ **PASS** if 10/12 questions answered correctly  
❌ **FAIL** if 3+ questions answered incorrectly

---

### TEST 6: Knowledge Base - Service Types & Equipment

**Objective:** Verify AI knows exactly what services are offered and what's NOT offered

#### Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "Do you fix furnaces?" | Yes, we service all residential whole home ducted, split home ducted, and ductless systems | ✅ Confirms residential furnace service |
| "Do you install ductless systems?" | Yes, we install ductless systems for residential | ✅ Confirms ductless |
| "Do you work on boilers?" | No, we don't service boilers, but we can fit ducted/ductless systems and abandon or sub out boiler removal | ✅ Correctly says no, explains alternative |
| "Do you service geothermal systems?" | No, we don't service geothermal systems | ✅ Correctly says no |
| "Do you work on radiant systems?" | No, we don't service radiant systems | ✅ Correctly says no |
| "Do you service hydro or steam systems?" | No, we don't service hydro or steam systems | ✅ Correctly says no |
| "Do you do commercial work?" | Yes, we service commercial wall hung or roof mounted packaged unit air controlled systems | ✅ Confirms commercial with specific types |
| "What types of residential systems do you work on?" | Whole home ducted, split home ducted, and ductless systems | ✅ Lists all residential types |
| "Can you install a new system if I have a boiler?" | Yes, we can fit a ducted or ductless system and sub out the boiler removal | ✅ Explains alternative service |

#### Pass Criteria
✅ **PASS** if 8/9 questions answered correctly  
❌ **FAIL** if 2+ questions answered incorrectly

---

### TEST 7: Knowledge Base - Pricing & Hours

**Objective:** Verify AI provides accurate pricing, hours, and appointment duration information

#### Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "How much is a diagnostic?" | $190 residential, $240 commercial (prices may be reduced to stay competitive) | ✅ Gives correct base prices with note about potential reduction |
| "What are your hours?" | 24/7 AI for calls, 7 AM-8:30 PM for human-answered phones, 8 AM-4:30 PM for field/site work | ✅ States all three timeframes accurately |
| "Do you work weekends?" | Case-by-case for emergencies affecting health - typically reserved for hot/cold storms, people with infants, and senior citizens | ✅ Explains weekend policy with health threat priority |
| "How much for emergency or weekend service?" | Case-by-case, no static pricing - determined by company operational costs, customer circumstances, and weather conditions | ✅ Explains case-by-case with factors |
| "What's the price range for a new furnace?" | $4,900-$7,900 for base level furnace or air handler (rough estimate, on-site assessment needed) | ✅ Gives correct range, emphasizes on-site |
| "How much for a new AC or heat pump?" | $6,200-$9,400 (rough estimate, on-site assessment needed) | ✅ Gives correct range |
| "What's the price for a full system replacement?" | $9,800-$17,500+ depending on scope and equipment size (on-site assessment required) | ✅ Gives correct range |
| "How long is a diagnostic appointment?" | 20-30 minutes actual work, scheduled for up to 1 hour block | ✅ States duration correctly |
| "How long is an estimate visit?" | 20-50 minutes, varies by project scope | ✅ States duration range |
| "How long does an installation take?" | 2.5-4 hours for simple, up to 2-3 full days for complex systems | ✅ States duration range |
| "What about out of service area pricing?" | Additional $50-$110 based on distance, road type, and parts availability | ✅ States out-of-area pricing range |

#### Pass Criteria
✅ **PASS** if 9/11 questions answered correctly  
❌ **FAIL** if 3+ questions answered incorrectly

---

### TEST 8: Knowledge Base - Discounts & Brand Voice

**Objective:** Verify AI knows all discount programs and uses correct brand voice

#### Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "Do you offer veteran discounts?" | Yes, ~10% Veteran Appreciation program (discount applies to products/materials, may not fully apply to labor) | ✅ Confirms veteran discount with details |
| "Do seniors get a discount?" | Yes, ~10% Senior Community Member savings | ✅ Confirms senior discount |
| "Do you have educator discounts?" | Yes, ~10% Educator Thanks program | ✅ Confirms educator discount |
| "Do first responders get a discount?" | Yes, ~10% First Responder Recognition program | ✅ Confirms first responder discount |
| "Can I stack multiple discounts?" | Yes, combined stacking: 2 tiers = ~14%, 3 tiers = up to 16% maximum savings | ✅ Explains stacking policy |
| "What makes you different?" | Uses words: consultation, complimentary, inclusive, thorough, diligent, trusted, proposal, quality | ✅ Uses brand voice words |
| "Are your services free?" | Avoids word "free", uses "complimentary" or "inclusive" | ✅ Avoids prohibited words |
| "Are your prices cheap?" | Avoids "cheap", uses "quality", "trusted", "professional" | ✅ Avoids prohibited words |
| "Can you just give me a quote over the phone?" | AI pushes back, explains why on-site assessment is essential for accurate pricing | ✅ Pushes back professionally |
| "Can you install parts I buy separately?" | AI avoids this, explains why professional installation is recommended | ✅ Handles appropriately |

#### Pass Criteria
✅ **PASS** if 8/10 questions answered correctly AND avoids prohibited words  
❌ **FAIL** if uses "free", "cheap", or "low cost" inappropriately OR doesn't push back on phone quotes

---

### TEST 9: Outbound Call - New Lead from Various Sources

**Objective:** Verify outbound calls are made automatically for new leads from all sources

#### Step 1: Create Test Leads from Multiple Sources
- Create contact manually in CRM (simulates manual entry)
- Submit contact via website form
- Convert contact via web chat
- Submit contact via Google or Facebook ad
- Create contact with "yelp" tag
- Create contact with "website" tag

#### Step 2: Expected Behavior by Lead Source

| Lead Source | Expected Behavior | Pass Criteria |
|-------------|-------------------|---------------|
| Manual Entry | Outbound call within 1 minute | ✅ Call initiated |
| Form Submission | Outbound call triggered | ✅ Call initiated |
| Web Chat | Outbound call triggered, lead source recorded | ✅ Call + source recorded |
| Google Ad | Outbound call triggered, lead source recorded | ✅ Call + source recorded |
| Meta/Facebook Ad | Outbound call triggered, lead source recorded | ✅ Call + source recorded |
| Website (with tag) | Outbound call triggered, source identified from tag | ✅ Call + source from tag |
| Yelp (with tag) | Outbound call triggered, source identified from tag | ✅ Call + source from tag |
| Thumbtack (with tag) | Outbound call triggered, source identified from tag | ✅ Call + source from tag |

#### Step 3: Test Questions During Call

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| AI greeting | "Hi [Name], this is [AI name] from Scott Valley HVAC. I'm calling because you recently requested information..." | ✅ Professional, mentions inquiry |
| "Is now a good time?" | AI respects if busy, offers callback | ✅ Handles busy appropriately |
| Lead qualification | AI asks about HVAC needs (heating, cooling, repair, installation) | ✅ Qualifies lead |
| Appointment offer | AI offers to schedule if interested | ✅ Offers appointment |

#### Step 4: Verification Checklist

- [ ] System received new lead notification for each source
- [ ] Outbound call initiated automatically within 1 minute
- [ ] Contact record shows that call was attempted
- [ ] Lead source correctly recorded in customer record:
  - [ ] Form submission shows as "form" source
  - [ ] Web chat shows as "webchat" source
  - [ ] Google ad shows as "google_ads" source
  - [ ] Meta/Facebook ad shows as "meta_ads" or "facebook_ads" source
  - [ ] Website tag shows as "website" source
  - [ ] Yelp tag shows as "yelp" source
  - [ ] Thumbtack tag shows as "thumbtack" source
- [ ] Call ID recorded in customer record
- [ ] Call activity logged in customer timeline
- [ ] If call not answered, text message sent automatically (after 45 seconds)

#### Pass Criteria
✅ **PASS** if call initiated for all sources AND lead source recorded correctly in customer record  
❌ **FAIL** if any source doesn't trigger call OR source not recorded

---

### TEST 9A: Duplicate Call Prevention

**Objective:** Verify system prevents duplicate calls to same contact

#### Step 1: Setup
- Create contact in CRM
- Mark contact as "already called" in system
- Create another lead entry for same contact

#### Step 2: Expected Behavior

| Checkpoint | Expected | Pass Criteria |
|------------|----------|---------------|
| System receives lead | Within 5 seconds | ✅ Lead received |
| System checks history | System checks if contact was already called | ✅ History checked |
| Call skipped | No outbound call initiated | ✅ Call NOT made |
| System response | System recognizes duplicate and skips | ✅ Handled correctly |

#### Pass Criteria
✅ **PASS** if call is NOT initiated when contact was already called  
❌ **FAIL** if duplicate call is made

---

### TEST 9B: Missing Phone Number Handling

**Objective:** Verify graceful handling when contact has no phone number

#### Step 1: Setup
- Create contact in CRM WITHOUT phone number
- System attempts to process lead

#### Step 2: Expected Behavior

| Checkpoint | Expected | Pass Criteria |
|------------|----------|---------------|
| System receives lead | Within 5 seconds | ✅ Lead received |
| Phone check | System attempts to find phone number | ✅ Phone check performed |
| Call skipped | No outbound call initiated | ✅ Call NOT made |
| System response | System handles missing phone gracefully | ✅ Error handled properly |
| System continues | System continues processing other leads | ✅ No system errors |

#### Pass Criteria
✅ **PASS** if call is NOT initiated AND error logged gracefully  
❌ **FAIL** if system crashes OR call attempted without phone

---

### TEST 9C: Invalid Phone Number Handling

**Objective:** Verify validation works for invalid phone formats

#### Step 1: Setup
- Create contact with invalid phone: "123" or "abc"
- System attempts to process lead

#### Step 2: Expected Behavior

| Checkpoint | Expected | Pass Criteria |
|------------|----------|---------------|
| System receives lead | Within 5 seconds | ✅ Lead received |
| Phone validation | System validates phone format | ✅ Validation performed |
| Call skipped | No outbound call initiated | ✅ Call NOT made |
| System response | System recognizes invalid format | ✅ Error handled properly |
| System continues | System continues processing other leads | ✅ No system errors |

#### Pass Criteria
✅ **PASS** if call is NOT initiated AND validation error logged  
❌ **FAIL** if invalid phone accepted OR system crashes

---

### TEST 9D: Lead Source Identification from Tags

**Objective:** Verify lead source is identified from contact tags

#### Step 1: Setup
- Create contact in CRM with tag "yelp"
- System processes lead

#### Step 2: Expected Behavior

| Checkpoint | Expected | Pass Criteria |
|------------|----------|---------------|
| System receives lead | Within 5 seconds | ✅ Lead received |
| Tag check | System reads contact tags | ✅ Tags accessed |
| Lead source identified | Source identified as "yelp" | ✅ Source from tag |
| Call initiated | Outbound call made | ✅ Call initiated |
| Lead source saved | Source "yelp" saved to customer record | ✅ Saved to CRM |

#### Step 3: Repeat for Other Tags
- Test with tag "website" → should identify as "website" source
- Test with tag "thumbtack" → should identify as "thumbtack" source
- Test with tag "google" → should identify as "google_ads" source

#### Pass Criteria
✅ **PASS** if lead source identified from tags AND saved to customer record  
❌ **FAIL** if tag not detected OR source not saved

---

### TEST 10: SMS Fallback - Unanswered Call

**Objective:** Verify SMS sent automatically when call not answered

#### Step 1: Setup
- Create lead with valid phone number
- Ensure phone won't answer (or let it ring out)

#### Step 2: Expected Behavior

| Checkpoint | Expected | Pass Criteria |
|------------|----------|---------------|
| Call attempted | Within 1 minute of lead creation | ✅ Call initiated |
| Call status check | After 45 seconds | ✅ System checks status |
| Text sent | If call failed/no answer | ✅ Text sent automatically |
| Text content | Personalized with first name, company info | ✅ Professional message |
| Record updated | System records that text was sent, date, reason | ✅ Record updated |

#### Step 3: Verification Checklist

- [ ] Call attempted
- [ ] Call status detected as failed/no-answer
- [ ] Text message sent automatically (if customer consented)
- [ ] Text includes: "Hi [Name], this is Scott Valley HVAC..."
- [ ] Customer record shows: text sent, date, reason

#### Pass Criteria
✅ **PASS** if text sent automatically after call failure AND record updated  
❌ **FAIL** if text not sent OR consent not checked

---

### TEST 11: Calendar Availability Check

**Objective:** Verify AI checks calendar correctly and uses correct appointment types

#### Step 1: Initiate Call

#### Step 2: Test Questions & Expected Answers

| Question | Expected Answer | Pass Criteria |
|----------|----------------|---------------|
| "When are you available?" | AI checks business hours first, then calendar | ✅ Checks business hours tool first |
| "Can I schedule for tomorrow?" | AI checks calendar, shows available slots (8 AM - 4:30 PM) | ✅ Shows actual availability |
| "What times do you have next week?" | AI shows multiple available time slots | ✅ Shows multiple options |
| "I need a repair appointment" | AI uses Diagnostic calendar, schedules 60-minute block | ✅ Correct calendar, correct duration |
| "I need an estimate" | AI uses Proposal calendar, schedules 30-60 minute block | ✅ Correct calendar, correct duration |
| "I need maintenance service" | AI uses appropriate calendar (Diagnostic or Maintenance) | ✅ Correct calendar for maintenance |
| "I need an installation" | AI uses Proposal calendar for consultation | ✅ Correct calendar for installation |
| "Can I schedule for Saturday?" | AI explains weekend policy (case-by-case for emergencies) | ✅ Handles weekend request appropriately |

#### Step 3: Verification Checklist

- [ ] AI checks business hours before showing availability
- [ ] Correct calendar type selected:
  - [ ] Service calendar for repairs/service calls
  - [ ] Estimate calendar for estimates/installations
  - [ ] Maintenance calendar for maintenance (if exists)
- [ ] Available slots shown (8 AM - 4:30 PM, Monday-Friday)
- [ ] No appointments offered outside business hours
- [ ] Appointment duration appropriate:
  - [ ] 60 minutes for service/diagnostic
  - [ ] 30-60 minutes for estimates

#### Pass Criteria
✅ **PASS** if business hours checked first AND correct calendar/duration used  
❌ **FAIL** if wrong calendar OR appointments outside hours OR wrong duration

---

### TEST 12: Data Capture Accuracy

**Objective:** Verify all contact information captured correctly

#### Step 1: Complete Full Call
- Provide: name, phone, email, address, ZIP, SMS consent

#### Step 2: Verification Checklist

| Field | Test Value | Captured? | Format Correct? |
|-------|------------|-----------|----------------|
| Full Name | "John Smith" | ⬜ | ⬜ |
| Phone | "+15035550101" | ⬜ | E.164 format ⬜ |
| Email | "john@test.com" | ⬜ | Valid format ⬜ |
| Address | "123 Main St, Salem, OR 97301" | ⬜ | Complete ⬜ |
| ZIP Code | "97301" | ⬜ | Extracted ⬜ |
| SMS Consent | `true` | ⬜ | Boolean ⬜ |

#### Step 3: CRM Verification
- [ ] Contact created in CRM
- [ ] All fields populated correctly
- [ ] Phone number formatted correctly
- [ ] Email address valid
- [ ] ZIP code extracted from address

#### Pass Criteria
✅ **PASS** if all 6 fields captured correctly AND format correct  
❌ **FAIL** if any field missing OR format incorrect

---

### TEST 13: Customer Record Data Population

**Objective:** Verify all customer information saved correctly after call

#### Verification Checklist

| Information Type | Expected Value | Saved? | Correct? |
|-----------------|----------------|--------|----------|
| Call Summary | AI-generated summary of conversation | ⬜ | ⬜ |
| Call Recording | Link to call recording/transcript | ⬜ | ⬜ |
| Text Consent | Yes or No | ⬜ | ⬜ |
| Lead Quality | Quality score (0-100) | ⬜ | ⬜ |
| Equipment Type | Equipment mentioned during call | ⬜ | ⬜ |
| Call Duration | Length of call | ⬜ | ⬜ |
| Call Type | Service, installation, estimate, etc. | ⬜ | ⬜ |
| Call Outcome | Booked, transferred, no booking | ⬜ | ⬜ |
| Outbound Call Flag | Marked if outbound call was made | ⬜ | ⬜ |
| Call ID | Unique call identifier | ⬜ | ⬜ |
| Lead Source | Where lead came from (form, ad, etc.) | ⬜ | ⬜ |
| Text Fallback Sent | Yes if text was sent | ⬜ | ⬜ |
| Text Fallback Date | Date text was sent | ⬜ | ⬜ |
| Text Fallback Reason | Why text was sent | ⬜ | ⬜ |

#### Pass Criteria
✅ **PASS** if 12/14 data points saved correctly  
❌ **FAIL** if 3+ data points missing or incorrect

---

### TEST 14: Appointment Booking Accuracy

**Objective:** Verify appointments booked correctly in GHL

#### Step 1: Book Appointment via Call
- Complete call and book appointment

#### Step 2: Verification Checklist

- [ ] Appointment appears in calendar
- [ ] Correct calendar type used (Service or Estimate)
- [ ] Date and time correct
- [ ] Customer linked to appointment
- [ ] Service type correct
- [ ] Urgency level set (if emergency)
- [ ] Notes included (if customer provided details)
- [ ] Duration appropriate (60 min for service, 30-60 min for estimate)

#### Pass Criteria
✅ **PASS** if appointment appears in calendar AND all details correct  
❌ **FAIL** if appointment missing OR wrong calendar/details

---

### TEST 15: Error Handling - Invalid Phone Number

**Objective:** Verify graceful error handling

#### Step 1: Test Invalid Inputs

| Input | Expected Behavior | Pass Criteria |
|-------|-------------------|---------------|
| Invalid phone: "123" | AI asks for correct phone number | ✅ Error handled gracefully |
| Invalid email: "notanemail" | AI asks for valid email | ✅ Validation works |
| Out of service area: "Portland, OR" | AI explains extended area policy | ✅ Handles gracefully |
| No calendar availability | AI offers extended dates or callback | ✅ Offers alternatives |

#### Pass Criteria
✅ **PASS** if all errors handled gracefully AND no system crash  
❌ **FAIL** if system crashes OR unhelpful error message

---

### TEST 16: System Integration - Lead Processing

**Objective:** Verify system receives and processes new leads correctly

#### Step 1: Create Test Lead
- Create a new contact through any channel (form, chat, manual entry, etc.)

#### Step 2: Verification Checklist

- [ ] System received new lead notification
- [ ] Lead information processed correctly
- [ ] Lead type identified correctly
- [ ] Contact information extracted
- [ ] Location verified
- [ ] Appropriate action taken (call initiated, etc.)

#### Pass Criteria
✅ **PASS** if lead received AND processed correctly  
❌ **FAIL** if lead not processed OR action not taken

---

### TEST 17: Performance - Call Response Time

**Objective:** Verify system responds quickly

#### Metrics to Check

| Metric | Target | Actual | Pass Criteria |
|--------|--------|--------|---------------|
| Time to answer | < 3 seconds | ⬜ | ✅ |
| System response time | < 2 seconds | ⬜ | ✅ |
| Database response | < 1 second | ⬜ | ✅ |
| Total call setup | < 5 seconds | ⬜ | ✅ |

#### Pass Criteria
✅ **PASS** if all metrics within targets  
❌ **FAIL** if any metric exceeds target by 50%+

---

## 📊 Test Execution Summary

### Test Run Log

**Date:** _______________  
**Tester:** _______________  
**Environment:** Production / Staging / Development

### Results

| Test ID | Test Name | Questions | Pass Criteria | Status | Notes |
|---------|-----------|-----------|---------------|--------|-------|
| TEST 1 | Inbound - Service/Repair | 7 | All 7 correct + verification | ⬜ | |
| TEST 2 | Inbound - Installation | 7 | All 7 correct + Proposal calendar | ⬜ | |
| TEST 3 | Inbound - Emergency | 4 | Emergency recognized + same-day | ⬜ | |
| TEST 4 | Warm Transfer | 6 | Transfer to correct staff member | ⬜ | |
| TEST 5 | Knowledge - Service Area | 12 | 10/12 correct | ⬜ | |
| TEST 6 | Knowledge - Service Types | 9 | 8/9 correct | ⬜ | |
| TEST 7 | Knowledge - Pricing/Hours | 11 | 9/11 correct | ⬜ | |
| TEST 8 | Knowledge - Discounts | 10 | 8/10 correct + no prohibited words | ⬜ | |
| TEST 9 | Outbound - New Lead | Multiple sources | All sources trigger + tagged | ⬜ | |
| TEST 9A | Duplicate Call Prevention | 1 scenario | Call skipped if already called | ⬜ | **NEW** |
| TEST 9B | Missing Phone Handling | 1 scenario | Graceful skip, no crash | ⬜ | **NEW** |
| TEST 9C | Invalid Phone Handling | 1 scenario | Validation error logged | ⬜ | **NEW** |
| TEST 9D | Lead Source from Tags | 4 tags | Source extracted from tags | ⬜ | **NEW** |
| TEST 10 | SMS Fallback | Auto-trigger | SMS sent after call failure | ⬜ | |
| TEST 11 | Calendar Availability | 8 | Business hours + correct calendar | ⬜ | |
| TEST 12 | Data Capture | 6 fields | All 6 fields correct format | ⬜ | |
| TEST 13 | Custom Fields | 14 fields | 12/14 populated | ⬜ | |
| TEST 14 | Appointment Booking | Full booking | Appears in GHL + correct details | ⬜ | |
| TEST 15 | Error Handling | 4 scenarios | All handled gracefully | ⬜ | |
| TEST 16 | Webhook Integration | Multiple events | All events processed | ⬜ | |
| TEST 17 | Performance | 4 metrics | All within targets | ⬜ | |

### Summary

- **Total Tests:** 21 (was 17, added 4 new lead handling tests)
- **Total Questions:** 120+
- **Passed:** ⬜
- **Failed:** ⬜
- **Pass Rate:** ⬜%

### Recent Improvements

✅ **Improved:** Lead source identification from all sources  
✅ **Improved:** Lead source identification from contact tags  
✅ **Added:** Duplicate call prevention testing  
✅ **Added:** Missing/invalid phone number handling tests  
✅ **Added:** Lead source tracking verification

### Issues Found

| Issue | Test ID | Severity | Description | Resolution |
|-------|---------|----------|-------------|------------|
| | | | | |

### Sign-Off

**Tested By:** _______________  
**Date:** _______________  
**Approved By:** _______________  
**Date:** _______________

---

**End of Testing Protocol**
