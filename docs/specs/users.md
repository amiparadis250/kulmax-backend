# Users
Status: implemented

## Purpose
Kulmax employees who can log in, their role (`admin`, `manager`, `staff`), and the contact
details used for alerts (phone for WhatsApp, email). Only admins manage users.

## Data model
`users`
| column | type | constraints |
|---|---|---|
| id | uuid | pk |
| email | varchar(254) | unique, stored lower-cased |
| full_name | varchar(120) | not null, trimmed |
| phone | varchar(20) | nullable; 9–15 digits, optional leading `+`; spaces/dashes stripped |
| role | varchar(20) | `admin` \| `manager` \| `staff` (CHECK) |
| password_hash | varchar(255) | argon2 |
| is_active | bool | default true |
| last_login_at | timestamptz | nullable |
| created_at, updated_at | timestamptz | |

## Endpoints (all admin only)
| method | path | request | response | errors |
|---|---|---|---|---|
| GET | `/api/v1/users` | query: `page`, `limit`, `role`, `is_active`, `q` (name/email search) | `Page[UserRead]` | 401, 403, 422 |
| POST | `/api/v1/users` | `UserCreate` {email, full_name, phone?, role, password (8–128)} | 201 `UserRead` | 409 `email_taken`, 422 |
| GET | `/api/v1/users/{id}` | | `UserRead` | 404 |
| PATCH | `/api/v1/users/{id}` | `UserUpdate` {full_name?, phone? (null clears), role?, is_active?, password?} | `UserRead` | 404, 422 `cannot_modify_self`, 422 `last_admin` |

`UserRead` never contains the password or its hash.

## Business rules
1. Email is unique, case-insensitive (stored lower-case).
2. An admin cannot deactivate themselves or change their own role (`cannot_modify_self`).
3. There is always at least one active admin: demoting or deactivating the last active admin
   fails (`last_admin`).
4. Deactivated users cannot log in, and their existing tokens stop working immediately.
5. Admins can set a new password for a user (PATCH `password`).
6. Users are never hard-deleted (deactivate instead), so history (created_by etc.) stays valid.

## Service interface (for other features)
- `get_user(session, id) -> User` (404 if missing), `get_active_user(session, id) -> User | None`
- `authenticate(session, email, password) -> User | None` (used by `auth`)
- `list_users(...)`, `create_user(...)`, `update_user(...)`, `seed_admin(...)`
- Later, for `notifications`: a function returning active managers/admins with phone/email.

## Events published / consumed
None.

## Jobs
None. CLI: `uv run python tasks.py seed-admin --email ... --full-name ...` (password from
`--password`, `SEED_ADMIN_PASSWORD`, or a prompt). Idempotent: existing email → no change.

## Acceptance criteria
- [x] Admin creates a user; email lower-cased, name trimmed, phone normalised; no password in response
- [x] Duplicate email (any case) → 409 `email_taken`
- [x] Invalid email / short password / unknown role / bad phone / empty name → 422 `validation_error`
- [x] List supports pagination (`total`, `page`, `limit`) and filters `role`, `is_active`, `q`; `limit` > 100 → 422
- [x] Unknown id → 404 `not_found`
- [x] PATCH changes only the sent fields; `phone: null` clears; null for required fields → 422
- [x] Admin can reset a password and the user can log in with it
- [x] Admin cannot deactivate self or change own role
- [x] Last active admin cannot be demoted or deactivated (inactive admins don't count)
- [x] Manager and staff get 403 on every users endpoint; no token → 401
- [x] Deactivated user's token is rejected
- [x] `seed-admin` creates an admin once and is idempotent; never changes an existing user

## Open questions
- Should users be able to change their own password / phone (a `PATCH /auth/me`)? Not built.
- Password reset by email ("forgot password")? Not built; admins reset passwords for now.
