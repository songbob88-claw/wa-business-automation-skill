# WA Business Android Automation Runbook

## What works

- Launch WhatsApp Business (`com.whatsapp.w4b`)
- Open a visible chat from the main list
- Use the search bar to find a chat
- Fuzzy-match contact names
- Draft a message
- Require human confirmation before sending
- Send the message and return to the main screen

## Confirmation model

### Contact confirmation

Primary:
- `conversation_contact_name`

Fallbacks:
- title/content description
- contact photo/content description
- chat avatar/content description
- fuzzy similarity against target contact name

### Draft confirmation

Primary:
- input text readback from `entry`

Fallbacks:
- detect send-mode UI instead of pure voice-note mode
- refocus the input field and retry several times

### Send confirmation

Primary:
- message text visible in chat history

Fallback:
- entry cleared while still inside the chat UI

## Known limitations

- MIUI/AOD/lockscreen can interfere with UI dumps
- XML readback can be flaky even when the UI action succeeded
- Fuzzy contact matching should remain conservative
- Best reliability comes from keeping the phone unlocked and the screen on
