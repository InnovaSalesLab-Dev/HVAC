#!/usr/bin/env bash
# Send a test SMS via production API to validate Twilio + send_confirmation.
# Usage: ./scripts/send_test_sms.sh
# Or:   bash scripts/send_test_sms.sh

PROD_URL="https://scott-valley-hvac-api.fly.dev"
PHONE="${1:-+923035699010}"
MESSAGE="${2:-Test SMS from Valley View HVAC - if you received this, SMS is working.}"

echo "=== Test SMS via Prod ==="
echo "URL: $PROD_URL"
echo "To:  $PHONE"
echo ""

# 1) Create contact (so send_confirmation has a contact_id with this phone)
echo "1. Creating contact..."
CREATE_RESP=$(curl -s -X POST "$PROD_URL/functions/create-contact" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test SMS\",\"phone\":\"$PHONE\",\"sms_consent\":true}")

if echo "$CREATE_RESP" | grep -q '"contact_id"'; then
  if command -v jq &>/dev/null; then
    CONTACT_ID=$(echo "$CREATE_RESP" | jq -r '.contact_id')
  else
    CONTACT_ID=$(echo "$CREATE_RESP" | sed -n 's/.*"contact_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  fi
fi

if [ -z "$CONTACT_ID" ]; then
  echo "   Failed to get contact_id. Response: $CREATE_RESP"
  exit 1
fi
echo "   contact_id: $CONTACT_ID"

# 2) Send confirmation SMS
echo ""
echo "2. Sending SMS..."
SEND_RESP=$(curl -s -X POST "$PROD_URL/functions/send-confirmation" \
  -H "Content-Type: application/json" \
  -d "{\"contact_id\":\"$CONTACT_ID\",\"method\":\"sms\",\"message\":\"$MESSAGE\"}")

echo "$SEND_RESP" | grep -q '"success":true' && echo "   SMS sent successfully." || echo "   Response: $SEND_RESP"
echo ""
echo "Check the phone $PHONE for the message."
