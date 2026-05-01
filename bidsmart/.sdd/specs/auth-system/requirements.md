# Auth System — Requirements (EARS Format)

## FR-1: User Registration

**As a** new user
**When** I submit a registration request with username, password, and role
**The system shall** check username uniqueness, hash the password with bcrypt,
store the user with `must_change_password=True`, and return the created user
profile (without password hash).

**Acceptance criteria:**
- Duplicate username returns HTTP 409 with "Username already registered"
- Password hash stored using bcrypt via `hashpw(password, gensalt())`
- Password hash never returned in API responses
- `must_change_password` defaults to `True`
- Role defaults to `viewer` if not specified
- Role validated against `UserRole` enum (admin, reviewer, viewer, bid_editor)

## FR-2: JWT Login with Access/Refresh Tokens

**As a** registered user
**When** I submit valid credentials
**The system shall** verify the password with constant-time bcrypt comparison,
issue an HS256-signed access token (default 24h expiry) and refresh token
(default 7d expiry), and return both with token_type "bearer".

**Acceptance criteria:**
- Invalid credentials return HTTP 401 with "Invalid username or password"
- `WWW-Authenticate: Bearer` header on 401 responses
- Access token JWT claims: `{sub, type:"access", iat, exp}`
- Refresh token JWT claims: `{sub, type:"refresh", iat, exp}`
- `must_change_password` flag returned in token response
- Token expiry configurable via Settings (access/refresh_token_expire_minutes)

## FR-3: Token Refresh

**As a** user with an expiring access token
**When** I submit a valid refresh token
**The system shall** validate it is type "refresh", verify the user still exists,
and issue a new access + refresh token pair.

**Acceptance criteria:**
- Non-refresh token (type "access") returns HTTP 401 with "Token is not a refresh token"
- Expired refresh token returns HTTP 401 with "Invalid or expired token"
- Deleted user's refresh token returns HTTP 401 with "User no longer exists"
- New token pair has fresh expiry timestamps

## FR-4: RBAC Role Enforcement

**As an** administrator
**When** I access admin-only endpoints
**The system shall** extract the Bearer token, decode and validate it,
load the user, and check that the user's role is in the allowed set.
Return HTTP 403 for denied roles.

**Acceptance criteria:**
- `get_current_user` dependency extracts token from Authorization header
- Missing Authorization header returns HTTP 401
- Invalid/expired token returns HTTP 401
- `require_role(*roles)` returns a dependency that chains with `get_current_user`
- Mismatched role returns HTTP 403 with "Requires one of roles: ..."
- Example: `require_role("admin")` on `GET /users/me/admin`

## FR-5: Password Change with First-Login Enforcement

**As a** user who must change password
**When** I call the password change endpoint with a new password (min 6 chars)
**The system shall** hash the new password with bcrypt, update the stored hash,
set `must_change_password=False`, and return success.

**Acceptance criteria:**
- Requires authentication (valid access token)
- New password minimum length: 6 characters, maximum: 128
- Successful change clears `must_change_password` flag
- `must_change_password=True` is returned in login response to signal enforcement
- Upstream enforcement (blocking non-password-change endpoints) is a TODO

## FR-6: Current User Endpoint

**As an** authenticated user
**When** I request my own profile
**The system shall** return my user ID, username, and role.

**Acceptance criteria:**
- `GET /auth/me` returns `{id, username, role}` — lightweight, no DB query beyond auth
- `GET /users/me` returns full `UserResponse` (id, username, role, created_at)
- Both require valid Bearer token
- Password hash never exposed

## Non-Functional Requirements

| ID    | Description                                  | Target          |
|-------|----------------------------------------------|-----------------|
| NFR-1 | bcrypt hash time                             | ~100ms          |
| NFR-2 | JWT verification overhead                    | < 2ms           |
| NFR-3 | Token size (HS256)                           | < 500 bytes     |
| NFR-4 | Stateless service (no server-side session)   | Yes             |
| NFR-5 | Concurrent login safety                      | Thread-safe     |
