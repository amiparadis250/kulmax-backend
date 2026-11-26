# Incidents
Status: draft

## Purpose
Open, track and close temperature problems: `high`, `low` and `offline`. Decides *when* an
incident exists; `notifications` decides who hears about it.

## Data model
`incidents`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| sensor_id | uuid | fk sensors |
| vehicle_id | uuid | snapshot at opening |
| type | varchar(10) | `high` \| `low` \| `offline` |
| status | varchar(15) | `open` \| `acknowledged` \| `resolved` |
| opened_at | timestamptz | |
| acknowledged_by | uuid | fk users, nullable |
| acknowledged_at | timestamptz | nullable |
| resolved_by | uuid | fk users, nullable |
| resolved_at | timestamptz | nullable |
| resolution_note | text | required when resolved |
| first_reading_id | uuid | fk readings, nullable (null for offline) |
| latest_reading_id | uuid | fk readings, nullable |
| peak_temperature_c | numeric(5,2) | nullable; highest (high) / lowest (low) seen |
| offline_period_id | uuid | fk sensor_offline_periods, nullable |
| limit_min_c, limit_max_c | numeric(5,2) | limits in force when opened |
| created_at, updated_at | timestamptz | |
Partial unique index `(sensor_id, type) WHERE status <> 'resolved'` → at most one unresolved
incident per sensor and type.

## Endpoints
| method | path | roles | request | response | errors |
|---|---|---|---|---|---|
| GET | `/api/v1/incidents` | all | page, limit, `status` (multi), `type`, `vehicle_id`, `from`, `to` | `Page[IncidentRead]` newest first | |
| GET | `/api/v1/incidents/active` | all | | `list[IncidentRead]` (open + acknowledged) | |
| GET | `/api/v1/incidents/{id}` | all | | `IncidentDetail` (incl. user names, readings) | 404 |
| POST | `/api/v1/incidents/{id}/acknowledge` | all | | `IncidentRead` | 404, 422 `invalid_status_transition` |
| POST | `/api/v1/incidents/{id}/resolve` | admin, manager | {resolution_note (1–2000 chars, required)} | `IncidentRead` | 403, 404, 422 |

## Business rules
Evaluation applies only to sensors on **active, cold_chain, in_service** vehicles.
1. **High**: reading > vehicle `max_temp_c`. **Low**: reading < `min_temp_c`. Equal to a limit is OK.
2. **Blip filter**: open a high/low incident only when this reading AND the previous reading of
   the same sensor (by `measured_at`) are both out of limit in the same direction.
3. **No duplicates**: if an unresolved incident exists for (sensor, type), a further bad reading
   attaches to it (`latest_reading_id`, `peak_temperature_c` updated); no new incident.
4. **Offline**: on `sensors.offline_detected`, open one `offline` incident per listed sensor
   (unless an unresolved offline incident exists for it), linked to its offline period.
5. **Lifecycle**: `open → acknowledged → resolved`. Any other transition → 422
   `invalid_status_transition`. Resolving requires a non-empty note.
6. Return to normal (or back online) does **not** close the incident: it stays open until a
   person resolves it. The vehicle tile shows "normal" based on the latest reading.
7. Only admin/manager can resolve; all roles can acknowledge.
8. Uses vehicle limits at evaluation time and stores them on the incident.

## Events published / consumed
- Consumes `reading.recorded` (high/low evaluation), `sensors.offline_detected` (offline).
- Publishes `incidents.opened` {items: [{incident_id, type, vehicle_id, sensor_id}], grouped: bool}
  (one event per offline check run; one per high/low incident).
- Publishes `incident.acknowledged` {incident_id, by} (stops reminders), `incident.resolved`.

## Jobs
None (reminders belong to `notifications`).

## Acceptance criteria
- [ ] One reading above max → no incident; two consecutive above max → one `high` incident
- [ ] Above-max then below-min → no incident (different directions)
- [ ] Out, normal, out → no incident (not consecutive)
- [ ] Two consecutive below min → `low` incident
- [ ] Further bad readings attach to the open incident; no second incident for same sensor+type
- [ ] A `high` and a `low` incident can coexist for the same sensor
- [ ] After resolve, two new bad readings open a new incident
- [ ] Readings back to normal leave the incident open
- [ ] No incidents for vehicles that are inactive, not in service, or not cold-chain
- [ ] Offline event opens one offline incident per sensor; repeat event does not duplicate
- [ ] Acknowledge: open → acknowledged (all roles); twice → 422
- [ ] Resolve without note → 422; staff → 403; resolve from acknowledged works
- [ ] open → resolved directly → 422 (per lifecycle; see open question)
- [ ] Late (out-of-order) readings use measured_at order for the blip filter

## Open questions
- May a manager resolve directly from `open` (skip acknowledge)? Draft: no.
- Should offline incidents auto-resolve when the sensor comes back? Draft: no (same as temperature).
- Late buffered readings arriving hours later: still open incidents for past excursions, or only
  record them? Draft: open, with `opened_at` = now and readings showing the real time.
