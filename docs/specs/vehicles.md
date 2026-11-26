# Vehicles
Status: draft

## Purpose
The Kulmax fleet. Orders and sales pick a vehicle from this list. Cold-chain vehicles carry a
temperature range (°C) that the alert logic checks readings against. Every limit change is audited.

## Data model
`vehicles`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| plate | varchar(20) | unique; normalised upper-case, no spaces (e.g. `RAD123A`) |
| type | varchar(20) | `cold_chain` \| `other` (CHECK) |
| min_temp_c | numeric(5,2) | nullable; required when `type = cold_chain` |
| max_temp_c | numeric(5,2) | nullable; required when `type = cold_chain` |
| in_service | bool | default true. Not in service → no alerts, no offline incidents |
| is_active | bool | default true. Inactive → hidden from pickers, no alerts |
| created_at, updated_at | timestamptz | |
CHECK: `min_temp_c < max_temp_c` when both set.

`vehicle_limit_changes` (audit log, append-only)
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| vehicle_id | uuid | fk vehicles, indexed |
| changed_by | uuid | fk users |
| old_min_temp_c, old_max_temp_c | numeric(5,2) | nullable (first time set) |
| new_min_temp_c, new_max_temp_c | numeric(5,2) | not null |
| created_at | timestamptz | = when the change happened |

## Endpoints
| method | path | roles | request | response | errors |
|---|---|---|---|---|---|
| GET | `/api/v1/vehicles` | all | query: page, limit, `type`, `in_service`, `is_active`, `q` (plate) | `Page[VehicleRead]` | |
| POST | `/api/v1/vehicles` | admin | {plate, type, min_temp_c?, max_temp_c?, in_service?} | 201 `VehicleRead` | 409 `plate_taken`, 422 `invalid_limits` |
| GET | `/api/v1/vehicles/{id}` | all | | `VehicleRead` | 404 |
| PATCH | `/api/v1/vehicles/{id}` | admin | {plate?, type?, in_service?, is_active?} | `VehicleRead` | 404, 409, 422 |
| PUT | `/api/v1/vehicles/{id}/temperature-limits` | all | {min_temp_c, max_temp_c} | `VehicleRead` | 404, 422 `invalid_limits`, 422 `not_cold_chain` |
| GET | `/api/v1/vehicles/{id}/temperature-limits/history` | all | page, limit | `Page[LimitChangeRead]` (newest first, with changed_by name) | 404 |

## Business rules
1. Plate is unique after normalisation (`rad 123 a` == `RAD123A`).
2. `min_temp_c < max_temp_c`, else 422 `invalid_limits`. Limits are only for `cold_chain`
   vehicles (422 `not_cold_chain` otherwise).
3. Changing a vehicle to `cold_chain` requires limits in the same request.
4. Every change to min/max (including the initial values on create) writes one
   `vehicle_limit_changes` row: who, old values, new values, when. Setting the same values is a
   no-op (no audit row).
5. Limits can only be changed through the temperature-limits endpoint (not via PATCH), so the
   audit cannot be bypassed.
6. Vehicles are never hard-deleted (orders, sales and readings reference them); use `is_active`.

## Service interface (for other features)
- `get_vehicle(session, id)`; `get_monitoring_config(session, id) -> {type, min, max, in_service, is_active}`
- `list_monitored_vehicles(session)` → active, in-service, cold-chain vehicles (alerts, dashboard)
- `ensure_vehicle_selectable(session, id)` → 404/422 if missing or inactive (orders, sales)

## Events published / consumed
- Publishes `vehicle.limits_changed` {vehicle_id, old_min, old_max, new_min, new_max, changed_by}.
- Consumes none.

## Jobs
None.

## Acceptance criteria
- [ ] Admin creates cold-chain vehicle with limits; initial audit row written
- [ ] Creating a cold-chain vehicle without limits → 422
- [ ] Duplicate plate (after normalisation) → 409 `plate_taken`
- [ ] Any role can set limits; audit row has user, old and new values, timestamp
- [ ] min ≥ max → 422 `invalid_limits`; limits on `other` vehicle → 422 `not_cold_chain`
- [ ] Same values again → no new audit row
- [ ] PATCH cannot change limits
- [ ] Manager/staff get 403 on create and PATCH; all roles can list and read
- [ ] List filters by type, in_service, is_active, plate search; paginated
- [ ] Limit history newest first, paginated

## Open questions
- Extra vehicle fields needed (name, make/model, capacity, default driver)? Not included.
- Who may toggle `in_service` (e.g. staff when a truck is parked for maintenance)? Draft: admin only.
- Allowed temperature range sanity bounds (e.g. −40 °C to +40 °C)?
