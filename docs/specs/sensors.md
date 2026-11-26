# Sensors
Status: draft

## Purpose
Thermal sensors installed in cold-chain vehicles, the per-device secret token the gateway uses to
post readings, when each sensor was last heard from, and the periods it was offline.

## Data model
`sensors`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| device_id | varchar(64) | unique (hardware/gateway identifier) |
| vehicle_id | uuid | fk vehicles, nullable (spare sensor), indexed |
| offline_after_minutes | int | default 45, 5–1440 |
| last_seen_at | timestamptz | nullable (never reported) |
| is_active | bool | default true |
| token_hash | varchar(64) | unique; SHA-256 of the device token (token itself is never stored) |
| token_rotated_at | timestamptz | |
| created_at, updated_at | timestamptz | |

`sensor_offline_periods`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| sensor_id | uuid | fk sensors, indexed |
| vehicle_id | uuid | snapshot of the sensor's vehicle when the period started |
| started_at | timestamptz | = last_seen_at (or baseline, see rule 5) |
| detected_at | timestamptz | when the check noticed |
| ended_at | timestamptz | nullable; = measured_at of the first reading after coming back |
| duration_seconds | int | nullable; set on close |
At most one open period per sensor (partial unique index on sensor_id where ended_at is null).

## Endpoints
| method | path | roles | request | response | errors |
|---|---|---|---|---|---|
| GET | `/api/v1/sensors` | all | page, limit, `vehicle_id`, `is_active` | `Page[SensorRead]` (incl. `online` flag) | |
| POST | `/api/v1/sensors` | admin | {device_id, vehicle_id?, offline_after_minutes?} | 201 `SensorCreated` (includes `device_token`, shown once) | 409 `device_id_taken`, 404 vehicle |
| GET | `/api/v1/sensors/{id}` | all | | `SensorRead` | 404 |
| PATCH | `/api/v1/sensors/{id}` | admin | {vehicle_id? (null = unassign), offline_after_minutes?, is_active?} | `SensorRead` | 404, 422 |
| POST | `/api/v1/sensors/{id}/rotate-token` | admin | | `SensorTokenRead` {device_token} (shown once) | 404 |
| GET | `/api/v1/sensors/{id}/offline-periods` | all | page, limit, from, to | `Page[OfflinePeriodRead]` | 404 |

## Business rules
1. Device tokens: 32+ random bytes (URL-safe), shown only on create/rotate, stored as SHA-256
   (high-entropy token, so a fast hash is fine and allows an indexed lookup per reading).
   Rotating invalidates the old token immediately.
2. A cold-chain vehicle has at most one active sensor (open question if a vehicle can have two).
3. Moving a sensor to another vehicle only changes future readings; old readings keep their
   vehicle snapshot.
4. Inactive sensors cannot ingest (401) and are never checked for offline.
5. Offline check (worker, every minute): a sensor is offline when it is active, assigned to an
   active + in-service + cold-chain vehicle, has no open offline period, and
   `now - (last_seen_at or monitoring baseline) > offline_after_minutes`. The baseline for a
   sensor that never reported is when it was assigned / became monitored.
6. When a sensor goes offline: open a period (`started_at = last_seen_at`) and publish one
   `sensors.offline_detected` event per check run, listing all sensors detected in that run
   (so notifications can group them into one message).
7. When a reading arrives for a sensor with an open period: close it (`ended_at`,
   `duration_seconds`) and publish `sensor.back_online`.
8. Vehicles not `in_service` never get offline periods or incidents.

## Service interface
- `authenticate_device(session, token) -> SensorContext {sensor_id, vehicle_id}` (readings ingest)
- `mark_seen(session, sensor_id, measured_at)` → updates `last_seen_at` (max), closes open period
- `list_offline_periods(...)` (reports), `get_sensor_status(...)` (dashboard)

## Events published / consumed
- Publishes `sensors.offline_detected` {detected_at, items: [{sensor_id, vehicle_id, offline_period_id, last_seen_at}]}
- Publishes `sensor.back_online` {sensor_id, vehicle_id, offline_period_id, ended_at}
- Consumes none (readings calls `mark_seen` directly).

## Jobs
- `check_offline_sensors` every 60 s (see rules 5–6). Idempotent: an open period blocks re-detection.

## Acceptance criteria
- [ ] Admin creates sensor; token returned once; only the hash is stored
- [ ] Duplicate device_id → 409
- [ ] Rotate token: new token works, old token rejected
- [ ] Moving a sensor does not change existing readings' vehicle snapshot
- [ ] Offline check opens one period after `offline_after_minutes` with no reading, not before
- [ ] Several sensors detected in one run → one `sensors.offline_detected` event listing all
- [ ] Second check run while still offline does not open another period
- [ ] Vehicle not in service / inactive / not cold-chain → never detected offline
- [ ] Next reading closes the period with correct duration and publishes `sensor.back_online`
- [ ] Manager/staff get 403 on create/patch/rotate

## Open questions
- GSM gateway model: one token per sensor, or one gateway serving several sensors (token per gateway)?
- Can one vehicle have more than one sensor (e.g. front/back of the cold box)?
- Should a sensor that never reported raise an offline incident, and after how long?
