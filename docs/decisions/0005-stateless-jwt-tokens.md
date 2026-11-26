# 0005. Stateless JWT access and refresh tokens

Date: 2026-11-26 · Status: accepted

## Context
Employees log in from a browser with email + password. We need short-lived access tokens and a
way to stay logged in, with the least moving parts for now.

## Decision
`POST /auth/login` returns an access token (30 min) and a refresh token (7 days), both HS256
JWTs with a `type` claim. No token table. Every request that uses a token reloads the user and
rejects inactive users.

## Consequences
- Deactivating a user locks them out on their next request.
- A stolen refresh token cannot be revoked individually before it expires (only by deactivating
  the user or rotating `JWT_SECRET`, which logs everyone out). If this becomes a problem, add a
  `refresh_tokens` table with rotation; the API shape does not need to change.
- Logout is client-side (drop the tokens).
