---
name: wa-business-automation
description: Automate WhatsApp Business on an Android phone via ADB/UIAutomator with a human-confirmed send flow. Use when the user wants OpenClaw to open WhatsApp Business, find/open a customer chat, draft a message, wait for explicit confirmation like “发送”, send it, and return to the WA main screen. Supports visible-list matching, search-bar lookup, and fuzzy contact matching.
---

# WA Business Automation

Use this skill for deterministic WhatsApp Business messaging on the connected Android device.

## Workflow

1. Ensure the Android phone is connected with ADB and kept unlocked/awake when possible.
2. Use `scripts/wa_business_send_confirmed.py prepare <text> [contact]` to:
   - open WhatsApp Business
   - open the target chat from the visible list or search bar
   - verify the contact by title/fallback descriptors/fuzzy matching
   - type the draft
   - verify the draft by input-text readback or send-mode fallback
3. Stop and ask for explicit confirmation before sending.
4. After the user confirms, run `scripts/wa_business_send_confirmed.py send`.
5. Verify send success and return to the WA main screen.

## Safety rules

- Never send immediately after drafting unless the user explicitly asks to skip confirmation.
- If contact confirmation fails, stop.
- If draft confirmation fails, stop.
- If send-stage confirmation fails, stop.
- Prefer exact contact matches; use fuzzy matching only as a fallback.

## Commands

### Draft in the current open chat

```bash
scripts/wa_business_send_confirmed.py prepare hallo
```

### Draft after opening a target contact

```bash
scripts/wa_business_send_confirmed.py prepare danke bob
```

### Send an already prepared draft

```bash
scripts/wa_business_send_confirmed.py send
```

## Resources

- `scripts/wa_business_send_confirmed.py`: main automation entry point
- `references/runbook.md`: operational notes, known limitations, and validation flow
