# Sales
Status: draft

## Purpose
Money earned, entered by hand. **Sales and orders are completely separate**: a sale never
references an order (no FK, no field).

## Data model
`sales`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| sale_date | date | not null (business date in Africa/Kigali) |
| origin | varchar(255) | not null |
| destination | varchar(255) | not null |
| vehicle_id | uuid | fk vehicles |
| amount | numeric(14,2) | > 0; currency RWF |
| currency | char(3) | fixed `RWF` (kept explicit for reports) |
| payment_method | varchar(30) | see open questions; draft: `cash` \| `mobile_money` \| `bank_transfer` \| `cheque` \| `other` |
| payment_reference | varchar(100) | nullable |
| note | text | nullable |
| recorded_by | uuid | fk users; the current user, never sent by the client |
| created_at, updated_at | timestamptz | |
Index on `sale_date`, `vehicle_id`.

## Endpoints (all roles)
| method | path | request | response | errors |
|---|---|---|---|---|
| GET | `/api/v1/sales` | page, limit, `from`, `to` (sale_date), `vehicle_id`, `payment_method` | `Page[SaleRead]` + `total_amount` for the filter | |
| POST | `/api/v1/sales` | `SaleCreate` {sale_date, origin, destination, vehicle_id, amount, payment_method, payment_reference?, note?} | 201 `SaleRead` | 404/422 vehicle, 422 |
| GET | `/api/v1/sales/{id}` | | `SaleRead` (with recorded_by name) | 404 |

## Business rules
1. No link to orders anywhere (schema, API, code).
2. `amount` is a Decimal > 0, serialised as a string to avoid float rounding.
3. `recorded_by` = current user.
4. Vehicle must exist (inactive vehicles allowed? see open questions; draft: must be active).
5. `sale_date` cannot be in the future (Kigali date).

## Events published / consumed
None.

## Jobs
None.

## Acceptance criteria
- [ ] Any role records a sale; `recorded_by` is the caller
- [ ] Amount ≤ 0 or non-numeric → 422; amount round-trips exactly (no float error)
- [ ] Future sale_date → 422
- [ ] Sale schema has no order reference
- [ ] List filters by date range, vehicle and payment method; returns total amount for the filter
- [ ] Unknown vehicle → error

## Open questions
- **Are the sale fields complete?** (customer name? invoice number? VAT?)
- Final list of payment methods.
- Can sales be edited or deleted, and by whom (draft: not editable; admin-only correction)?
- Can a sale use an inactive vehicle (historical entry)?
