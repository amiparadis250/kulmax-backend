# Dashboard
Status: draft

## Purpose
One endpoint with everything the home screen needs, so the frontend makes a single call.
Owns no tables; reads through other features' services.

## Data model
None.

## Endpoints
| method | path | roles | response |
|---|---|---|---|
| GET | `/api/v1/dashboard` | all | `DashboardRead` |

`DashboardRead`:
- `orders_by_status`: {pending, confirmed_dispatched, delivered, rejected} counts (draft: all time
  for pending/dispatched, today for delivered/rejected)
- `recent_sales`: last 10 sales {id, sale_date, origin, destination, vehicle plate, amount}
  + `sales_today_total`
- `vehicles`: one tile per active cold-chain vehicle {vehicle_id, plate, in_service, min, max,
  latest temperature, measured_at, state, has_active_incident}
  where `state` = `normal` | `high` | `low` | `offline` | `no_data` | `not_in_service`
- `active_incidents`: open + acknowledged incidents, newest first
- `generated_at`

## Business rules
1. Tile `state` comes from the latest reading vs current limits, `offline` if the sensor has an
   open offline period, `not_in_service` if the vehicle is out of service.
2. A tile can show `normal` while an incident is still open (incidents stay open until resolved).
3. Today = current date in Africa/Kigali.
4. Must stay fast: a handful of aggregate queries, no per-vehicle N+1 loops.

## Events published / consumed
None.

## Jobs
None.

## Acceptance criteria
- [ ] All roles get 200; no token → 401
- [ ] Order counts by status are correct
- [ ] Recent sales are the 10 newest; today's total uses the Kigali date
- [ ] One tile per active cold-chain vehicle with the correct state in each case
- [ ] Tile shows `normal` while its incident is still open
- [ ] Active incidents include open and acknowledged, not resolved

## Open questions
- Should the dashboard auto-refresh by polling, or do we want live updates (SSE/WebSocket)?
- Should non-cold-chain vehicles appear as tiles too?
- Exact time windows for order counts.
