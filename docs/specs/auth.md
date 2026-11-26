# Auth
Status: implemented

## Purpose
Email + password login for employees, token refresh, and `/me`. Owns no tables; reads users
through `users.service`. See ADR 0005 (stateless JWTs).

## Data model
None. Tokens are HS256 JWTs: `sub` (user id), `type` (`access` | `refresh`), `iat`, `exp`, `jti`.
Access token lifetime `ACCESS_TOKEN_MINUTES` (30), refresh `REFRESH_TOKEN_DAYS` (7).

## Endpoints
| method | path | roles | request | response | errors |
|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | public | {email, password} | `TokenResponse` {access_token, refresh_token, token_type: "bearer", expires_in} | 401 `invalid_credentials` |
| POST | `/api/v1/auth/refresh` | public (refresh token) | {refresh_token} | `TokenResponse` (new pair) | 401 `invalid_token`, `token_expired` |
| GET | `/api/v1/auth/me` | all roles | Bearer access token | `MeRead` {id, email, full_name, phone, role, last_login_at} | 401 |

Clients send `Authorization: Bearer <access_token>` on every other route.

## Business rules
1. Wrong password, unknown email and inactive account all return the same 401
   `invalid_credentials` (no account enumeration; unknown emails still cost a hash check).
2. Login is case-insensitive on email and records `last_login_at`.
3. Access tokens are rejected on `/refresh`; refresh tokens are rejected as access tokens.
4. Every token use reloads the user: inactive or deleted user → 401.
5. Expired token → 401 `token_expired`; malformed / bad signature → 401 `invalid_token`.
6. 401 responses carry `WWW-Authenticate: Bearer`.
7. In production the API refuses to start if `JWT_SECRET` is the default or shorter than 32 chars.

## Events published / consumed
None.

## Jobs
None.

## Acceptance criteria
- [x] Valid login returns both tokens, `expires_in` = access lifetime, sets `last_login_at`
- [x] Login email is case-insensitive
- [x] Wrong password / unknown email / inactive user → identical 401 `invalid_credentials`
- [x] `/me` works for admin, manager and staff
- [x] `/me` without token → 401 with `WWW-Authenticate: Bearer`
- [x] Refresh token used as access token → 401 `invalid_token`
- [x] Expired access token → 401 `token_expired`; garbage / wrong-secret token → 401 `invalid_token`
- [x] Refresh returns a working new access token
- [x] Access token used as refresh token → 401
- [x] Refresh for a deactivated user → 401

## Open questions
- Login rate limiting / lockout after repeated failures? Not built.
- Revocable refresh tokens (token table with rotation)? Deferred, see ADR 0005.
- Should the frontend keep tokens in httpOnly cookies (would need a cookie-based login variant)?
