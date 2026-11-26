# Readings
Status: draft

## Purpose
Store temperature readings sent by sensors through the GSM gateway, and serve temperature
history. The gateway payload format is not decided, so ingest goes through adapters that
produce a clean internal `ReadingIn`.

## Data model
`readings`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| sensor_id | uuid | fk sensors |
| vehicle_id | uuid | nullable; snapshot of the sensor's vehicle at ingest |
| temperature_c | numeric(5,2) | not null |
| measured_at | timestamptz | from the device |
| received_at | timestamptz | server time at ingest |
| created_at, updated_at | timestamptz | |
Unique `(sensor_id, measured_at)`. Index `(vehicle_id, measured_at desc)`.
(Volume: ~10 sensors × 1 reading/min ≈ 5M rows/year. Partitioning not needed yet.)

Internal schema `ReadingIn` {measured_at: aware datetime, temperature_c: Decimal}.

## Endpoints
| method | path | roles | request | response | errors |
|---|---|---|---|---|---|
| POST | `/api/v1/readings/ingest` | device token (`X-Device-Token` header), no user JWT | one reading or a list (max 1000), format per adapter; first adapter: JSON `{"readings": [{"measured_at", "temperature_c"}]}` or a single object | `IngestResult` {accepted, duplicates, rejected: [{index, reason}]} | 401 `invalid_device_token`, 422 |
| GET | `/api/v1/readings` | all | `vehicle_id` or `sensor_id` (one required), `from`, `to`, page, limit (max 1000 here) | `Page[ReadingRead]` ordered by measured_at | 422 |
| GET | `/api/v1/readings/latest` | all | | `list[LatestReadingRead]` one per active cold-chain vehicle | |

## Business rules
1. Ingest authenticates the device by its token (sensors.service), never by a user JWT.
2. Accepts one or many readings; gateways buffer during signal loss and send late batches.
3. Each stored reading has `measured_at` (device) and `received_at` (server), `sensor_id`, and the
   sensor's current `vehicle_id` as a snapshot.
4. Exact duplicates (same sensor + measured_at) are ignored and counted as `duplicates`
   (`INSERT ... ON CONFLICT DO NOTHING`), so gateway retries are safe.
5. Readings are processed in `measured_at` order within a batch.
6. After storing, call `sensors.mark_seen(sensor_id, max(measured_at))` (updates last_seen_at,
   closes any open offline period).
7. For every newly stored reading publish `reading.recorded`; alert evaluation happens in
   `incidents`, not here.
8. Proposed: reject readings with `measured_at` more than 5 minutes in the future (clock error),
   reported in `rejected`, the rest of the batch is still stored.
9. Adding a gateway format = one new adapter in `adapters.py` mapping raw payload → `list[ReadingIn]`.

## Service interface
- `get_previous_reading(session, sensor_id, before: measured_at)` (blip filter in incidents)
- `get_latest_by_vehicle(...)` (dashboard), `list_readings(...)` (reports)

## Events published / consumed
- Publishes `reading.recorded` {reading_id, sensor_id, vehicle_id, temperature_c, measured_at}
- Consumes none.

## Jobs
None.

## Acceptance criteria
- [ ] Valid token + single reading → stored with measured_at, received_at, sensor_id, vehicle snapshot
- [ ] Batch of readings accepted in one request
- [ ] Missing / wrong / rotated / inactive-sensor token → 401
- [ ] A user JWT is not accepted on ingest
- [ ] Duplicate (sensor, measured_at) ignored and counted; retrying the same batch stores nothing new
- [ ] `last_seen_at` updated to the newest measured_at; never moves backwards on a late batch
- [ ] Open offline period closed by the next reading
- [ ] `reading.recorded` published once per new reading, in measured_at order
- [ ] Moving the sensor afterwards does not change stored vehicle snapshots
- [ ] History endpoint filters by vehicle/sensor and time range

## Open questions
- **GSM gateway model and payload format (HTTP, MQTT or SMS)** — decides the first real adapter.
  If MQTT or SMS, a bridge process (or SMS provider webhook) will post into the same service.
- Reading interval of the sensors (affects offline timing and storage)?
- Retention: keep raw readings forever, or downsample after N months?
- Future-timestamp rule (rule 8): confirm the 5-minute tolerance.
