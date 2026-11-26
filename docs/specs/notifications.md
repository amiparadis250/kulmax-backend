# Notifications
Status: draft

## Purpose
Tell the right people about incidents through WhatsApp (self-hosted OpenWA), email (HTTPS email
API) and the dashboard; send reminders; log every attempt. Channels sit behind one `Notifier`
protocol (ADR 0004).

## Data model
`notifications` (log + WhatsApp/email queue)
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| incident_id | uuid | fk incidents, nullable (system messages, e.g. OpenWA disconnected) |
| group_key | varchar(64) | nullable; same for all incidents in one grouped offline message |
| kind | varchar(20) | `alert` \| `reminder` \| `system` |
| channel | varchar(20) | `whatsapp` \| `email` \| `dashboard` |
| recipient_user_id | uuid | fk users, nullable |
| recipient_contact_id | uuid | fk notification_contacts, nullable |
| recipient_address | varchar(254) | phone or email actually used; null for dashboard |
| subject | varchar(200) | nullable (email) |
| message | text | |
| status | varchar(10) | `queued` \| `sent` \| `failed` |
| attempts | int | default 0 |
| error | text | nullable |
| send_after | timestamptz | queue ordering |
| sent_at | timestamptz | nullable |
| read_at | timestamptz | nullable (dashboard only) |
| created_at, updated_at | timestamptz | |

`notification_contacts` (recipients that are not users, e.g. drivers — only if confirmed)
| id | name | phone | email | receives (`whatsapp`/`email` flags) | is_active | timestamps |

`notification_settings` (single row, admin-managed): reminder interval (30 min), max WhatsApp
reminders (3), WhatsApp send gap (seconds), OpenWA session name.

Internal: `Recipient` value object {name, phone?, email?, user_id?, contact_id?}, so a plain
phone number can be a recipient.
`class Notifier(Protocol): async def send(self, recipient: Recipient, message: Message) -> SendResult`
Implementations: `OpenWANotifier` (httpx), `EmailNotifier` (httpx), `DashboardNotifier`, `FakeNotifier`.

## Endpoints
| method | path | roles | request | response |
|---|---|---|---|---|
| GET | `/api/v1/notifications/feed` | all | page, limit, `unread` | `Page[DashboardNotificationRead]` |
| POST | `/api/v1/notifications/feed/{id}/read` | all | | `DashboardNotificationRead` |
| GET | `/api/v1/notifications/log` | admin, manager | page, limit, incident_id, channel, status, from, to | `Page[NotificationLogRead]` |
| GET/PUT | `/api/v1/notifications/settings` | admin | settings body | `NotificationSettingsRead` |
| GET/POST/PATCH | `/api/v1/notifications/contacts[/{id}]` | admin | contact body | `NotificationContactRead` |
| GET | `/api/v1/notifications/whatsapp/status` | admin | | {connected, checked_at} |

## Business rules
1. Recipients: active users with role manager or admin who have a phone (WhatsApp) / email,
   plus active `notification_contacts` (if that table is confirmed).
2. `high` / `low` opened → WhatsApp + email + dashboard.
3. `offline` opened → email + dashboard only (no WhatsApp). All offline incidents from one check
   run → **one** grouped message per recipient per channel.
4. Reminders: every 30 min while the incident is still `open` (not acknowledged). At most 3
   WhatsApp reminders per incident; after that, reminders continue by email only. Acknowledging
   or resolving stops reminders.
5. WhatsApp messages are queued (`status = queued`) and sent by the worker one at a time, a few
   seconds apart (configurable gap), never in a burst. Failed sends retry up to 3 attempts.
6. Every send attempt is logged: incident, recipient, channel, status, error, sent_at.
7. If OpenWA reports the session disconnected, email all active admins once per disconnection
   (not every check), and log a `system` notification.
8. Email goes through an HTTPS email API (not SMTP).
9. Channel failures never break incident creation (notifications react to events after commit).

## Events published / consumed
- Consumes `incidents.opened`, `incident.acknowledged`, `incident.resolved`.
- Publishes none.

## Jobs
- `send_whatsapp_queue`: every few seconds, send the oldest due queued WhatsApp message.
- `send_email_queue`: every 30 s, send queued emails.
- `send_reminders`: every minute, find open incidents due a reminder (rule 4).
- `check_openwa_session`: every 5 min (rule 7).

## Acceptance criteria
- [ ] High/low incident → WhatsApp + email + dashboard entries for each manager/admin with contact
- [ ] Offline incident → email + dashboard only, never WhatsApp
- [ ] 3 offline sensors in one check → one grouped message per recipient per channel
- [ ] Inactive users and staff are not recipients; users without phone get no WhatsApp
- [ ] A contact with only a phone number receives WhatsApp (if contacts confirmed)
- [ ] Reminder at 30, 60, 90 min while open; 4th reminder and later are email only
- [ ] Acknowledged incident gets no more reminders
- [ ] WhatsApp queue sends messages at least N seconds apart
- [ ] Every attempt logged with status and error; failed send retried, then `failed`
- [ ] OpenWA disconnected → admins emailed once per disconnection
- [ ] Tests use `FakeNotifier`; no real HTTP calls in tests
- [ ] Swapping OpenWA for another WhatsApp provider needs only a new `Notifier` class

## Open questions
- **Should drivers also receive alerts?** (decides whether `notification_contacts` is built, or
  whether to use the driver phone from orders).
- **Email provider** (Resend, Brevo, SendGrid, ...), sender address and domain — deferred.
- OpenWA deployment (Docker, `rmyndharis/openwa`, `ENGINE_TYPE=baileys`) — deferred with Docker.
- Reminders for `acknowledged` but unresolved incidents? Draft: no.
- Message language (English / Kinyarwanda / French) and exact wording.
- Quiet hours? Draft: none — cold-chain alerts are 24/7.
