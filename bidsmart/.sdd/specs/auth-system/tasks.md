# Auth System — Task Breakdown

All tasks are **completed** as of BidSmart v0.7.7.

## Phase 1: User Model & Database

| Task | Description | File | Status |
|------|-------------|------|--------|
| T1.1 | Create `UserRole` enum (admin, reviewer, viewer, bid_editor) | `src/models/user.py` | ✅ Done |
| T1.2 | Create `User` model with username, password_hash, role, must_change_password | `src/models/user.py` | ✅ Done |
| T1.3 | Add database migration for `users` table | `src/db/migrations/versions/20260430_0726_initial.py` | ✅ Done |

## Phase 2: Service Layer

| Task | Description | File | Status |
|------|-------------|------|--------|
| T2.1 | Implement `_hash_password()` / `_verify_password()` with bcrypt | `src/platform/auth/service.py` | ✅ Done |
| T2.2 | Implement `_create_token()` — HS256 JWT with sub, type, iat, exp claims | `src/platform/auth/service.py` | ✅ Done |
| T2.3 | Implement `_decode_token()` — JWT validation with JWTError handling | `src/platform/auth/service.py` | ✅ Done |
| T2.4 | Implement `_create_token_pair()` — access + refresh token generation | `src/platform/auth/service.py` | ✅ Done |
| T2.5 | Implement `register()` — uniqueness check, bcrypt hash, user creation | `src/platform/auth/service.py` | ✅ Done |
| T2.6 | Implement `login()` — credential validation, token pair issuance | `src/platform/auth/service.py` | ✅ Done |
| T2.7 | Implement `refresh_token()` — refresh token validation, new pair issuance | `src/platform/auth/service.py` | ✅ Done |
| T2.8 | Implement `get_current_user()` — access token decode, user load | `src/platform/auth/service.py` | ✅ Done |
| T2.9 | Implement `change_password()` — rehash, clear must_change_password | `src/platform/auth/service.py` | ✅ Done |
| T2.10 | Create module-level `auth_service` singleton | `src/platform/auth/service.py` | ✅ Done |

## Phase 3: Schemas

| Task | Description | File | Status |
|------|-------------|------|--------|
| T3.1 | Create `RoleEnum` for request validation | `src/platform/auth/schemas.py` | ✅ Done |
| T3.2 | Create `RegisterRequest`, `LoginRequest`, `RefreshRequest` | `src/platform/auth/schemas.py` | ✅ Done |
| T3.3 | Create `TokenResponse` (access/refresh/token_type/must_change_password) | `src/platform/auth/schemas.py` | ✅ Done |
| T3.4 | Create `UserResponse` (id/username/role/created_at, from_attributes=True) | `src/platform/auth/schemas.py` | ✅ Done |

## Phase 4: Router

| Task | Description | File | Status |
|------|-------------|------|--------|
| T4.1 | Implement `POST /auth/register` with 201 response | `src/platform/auth/router.py` | ✅ Done |
| T4.2 | Implement `POST /auth/login` | `src/platform/auth/router.py` | ✅ Done |
| T4.3 | Implement `POST /auth/refresh` | `src/platform/auth/router.py` | ✅ Done |
| T4.4 | Implement `GET /auth/me` (lightweight current user) | `src/platform/auth/router.py` | ✅ Done |
| T4.5 | Implement `GET /users/me` (full user profile) | `src/platform/auth/router.py` | ✅ Done |
| T4.6 | Implement `PUT /auth/change-password` with `ChangePasswordRequest` | `src/platform/auth/router.py` | ✅ Done |
| T4.7 | Implement admin-only demo endpoint `GET /users/me/admin` | `src/platform/auth/router.py` | ✅ Done |

## Phase 5: Dependencies (RBAC)

| Task | Description | File | Status |
|------|-------------|------|--------|
| T5.1 | Implement `get_current_user` FastAPI dependency | `src/dependencies.py` | ✅ Done |
| T5.2 | Implement `require_role(*roles)` dependency factory | `src/dependencies.py` | ✅ Done |
| T5.3 | Wire `_bearer_scheme = HTTPBearer(auto_error=False)` | `src/dependencies.py` | ✅ Done |

## Phase 6: Tests

| Task | Description | Status |
|------|-------------|--------|
| T6.1 | Unit tests: bcrypt hash/verify round-trip | ✅ Done |
| T6.2 | Unit tests: JWT encode/decode round-trip | ✅ Done |
| T6.3 | Unit tests: register with duplicate username → 409 | ✅ Done |
| T6.4 | Unit tests: login with wrong password → 401 | ✅ Done |
| T6.5 | Unit tests: refresh with access token → 401 | ✅ Done |
| T6.6 | Unit tests: require_role denies wrong role → 403 | ✅ Done |
| T6.7 | Unit tests: missing Authorization header → 401 | ✅ Done |
| T6.8 | Integration tests: full register → login → auth/me flow | ✅ Done |
