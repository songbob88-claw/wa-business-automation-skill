# WA Business Automation Skill for OpenClaw

A public OpenClaw skill for automating **WhatsApp Business** on an Android phone through **ADB + UIAutomator** with a **human-confirmed send flow**.

## What it does

This skill packages the WhatsApp Business workflow we validated on Android:

- launch WhatsApp Business
- open a customer chat from the visible list or through the search bar
- support fuzzy contact matching
- draft a message first
- require explicit human confirmation before sending
- send the message
- return to the WhatsApp Business main screen

## Safety model

The workflow is intentionally conservative.

It tries to avoid accidental sends by using:

- contact confirmation
- fallback contact confirmation
- draft confirmation
- send-stage confirmation
- return-to-main-screen cleanup

If confirmation is not good enough, the script stops instead of sending.

## Repository contents

- `skill/` – OpenClaw skill folder
- `dist/wa-business-automation.skill` – packaged distributable skill artifact
- `examples/` – optional local examples or notes (if added later)

## Skill usage

### Prepare a draft in the current open chat

```bash
scripts/wa_business_send_confirmed.py prepare hallo
```

### Open a target contact and prepare a draft

```bash
scripts/wa_business_send_confirmed.py prepare danke bob
```

### Send the prepared draft after explicit confirmation

```bash
scripts/wa_business_send_confirmed.py send
```

## Requirements

- Android phone with WhatsApp Business installed
- `adb` installed on the host machine
- USB debugging enabled
- Phone unlocked / screen awake for best reliability
- OpenClaw environment capable of invoking local scripts

## Known limitations

- MIUI / AOD / lockscreen states can make UI dumps flaky
- XML readback may intermittently miss visible UI state
- fuzzy contact matching is conservative by design

## Why this exists

This repo captures a real-world integration workflow that was iteratively debugged and hardened:

- Android node setup
- ADB access
- WA Business UI automation
- contact confirmation
- draft confirmation
- send confirmation

So the process can be reused instead of rediscovered.

## License

Personal / experimental automation example unless replaced with another license.
