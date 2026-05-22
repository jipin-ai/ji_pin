# Knowledge Base — Functional Requirements (EARS)

## KB-REQ-001: Create Knowledge Entry
- **WHEN** an authenticated user submits a POST request to `/api/knowledge` with a valid title, content body, and optional tags
- **THE SYSTEM SHALL** validate the input, create a new knowledge entry with a unique UUID, set the author to the current user, and return the entry with HTTP 201.

## KB-REQ-002: Retrieve Knowledge Entry
- **WHEN** an authenticated user submits a GET request to `/api/knowledge/{entry_id}`
- **THE SYSTEM SHALL** return the full entry (title, body, tags, author, created_at, updated_at) with HTTP 200, or HTTP 404 if not found.

## KB-REQ-003: List Knowledge Entries
- **WHEN** an authenticated user submits a GET request to `/api/knowledge` with optional query parameters `?tags=...`, `?search=...`, `?page=...`, `?limit=...`
- **THE SYSTEM SHALL** return a paginated list of knowledge entries matching the filters, sorted by most recently updated, with HTTP 200.

## KB-REQ-004: Update Knowledge Entry
- **WHEN** an authenticated user submits a PUT request to `/api/knowledge/{entry_id}` with updated fields (title, body, or tags)
- **THE SYSTEM SHALL** validate the input, update the entry, bump the `updated_at` timestamp, and return the updated entry with HTTP 200.

## KB-REQ-005: Delete Knowledge Entry
- **WHEN** an authenticated user submits a DELETE request to `/api/knowledge/{entry_id}`
- **THE SYSTEM SHALL** soft-delete the entry (set `deleted_at`), return HTTP 204, and exclude soft-deleted entries from list/search results.

## KB-REQ-006: Full-Text Search
- **WHEN** an authenticated user provides a `?search=` query parameter on the list endpoint
- **THE SYSTEM SHALL** perform a full-text search across entry titles and bodies using database-level text search (e.g., PostgreSQL `tsvector`/`tsquery`), rank results by relevance, and return them paginated.

## KB-REQ-007: Tag Filtering
- **WHEN** an authenticated user provides a `?tags=` query parameter (comma-separated tag slugs) on the list endpoint
- **THE SYSTEM SHALL** filter entries to those matching ALL specified tags (AND logic), returning only entries that have every specified tag.

## KB-REQ-008: Entry Versioning
- **WHEN** a knowledge entry is updated via PUT
- **THE SYSTEM SHALL** preserve the previous version in a `knowledge_entry_versions` table with a version number, the prior content, and a timestamp, so full history is recoverable.

## KB-REQ-009: Link Entry to Project
- **WHEN** an authenticated user submits a POST request to `/api/knowledge/{entry_id}/link` with `{"project_id": "..."}`
- **THE SYSTEM SHALL** create an association record linking the knowledge entry to the project, enabling bidirectional navigation (project → used entries, entry → used in projects).

## KB-REQ-010: Input Validation
- **WHEN** creating or updating a knowledge entry
- **THE SYSTEM SHALL** enforce: title is required (1–500 chars), body is required (1–100,000 chars), tags are optional (max 20 tags, each 1–100 chars, alphanumeric + hyphens only). Invalid input shall return HTTP 422 with field-level error messages.
