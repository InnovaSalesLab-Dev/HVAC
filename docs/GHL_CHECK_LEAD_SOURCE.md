# How to Check Lead Source Custom Field in GHL Dashboard

## Quick Steps

### Method 1: View Contact Profile

1. **Go to Contacts**
   - Navigate to **Contacts** in GHL dashboard
   - Search for the contact you want to check

2. **Open Contact Profile**
   - Click on the contact name to open their profile

3. **View Custom Fields**
   - Scroll down to **Custom Fields** section
   - Look for field named: **"Lead Source"** or **"Lead Source (lead_source)"**
   - The value will show: `form`, `webchat`, `google_ads`, `meta_ads`, `yelp`, `website`, `thumbtack`, etc.

### Method 2: Contact List View

1. **Go to Contacts List**
   - Navigate to **Contacts** → **All Contacts**

2. **Add Custom Field Column**
   - Click **Columns** or **View Options**
   - Select **"Lead Source"** custom field to add as a column
   - You'll see lead source for each contact in the list

### Method 3: Filter by Lead Source

1. **Go to Contacts**
   - Navigate to **Contacts**

2. **Use Filter**
   - Click **Filter** button
   - Select **Custom Fields** → **Lead Source**
   - Choose the lead source value (e.g., "yelp", "website")
   - Click **Apply**

3. **View Results**
   - All contacts with that lead source will be shown

## Field Name Variations

The custom field might appear as:
- **"Lead Source"** (display name)
- **"lead_source"** (field key)
- **"contact.lead_source"** (full field key in API)

All refer to the same field.

## Expected Values

| Lead Source | Value in Field |
|-------------|----------------|
| Website form | `form` |
| Web chat | `webchat` |
| Google Ads | `google_ads` |
| Meta/Facebook Ads | `meta_ads` or `facebook_ads` |
| Yelp | `yelp` |
| Website (valleyviewhvac.com) | `website` |
| Thumbtack | `thumbtack` |
| Manual entry | `inbound` or empty |

## Troubleshooting

### If Field is Empty:

1. **Check if field exists:**
   - Go to **Settings** → **Custom Fields**
   - Search for "Lead Source"
   - If missing, it needs to be created

2. **Check webhook logs:**
   - Look for "📋 Lead source identified" in server logs
   - Verify webhook is triggering correctly

3. **Check contact tags:**
   - If lead source should come from tags, verify contact has correct tag
   - Tags: "yelp", "website", "thumbtack", etc.

### If Field Shows Wrong Value:

1. **Check contact tags:**
   - Tags might override webhook source
   - Remove incorrect tags if needed

2. **Check webhook payload:**
   - Verify webhook is sending correct `leadSource` value
   - Check server logs for lead source extraction

## Visual Guide

```
GHL Dashboard → Contacts → [Contact Name]
  ↓
Contact Profile Page
  ↓
Scroll to "Custom Fields" section
  ↓
Find "Lead Source" field
  ↓
Value: yelp | website | form | google_ads | etc.
```

## API Check (Advanced)

If you have API access, you can check via API:

```bash
curl -X GET "https://services.leadconnectorhq.com/contacts/{contactId}?locationId={locationId}" \
  -H "Authorization: Bearer {api_key}" \
  -H "Version: 2021-07-28"
```

Look for:
```json
{
  "contact": {
    "customFields": [
      {
        "key": "contact.lead_source",
        "value": "yelp"
      }
    ]
  }
}
```

