# Auth System — Design Document

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          HTTP Request                            │
│   Authorization: Bearer eyJ...                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  HTTPBearer      │  ← FastAPI security scheme
                   │  (auto_error=False)│
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  get_current_user│  ← FastAPI dependency
                   │  (dependencies.py)│
                   │                   │
                   │  1. Extract token │
                   │  2. Decode JWT    │
                   │  3. Verify type   │
                   │  4. Load user     │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
     ┌────────▼────────┐   │    ┌────────▼────────┐
     │  require_role()  │   │    │  Router          │
     │  (dependencies)  │   │    │  (router.py)     │
     │                   │   │    │                   │
     │  Checks user.role │   │    │  POST /register  │
     │  ∈ allowed set    │   │    │  POST /login     │
     │  403 if denied    │   │    │  POST /refresh   │
     └──────────────────┘   │    │  GET  /auth/me   │
                            │    │  GET  /users/me  │
                            │    │  PUT  /change-pwd │
                            │    └──────────────────┘
                            │
                   ┌────────▼────────┐
                   │  AuthService     │
                   │  (service.py)    │
                   │                   │
                   │  register()       │
                   │  login()          │
                   │  refresh_token()  │
                   │  get_current_user()│
                   │  change_password() │
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  Database        │
                   │  (users table)   │
                   │                   │
                   │  username (unique)│
                   │  password_hash    │
                   │  role (enum)      │
                   │  must_change_pwd  │
                   └──────────────────┘
```

## 1. Token Flow

### Login → Token Pair

```
POST /auth/login {username, password}
    │
    ▼
AuthService.login()
    │
    ├── SELECT user WHERE username = :username
    ├── bcrypt.checkpw(plain, hashed)
    │     └── False → HTTP 401 "Invalid username or password"
    │
    └── _create_token_pair(username)
          │
          ├── access_token = _create_token(username, "access", 24h)
          │     └── jwt.encode({sub, type:"access", iat, exp}, secret, HS256)
          │
          └── refresh_token = _create_token(username, "refresh", 7d)
                └── jwt.encode({sub, type:"refresh", iat, exp}, secret, HS256)
                     │
                     ▼
          TokenResponse {
              access_token: "eyJ...",
              refresh_token: "eyJ...",
              token_type: "bearer",
              must_change_password: true|false
          }
```

### Access Token Structure (HS256 JWT)

```json
{
  "sub": "alice",
  "type": "access",
  "iat": 1714600000,
  "exp": 1714686400
}
```

### Refresh Token Structure (HS256 JWT)

```json
{
  "sub": "alice",
  "type": "refresh",
  "iat": 1714600000,
  "exp": 1715204800
}
```

### Token Refresh Flow

```
POST /auth/refresh {refresh_token}
    │
    ▼
AuthService.refresh_token()
    │
    ├── _decode_token(refresh_token)
    │     └── jwt.decode(..., algorithms=["HS256"])
    │         └── JWTError → HTTP 401
    │
    ├── payload["type"] != "refresh" → HTTP 401
    ├── SELECT user WHERE username = payload["sub"]
    │     └── None → HTTP 401 "User no longer exists"
    │
    └── _create_token_pair(username) → new TokenPair
```

## 2. Password Hashing

### Why bcrypt (via direct `bcrypt` import)?

- **Industry standard**: OWASP-recommended for password storage
- **Adaptive**: `gensalt()` uses 2^12 rounds by default (configurable)
- **Salt built-in**: no separate salt storage needed
- **Not passlib**: `passlib` has Python 3.13+ compatibility issues; direct
  `bcrypt` import avoids the dependency problem

### Hashing Flow

```python
@staticmethod
def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

@staticmethod
def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
```

- `checkpw()` uses constant-time comparison — resistant to timing attacks
- Hash format: `$2b$12$...` (12 = log2 rounds)

## 3. RBAC — `require_role()` Decorator Pattern

### Dependency Chain

```python
# Step 1: Extract and validate token, load user
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    # ... validates token, returns User

