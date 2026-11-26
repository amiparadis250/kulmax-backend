# Reports
Status: draft

## Purpose
Read-only aggregations with date filters and CSV export, for managers and admins. Owns no
tables; reads only through other features' services.

## Data model
None.

## Endpoints (admin, manager only)
All take `from` and `to` (dates, inclusive, interpreted in Africa/Kigali) and `format=json|csv`
(CSV → `text/csv` with `Content-Disposition: attachment; filename=<report>_<from>_<to>.csv`).
| method | path | extra filters | JSON response |
|---|---|---|---|
| GET | `/api/v1/reports/orders` | status, service_type, vehicle_id | rows + counts by status / service type |
| GET | `/api/v1/reports/sales` | vehicle_id, payment_method | rows + totals by vehicle, by payment method, grand total |
| GET | `/api/v1/reports/temperatures` | vehicle_id (required), `bucket` (`raw`\|`15m`\|`1h`\|`1d`) | per bucket: min / avg / max, reading count |
| GET | `/api/v1/reports/incidents` | type, status, vehicle_id | rows + counts by type, mean time to acknowledge / resolve |
| GET | `/api/v1/reports/offline-periods` | vehicle_id | rows + total offline duration per vehicle |
Errors: 403 for staff, 422 for `from > to` or a range over the max (draft: 366 days).

## Business rules
1. Staff get 403 on every report.
2. Date filters use Kigali day boundaries converted to UTC (`core.time.business_day_start_utc`).
3. Times in CSV are shown in Africa/Kigali with the offset; amounts as plain decimals.
4. CSV is streamed (large temperature exports must not load everything into memory).
5. Reports never query other features' tables directly.

## Events published / consumed
None.

## Jobs
None.

## Acceptance criteria
- [ ] Staff → 403 on every report; manager and admin → 200
- [ ] Each report respects `from`/`to` at Kigali midnight boundaries
- [ ] CSV export has a header row, correct content type and filename
- [ ] Sales totals match the sum of rows
- [ ] Temperature buckets compute min/avg/max correctly
- [ ] `from > to` → 422

## Open questions
- Exact columns wanted in each CSV? Excel-friendly (UTF-8 BOM, `;` separator)?
- PDF export needed?
- Scheduled reports by email (e.g. weekly temperature summary for audits)?
