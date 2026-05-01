# Auth System — Feature Brief

## Problem Statement

BidSmart is a multi-role enterprise platform handling competitive procurement
data. Without a proper authentication and authorization system, the platform
faces:

1. **No identity verification** — anyone with network access could submit bids,
   view confidential documents, or modify project configurations.
2. **No role-based access control** — a single user could perform actions
   reserved for administrators (user management, system configuration) or access
   competitors' bid data.
3. **Static credentials** — long-lived sessions without token rotation create a
   persistent attack surface. A leaked token remains valid indefinitely.
4. **No password lifecycle** — shared default passwords, no mechanism to enforce
   password changes, no account uniqueness guarantee.
5. **No current-user context** — endpoints can't identify the calling user,
   blocking personalization, audit trails, and multi-tenant isolation.

These gaps make BidSmart unsuitable for real enterprise procurement scenarios
where role separation (admin, reviewer, bid_editor, viewer) is a hard
requirement.

## Solution

The Auth System provides secure, token-based authentication with role-based
access control (RBAC):

| Capability                  | Implementation                                    | Code Location |
|-----------------------------|---------------------------------------------------|---------------|
| User registration           | Username uniqueness check, bcrypt password hash   | `src/platform/auth/service.py` |
| JWT Bearer auth             | HS256-signed access + refresh tokens              | `src/platform/auth/service.py` |
| Token refresh               | Long-lived refresh token → new token pair         | `src/platform/auth/service.py` |
| RBAC enforcement            | `require_role(*roles)` FastAPI dependency         | `src/dependencies.py` |
| Password change             | First-login enforcement via `must_change_password` | `src/platform/auth/router.py` |
| Current user endpoint       | `GET /auth/me` and `GET /users/me`                | `src/platform/auth/router.py` |

### How It Works

1. **Registration**: `POST /auth/register` — validates username uniqueness,
   hashes password with bcrypt (4 rounds via `gensalt()`), stores user with
   `must_change_password=True`.

2. **Login**: `POST /auth/login` — validates credentials with constant-time
   bcrypt comparison. Returns an access token (default 24h) and a refresh token
   (default 7d). Both are HS256 JWTs with typed claims (`"type":"access"` /
   `"type":"refresh"`).

3. **Authenticated requests**: `Authorization: Bearer <access_token>` header,
   validated by `get_current_user` dependency which decodes the token, verifies
   type is `"access"`, and loads the user from the database.

4. **RBAC**: `require_role("admin")` wraps `get_current_user` and checks
   `current_user.role.value` against the allowed list. Returns 403 if denied.

5. **Token refresh**: `POST /auth/refresh` — accepts a refresh token, validates
   it's type `"refresh"` and user still exists, issues a new token pair.

6. **Password change**: `PUT /auth/change-password` — hashes new password,
   clears `must_change_password` flag. Enforced at login via the
   `must_change_password` field in the token response.

## Scope

**In scope**: Registration, login, JWT issuance/validation, token refresh, RBAC,
password management, current-user endpoint.

**Out of scope**: OAuth2/SAML SSO, MFA, password reset via email, session
revocation (blacklist), external IdP integration.

## Status

All capabilities are fully implemented. The auth system is the foundation for
all access-controlled endpoints in the platform.