# Step 2: Role check factory
def require_role(*roles: str):
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(403, f"Requires one of roles: {', '.join(roles)}")
        return current_user
    return role_checker
```

### Usage Examples

```python
# Admin-only endpoint
@router.get("/users/me/admin")
async def get_me_admin(user: User = Depends(require_role("admin"))):
    return {"username": user.username, "role": user.role}

# Multi-role endpoint
@router.delete("/documents/{id}")
async def delete_doc(
    doc_id: str,
    user: User = Depends(require_role("admin", "bid_editor")),
):
    ...
```

### Role Hierarchy

| Role        | Permissions                                          |
|-------------|------------------------------------------------------|
| `admin`     | Full access: user management, system config, all data |
| `reviewer`  | Read all documents, create review sessions, comment  |
| `bid_editor`| Upload/edit bid documents, manage project files      |
| `viewer`    | Read-only access to assigned projects                |

## 4. API Endpoints

| Method | Path                    | Auth Required | RBAC    | Description                  |
|--------|-------------------------|---------------|---------|------------------------------|
| POST   | `/auth/register`        | No            | —       | Create new user account      |
| POST   | `/auth/login`           | No            | —       | Authenticate, get tokens     |
| POST   | `/auth/refresh`         | No (token)   | —       | Exchange refresh for new pair |
| GET    | `/auth/me`              | Yes           | Any     | Current user info (lightweight) |
| GET    | `/users/me`             | Yes           | Any     | Current user profile (full)  |
| PUT    | `/auth/change-password` | Yes           | Any     | Change own password          |
| GET    | `/users/me/admin`       | Yes           | admin   | Admin-only user info         |

## 5. Configuration

All JWT parameters are in `src/config.py`:

```python
class Settings(BaseSettings):
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24        # 24 hours
    refresh_token_expire_minutes: int = 60 * 24 * 7   # 7 days
```

### Production Hardening

- **`jwt_secret`**: Must be set via env var `JWT_SECRET` to ≥32 bytes of
  cryptographically random data
- **`jwt_algorithm`**: Use `"HS256"` for single-service deployments;
  `"RS256"` (asymmetric) for multi-service if needed in future
- **Token expiry**: Shorten `access_token_expire_minutes` to 15-60 min in
  production; rely on refresh tokens for session longevity

## 6. Service Design

`AuthService` is a **stateless singleton** (`auth_service = AuthService()` at
module level). All methods are instance methods that receive dependencies
(`db`, `settings`) as parameters — no global state, fully testable.

```python
class AuthService:
    # Password helpers (static)
    _hash_password(password: str) -> str
    _verify_password(plain: str, hashed: str) -> bool

    # Token helpers (static)
    _create_token(username, type, expires_delta, settings) -> str
    _decode_token(token, settings) -> dict

    # Token pair factory (instance)
    _create_token_pair(username, settings) -> TokenPair

    # Service methods (instance, async)
    async register(db, data, settings) -> User
    async login(db, data, settings) -> TokenPair
    async refresh_token(db, refresh_token, settings) -> TokenPair
    async get_current_user(db, token, settings) -> User
    async change_password(db, user, new_password) -> None
```

## Technology Decisions

| Decision                      | Rationale                                           |
|-------------------------------|-----------------------------------------------------|
| HS256 (symmetric JWT)         | Simple for single-service; avoids RSA key management|
| `bcrypt` direct import        | Avoids `passlib` Python 3.13+ compatibility issues  |
| Token type claim (`"type"`)   | Prevents refresh-token-as-access-token misuse       |
| Stateless service             | No server-side session store; scales horizontally   |
| `must_change_password` flag   | First-login enforcement without out-of-band channel |
| Pydantic v2 `from_attributes` | ORM model → response schema auto-conversion         |
