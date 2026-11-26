# Orders
Status: draft

## Purpose
Record a customer's transport request: who, what (free-text lines), which vehicle and driver,
where to, and track it through a fixed status flow. No inventory or stock tracking.
Orders are completely separate from sales.

## Data model
`orders`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| reference | varchar(20) | unique, auto: `ORD-<year>-<seq 4+ digits>`, e.g. `ORD-2026-0001` |
| customer_name | varchar(200) | not null |
| service_type | varchar(20) | `cold_chain` \| `other` |
| driver_name | varchar(120) | not null (typed in; drivers have no accounts) |
| driver_phone | varchar(20) | not null, same phone validation as users |
| vehicle_id | uuid | fk vehicles |
| destination | varchar(255) | not null |
| notes | text | nullable |
| status | varchar(30) | `pending` \| `rejected` \| `confirmed_dispatched` \| `delivered` |
| created_by | uuid | fk users |
| created_at, updated_at | timestamptz | |

`order_lines`
| id | order_id (fk, cascade) | position int | description varchar(500) not null | quantity varchar(100) not null (free text, e.g. "20 boxes") | timestamps |

`order_reference_counters` {year int pk, last_value int} — row-locked to issue references
without gaps under concurrency.

## Endpoints (all roles unless stated)
| method | path | request | response | errors |
|---|---|---|---|---|
| GET | `/api/v1/orders` | page, limit, `status` (multi), `service_type`, `vehicle_id`, `from`, `to`, `q` (reference/customer) | `Page[OrderRead]` newest first | |
| POST | `/api/v1/orders` | `OrderCreate` {customer_name, service_type, driver_name, driver_phone, vehicle_id, destination, notes?, lines: [{description, quantity}] (≥1)} | 201 `OrderRead` (status `pending`) | 404/422 vehicle, 422 |
| GET | `/api/v1/orders/{id}` | | `OrderRead` with lines | 404 |
| PATCH | `/api/v1/orders/{id}` | any field above, `lines` replaces all lines | `OrderRead` | 404, 422 `order_not_editable` |
| POST | `/api/v1/orders/{id}/status` | {status} | `OrderRead` | 404, 422 `invalid_status_transition` |

## Business rules
1. Status flow: `pending → rejected`, `pending → confirmed_dispatched → delivered`. Every other
   transition (including same-status) → 422 `invalid_status_transition` with
   `details: {from, to, allowed: [...]}`.
2. New orders always start `pending`; status cannot be set on create or via PATCH.
3. Reference is generated per calendar year (Africa/Kigali), sequential, never reused.
4. Vehicle must exist and be active.
5. Draft: order fields and lines are editable only while `pending`.
6. `created_by` is the current user; never sent by the client.

## Events published / consumed
- Publishes `order.status_changed` {order_id, from, to, by} (for future use; no consumer yet).

## Jobs
None.

## Acceptance criteria
- [ ] Create order with lines → `pending`, reference `ORD-<year>-0001`, next is `-0002`
- [ ] Reference sequence restarts at 0001 in a new year
- [ ] Concurrent creates never produce duplicate references
- [ ] pending→confirmed_dispatched→delivered allowed; pending→rejected allowed
- [ ] Every other transition → 422 with from/to/allowed (e.g. pending→delivered, rejected→pending, delivered→anything)
- [ ] Inactive / unknown vehicle → error
- [ ] Order without lines → 422
- [ ] Editing a non-pending order → 422 `order_not_editable`
- [ ] All three roles can create, update, change status and view
- [ ] List filters and pagination work

## Open questions
- Should we record who/when for each status change (status history table, or confirmed_at /
  delivered_at columns) and a rejection reason?
- Are orders editable after dispatch (e.g. to fix a typo)?
- Customer details beyond the name (phone, company)?
- Must the vehicle type match the service type (cold_chain order → cold_chain vehicle)?
