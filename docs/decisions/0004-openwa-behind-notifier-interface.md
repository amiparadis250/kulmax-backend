# 0004. WhatsApp through self-hosted OpenWA, behind a `Notifier` interface

Date: 2026-11-26 · Status: accepted

## Context
Temperature alerts must reach managers quickly; WhatsApp is what they read. The official
WhatsApp Cloud API needs business verification and templates. OpenWA (`rmyndharis/openwa`,
Baileys engine) is self-hosted and quick to start with, but it is unofficial: sessions can
disconnect and the number can be banned if it sends bursts.

## Decision
All channels implement one protocol, `Notifier.send(recipient, message)`:
`OpenWANotifier` (httpx → OpenWA REST), `EmailNotifier` (HTTPS email API, not SMTP),
`DashboardNotifier` (stored for the UI) and `FakeNotifier` (tests, local dev). Business code only
sees the protocol. WhatsApp messages are queued and sent by the worker a few seconds apart.
If OpenWA reports the session disconnected, admins are emailed.

## Consequences
- Moving to the official WhatsApp Cloud API later means one new class + config.
- OpenWA is a separate container that must not be exposed publicly.
- Email is the fallback channel, so it must be reliable (HTTPS API provider, TBD).
