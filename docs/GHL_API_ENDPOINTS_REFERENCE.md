# GHL API Endpoints Reference

Based on official GHL API documentation: https://marketplace.gohighlevel.com/docs/

## Calendar & Events API

### Appointment Management

**Delete/Cancel Appointment:**
- **Endpoint:** `DELETE /calendars/events/:eventId`
- **Method:** DELETE
- **Parameters:** `locationId` (query param)
- **Note:** Uses `eventId`, not `appointmentId`. May need to fetch appointment details first to get `eventId`.

**Get Appointment:**
- **Endpoint:** `GET /calendars/events/appointments/:appointmentId`
- **Method:** GET
- **Parameters:** `locationId` (query param)
- **Returns:** Appointment details including `eventId`

**Get Free Slots:**
- **Endpoint:** `GET /calendars/:calendarId/slots`
- **Method:** GET
- **Parameters:** `startDate`, `endDate`, `timezone`, `userId` (optional)

**Create Calendar:**
- **Endpoint:** `POST /calendars`
- **Method:** POST
- **Body:** Calendar configuration

**Get Calendars:**
- **Endpoint:** `GET /calendars`
- **Method:** GET
- **Parameters:** `locationId` (query param)

## Contacts API

**Get Contact:**
- **Endpoint:** `GET /contacts/:contactId`
- **Method:** GET
- **Parameters:** `locationId` (query param)

**Create Contact:**
- **Endpoint:** `POST /contacts`
- **Method:** POST
- **Body:** Contact data (name, phone, email, address, customFields, etc.)

**Update Contact:**
- **Endpoint:** `PUT /contacts/:contactId`
- **Method:** PUT
- **Body:** Updated contact data

**Upsert Contact:**
- **Endpoint:** `POST /contacts/upsert`
- **Method:** POST
- **Body:** Contact data (creates if doesn't exist, updates if exists)

**Get Contacts:**
- **Endpoint:** `GET /contacts`
- **Method:** GET
- **Parameters:** `locationId`, `limit`, `sortBy` (e.g., `date_added`), etc.
- **Note:** `limit` max is 100, `sortBy` must be `date_added` or `date_updated`, `sortOrder` is NOT allowed

**Search Contacts:**
- **Endpoint:** `POST /contacts/search`
- **Method:** POST
- **Body:** `{ "locationId": "...", "query": "phone:1234567890 email:test@example.com", "pageLimit": 10 }`
- **Note:** Query string must be <= 75 characters

**Get Contact Appointments:**
- **Endpoint:** `GET /contacts/:contactId/appointments`
- **Method:** GET
- **Parameters:** `locationId` (query param)
- **Note:** This is the WORKING endpoint for fetching appointments by contact

**Add Timeline Note:**
- **Endpoint:** `POST /contacts/:contactId/notes`
- **Method:** POST
- **Body:** `{ "body": "note text" }`
- **Parameters:** `locationId` (query param)

## Custom Fields API

**Get Custom Fields:**
- **Endpoint:** `GET /locations/:locationId/customFields`
- **Method:** GET
- **Returns:** List of custom fields

**Create Custom Field:**
- **Endpoint:** `POST /locations/:locationId/customFields`
- **Method:** POST
- **Body:** `{ "name": "Field Name", "dataType": "TEXT|LARGE_TEXT|NUMERICAL|CHECKBOX|SINGLE_OPTIONS|DATE|EMAIL|PHONE", "options": [...] }`
- **Note:** GHL auto-generates `fieldKey` as `contact.{name_lowercase_with_underscores}`

**Update Contact Custom Fields:**
- **Endpoint:** `PUT /contacts/:contactId/custom-fields`
- **Method:** PUT
- **Body:** `{ "locationId": "...", "customFields": [...] }`

## Important Notes

1. **API Version:** GHL is transitioning to API 2.0 (OAuth 2.0). API 1.0 is end-of-support but still works.

2. **Authentication:** Requires Bearer Token in Authorization header.

3. **Location ID:** Most endpoints require `locationId` as query parameter or in body.

4. **Appointment vs Event:** 
   - Appointments are calendar events
   - Use `eventId` for DELETE operations
   - Use `appointmentId` for GET operations
   - May need to fetch appointment to get `eventId`

5. **Rate Limits:** Be aware of API rate limits to avoid throttling.

6. **Error Handling:** 
   - 404 = Resource not found
   - 422 = Validation error (check parameters)
   - 401 = Authentication error

## Current Implementation Status

✅ **Working Endpoints:**
- `GET /contacts/:contactId/appointments` - Fetches appointments by contact (reliable)
- `POST /contacts/search` - Searches contacts
- `POST /contacts` - Creates contacts
- `PUT /contacts/:contactId` - Updates contacts
- `GET /calendars` - Gets calendars
- `POST /contacts/:contactId/notes` - Adds timeline notes

⚠️ **Unreliable Endpoints:**
- Calendar/date-based appointment fetching (returns 404 or empty)
- Direct appointment creation via REST API (use webhooks/automations instead)

🔧 **Recommended Approach:**
- Use webhooks/automations for appointment creation (more reliable)
- Use `GET /contacts/:contactId/appointments` for fetching appointments
- Use `DELETE /calendars/events/:eventId` for cancellation (may need to fetch eventId first)

