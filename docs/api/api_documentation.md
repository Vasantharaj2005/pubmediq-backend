# PubMedIQ Backend — Frontend API Documentation

> **Base URL:** `http://localhost:8000` (development) | `https://api.pubmediq.io` (production)  
> **API Version:** `v1`  
> **All endpoints are prefixed with** `/api/v1`  
> **Interactive Docs:** `http://localhost:8000/docs` (Swagger UI) | `http://localhost:8000/redoc`

---

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [Request / Response Format](#request--response-format)
3. [Error Handling](#error-handling)
4. [Endpoints Reference](#endpoints-reference)
   - [Health](#health)
   - [Authentication](#authentication)
   - [Search](#search)
   - [Papers](#papers)
   - [Research (AI Tools)](#research-ai-tools)
   - [History](#history)
   - [Feedback](#feedback)
   - [Users](#users)
5. [Common Data Types](#common-data-types)
6. [Quick-Start Recipes](#quick-start-recipes)

---

## Authentication Flow

PubMedIQ uses **JWT Bearer tokens**. Here is the standard lifecycle:

```
Register / Login
      ↓
  access_token  (expires in 30 min)
  refresh_token (expires in 7 days)
      ↓
All protected requests:
  Authorization: Bearer <access_token>
      ↓
Token about to expire?
  POST /auth/refresh  →  new access_token + refresh_token
      ↓
Logout:
  POST /auth/logout  →  token blacklisted
```

> **⚠️ Important:** The search endpoint works **with or without** a token. Authenticated users get their results saved to history automatically. Anonymous users do not.

---

## Request / Response Format

| Item | Value |
|---|---|
| Content-Type | `application/json` |
| Accept | `application/json` |
| Auth Header | `Authorization: Bearer <token>` |
| Request ID | Echoed back in `X-Request-ID` response header |
| Timestamps | ISO 8601 UTC strings (`2026-08-13T15:30:55.894038Z`) |

---

## Error Handling

All errors follow this shape:

```json
{
  "detail": "Human-readable message"
}
```

Or for validation errors (422):

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

| HTTP Code | Meaning |
|---|---|
| `200` | Success |
| `201` | Resource created |
| `204` | Success, no body (DELETE) |
| `400` | Bad request / business logic error |
| `401` | Missing or invalid token |
| `403` | Valid token but no permission |
| `404` | Resource not found |
| `422` | Validation error (schema mismatch) |
| `429` | Rate limited |
| `500` | Server error |

---

## Endpoints Reference

---

## Health

> No authentication required.

### `GET /api/v1/health` — Basic health check

Returns `200` if the API server is running.

**Response `200`**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "dependencies": null
}
```

---

### `GET /api/v1/health/ready` — Readiness check

Checks all external dependencies: PostgreSQL, Redis, and Pinecone.

**Response `200`**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "dependencies": {
    "database": true,
    "redis": true,
    "pinecone": false
  }
}
```

> `status` will be `"degraded"` if the database is down. Redis and Pinecone failures are non-fatal (graceful degradation).

---

### `GET /api/v1/health/live` — Kubernetes liveness probe

Minimal liveness check for container orchestration.

**Response `200`**
```json
{ "status": "alive" }
```

---

## Authentication

### `POST /api/v1/auth/register` — Register new user

Creates a new user account and returns tokens immediately (no separate login step needed).

**Request Body**
```json
{
  "email": "researcher@university.edu",
  "password": "SecurePass123!",
  "full_name": "Dr. Jane Smith"
}
```

| Field | Type | Constraints |
|---|---|---|
| `email` | `string` | Valid email, unique |
| `password` | `string` | Min 8, max 128 characters |
| `full_name` | `string` | Min 2, max 100 characters |

**Response `201`**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

| Field | Description |
|---|---|
| `access_token` | Short-lived JWT — use for all API calls |
| `refresh_token` | Long-lived JWT — use only for `/auth/refresh` |
| `token_type` | Always `"bearer"` |
| `expires_in` | Access token lifetime in seconds (`1800` = 30 min) |

**Errors**
- `400` — Email already registered

---

### `POST /api/v1/auth/login` — Login

**Request Body**
```json
{
  "email": "researcher@university.edu",
  "password": "SecurePass123!"
}
```

**Response `200`** — Same shape as `/register`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors**
- `401` — Invalid credentials

---

### `POST /api/v1/auth/refresh` — Refresh token

Exchange a valid refresh token for a new access/refresh token pair. The submitted refresh token is immediately revoked (rotation strategy).

**Request Body**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200`** — Same shape as `/login`

**Errors**
- `401` — Refresh token expired, invalid, or already revoked

---

### `POST /api/v1/auth/logout` — Logout

**Required:** `Authorization: Bearer <access_token>`

Revokes the current access token. All future requests with this token will return `401`.

**Request Body** — None

**Response `200`**
```json
{ "message": "Successfully logged out." }
```

---

### `GET /api/v1/auth/me` — Get current user

**Required:** `Authorization: Bearer <access_token>`

**Response `200`**
```json
{
  "id": "ce10c82d-f51f-4bfe-b3c2-03abc72ea937",
  "email": "researcher@university.edu",
  "full_name": "Dr. Jane Smith",
  "is_active": true,
  "created_at": "2026-08-13T08:00:00Z"
}
```

---

## Search

> The core feature. Works anonymously **or** authenticated.

### `POST /api/v1/search` — Hybrid PubMed Search

Runs the full PubMedIQ AI pipeline:

```
1. Query Understanding (LLM) — extracts PICO intent
2. Concept Mapping (LLM)    — expands to biomedical facets + MeSH terms
3. Query Planning (logic)   — builds keyword + MeSH + semantic queries
4. Parallel Retrieval       — keyword search + MeSH search + vector search
5. Fusion (RRF)             — Reciprocal Rank Fusion across 3 sources
6. Re-ranking               — CrossEncoder model scoring
7. Quality Gate             — auto-refines if quality < threshold
8. Answer Generation (LLM)  — evidence-grounded summary with citations
```

**Optional:** `Authorization: Bearer <access_token>` (saves to history if provided)

**Request Body**
```json
{
  "query": "treatments for Alzheimer's disease",
  "filters": {
    "year_from": 2020,
    "year_to": 2025,
    "study_type": "randomized_controlled_trial",
    "journal": "NEJM"
  },
  "top_k": 20,
  "mode": "hybrid",
  "session_id": "abc-123"
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | `string` | ✅ | — | Natural language biomedical query. Min 3, max 1000 chars. |
| `filters` | `SearchFilters` | ❌ | `null` | Optional search filters (see below) |
| `top_k` | `integer` | ❌ | `20` | Number of results to return. Range: 1–100 |
| `mode` | `enum` | ❌ | `"hybrid"` | `"hybrid"` \| `"keyword"` \| `"semantic"` \| `"mesh"` |
| `session_id` | `string` | ❌ | auto-generated | For follow-up questions. Pass the returned `session_id` back. |

**`SearchFilters` object**

| Field | Type | Description | Example |
|---|---|---|---|
| `year_from` | `integer` | Filter from this publication year | `2020` |
| `year_to` | `integer` | Filter up to this publication year | `2025` |
| `study_type` | `enum` | Filter by publication type | `"randomized_controlled_trial"` |
| `journal` | `string` | Filter by journal name | `"NEJM"` |

**`study_type` valid values**

| Value | PubMed type |
|---|---|
| `randomized_controlled_trial` | Randomized Controlled Trial |
| `systematic_review` | Systematic Review |
| `meta_analysis` | Meta-Analysis |
| `clinical_trial` | Clinical Trial |
| `observational` | Observational Study |
| `cohort_study` | Cohort Study |
| `case_control` | Case-Control Studies |
| `review` | Review |
| `case_report` | Case Reports |
| `any` | No filter |

---

**Response `200`**
```json
{
  "session_id": "abc-123",
  "query": "treatments for Alzheimer's disease",
  "intent": {
    "population": null,
    "intervention": null,
    "condition": "Alzheimer's disease",
    "outcome": null,
    "study_type": null,
    "timeframe": null
  },
  "results": [
    {
      "pmid": "41350162",
      "title": "A Randomized Controlled Trial of the Safety and Efficacy of Dronabinol for Agitation in Alzheimer's Disease.",
      "abstract": "Agitation in Alzheimer's disease (AD) is a great source...",
      "authors": ["Paul B Rosenberg", "Halima Amjad", "..."],
      "journal": "The American journal of geriatric psychiatry",
      "year": 2026,
      "score": 0.9776,
      "semantic_score": null,
      "keyword_score": null,
      "mesh_score": null,
      "pub_types": [
        "Clinical Trial, Phase II",
        "Randomized Controlled Trial"
      ],
      "mesh_terms": [
        "Aged",
        "Alzheimer Disease",
        "Dronabinol"
      ],
      "match_reasons": ["keyword"],
      "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/41350162/"
    }
  ],
  "total_results": 20,
  "search_strategy": {
    "keyword_query": "(\"Alzheimer's disease\" OR \"Alzheimer disease\")",
    "mesh_query": "\"Alzheimer Disease\"[MeSH]",
    "semantic_search": true,
    "mesh_terms": ["Alzheimer Disease"],
    "concepts": []
  },
  "quality": {
    "score": 0.9776,
    "level": "high",
    "refined": false,
    "refinement_count": 0
  },
  "ai_summary": "Based on recent PubMed literature, treatments for Alzheimer's disease...",
  "citations": ["41350162", "42134889"],
  "cached": false
}
```

**Response field descriptions:**

| Field | Description |
|---|---|
| `session_id` | Pass this back for follow-up questions via `/research/ask` |
| `intent` | Structured PICO extraction from the query |
| `results` | Array of `PaperResult` objects, sorted by `score` descending |
| `total_results` | Count of results in this response |
| `search_strategy` | Shows exactly which queries were sent to PubMed |
| `quality.score` | Reranker score 0.0–1.0 (higher = more relevant) |
| `quality.level` | `"high"` (≥0.80) \| `"medium"` (≥0.65) \| `"low"` (<0.65) |
| `quality.refined` | `true` if the pipeline automatically retried with a better query |
| `ai_summary` | AI-generated evidence summary with inline `[PMID: XXXXX]` citations |
| `citations` | Deduplicated list of PMIDs cited in the AI summary |
| `cached` | `true` if this response was served from Redis cache |

**`PaperResult` field descriptions:**

| Field | Type | Description |
|---|---|---|
| `pmid` | `string` | PubMed article ID — use for `/papers/{pmid}` |
| `title` | `string?` | Article title |
| `abstract` | `string?` | Full abstract text |
| `authors` | `string[]` | Author names |
| `journal` | `string?` | Journal full name |
| `year` | `integer?` | Publication year |
| `score` | `float` | Final rerank score (0.0–1.0) |
| `pub_types` | `string[]` | Publication type tags from PubMed |
| `mesh_terms` | `string[]` | MeSH controlled vocabulary terms |
| `match_reasons` | `string[]` | Which sources found this: `"keyword"`, `"mesh"`, `"semantic"` |
| `pubmed_url` | `string` | Direct PubMed link |

---

### `POST /api/v1/search/refine` — Refine an existing search

Manually re-run refinement on a previous session when results were unsatisfactory.

**Optional:** `Authorization: Bearer <access_token>`

**Request Body**
```json
{
  "session_id": "abc-123",
  "feedback": "Too broad — I only want clinical trials"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | `string` | ✅ | From a previous `/search` response |
| `feedback` | `string?` | ❌ | Optional hint for the LLM refiner |

**Response `200`** — Same shape as `/search`

---

## Papers

> Requires `Authorization: Bearer <access_token>` for save/unsave/list-saved. The `GET /{pmid}` endpoint is accessible anonymously.

### `GET /api/v1/papers/{pmid}` — Get full article metadata

Fetch complete metadata for a PubMed article. Results are cached in Redis for 24 hours.

**Path Parameter:** `pmid` — PubMed article ID (e.g., `41350162`)

**Optional:** `Authorization: Bearer <access_token>` (returns `is_saved` field if authenticated)

**Response `200`**
```json
{
  "pmid": "41350162",
  "title": "A Randomized Controlled Trial of the Safety and Efficacy of Dronabinol...",
  "abstract": "Agitation in Alzheimer's disease (AD) is a great source...",
  "authors": ["Paul B Rosenberg", "Halima Amjad"],
  "journal": "The American journal of geriatric psychiatry",
  "journal_abbr": "Am J Geriatr Psychiatry",
  "year": 2026,
  "pub_types": ["Clinical Trial, Phase II", "Randomized Controlled Trial"],
  "mesh_terms": ["Aged", "Alzheimer Disease", "Dronabinol"],
  "keywords": ["agitation", "dronabinol", "THC"],
  "doi": "10.1016/j.jagp.2026.03.001",
  "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/41350162/",
  "is_saved": false
}
```

**Errors**
- `404` — PMID not found in PubMed

---

### `GET /api/v1/papers/saved` — List saved papers

**Required:** `Authorization: Bearer <access_token>`

**Response `200`**
```json
[
  {
    "pmid": "41350162",
    "title": "A Randomized Controlled Trial...",
    "journal": "The American journal of geriatric psychiatry",
    "year": 2026,
    "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/41350162/"
  }
]
```

---

### `POST /api/v1/papers/{pmid}/save` — Save a paper

**Required:** `Authorization: Bearer <access_token>`

**Response `201`**
```json
{
  "pmid": "41350162",
  "saved": true,
  "message": "Paper saved to your library."
}
```

---

### `DELETE /api/v1/papers/{pmid}/save` — Remove a saved paper

**Required:** `Authorization: Bearer <access_token>`

**Response `200`**
```json
{
  "pmid": "41350162",
  "saved": false,
  "message": "Paper removed from your library."
}
```

---

## Research (AI Tools)

> All endpoints require `Authorization: Bearer <access_token>`. These are LLM-powered analysis tools.

### `POST /api/v1/research/summarize` — Summarize papers

Generate a concise evidence-based summary for 1–10 PubMed articles.

**Request Body**
```json
{
  "pmids": ["41350162", "42134889", "41920139"],
  "focus": "methodology"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `pmids` | `string[]` | ✅ | 1–10 PubMed IDs |
| `focus` | `string?` | ❌ | Optional focus area e.g. `"outcomes"`, `"sample size"` |

**Response `200`**
```json
{
  "answer": "Across three studies of Alzheimer's disease treatments...",
  "citations": ["[PMID: 41350162]", "[PMID: 42134889]"],
  "pmids_used": ["41350162", "42134889"],
  "confidence": 0.87
}
```

---

### `POST /api/v1/research/compare` — Compare papers

Systematically compare 2–5 PubMed articles on key dimensions.

**Request Body**
```json
{
  "pmids": ["41350162", "41451887"],
  "aspect": "sample size and outcomes"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `pmids` | `string[]` | ✅ | 2–5 PubMed IDs |
| `aspect` | `string?` | ❌ | Comparison dimension e.g. `"intervention"`, `"sample size"` |

**Response `200`** — Same shape as `/summarize`

---

### `POST /api/v1/research/gap-analysis` — Research gap analysis

Identify research gaps and unanswered questions from a corpus of papers.

**Request Body**
```json
{
  "pmids": ["41350162", "42134889", "41920139", "41451887"],
  "topic": "Alzheimer's disease pharmacological treatments"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `pmids` | `string[]` | ✅ | 3–20 PubMed IDs |
| `topic` | `string?` | ❌ | Topic context for gap analysis |

**Response `200`** — Same shape as `/summarize`

---

### `POST /api/v1/research/ask` — Follow-up question

Ask a specific follow-up question about a previous search session. The pipeline retrieves the cached search context and uses it to answer.

**Request Body**
```json
{
  "session_id": "abc-123",
  "question": "Which study had the largest sample size?"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | `string` | ✅ | From a previous `/search` response |
| `question` | `string` | ✅ | Your question. Min 3, max 1000 chars |

**Response `200`** — Same shape as `/summarize`

---

## History

> All endpoints require `Authorization: Bearer <access_token>`.

### `GET /api/v1/history` — Get search history

Returns the authenticated user's search history, newest first.

**Response `200`**
```json
[
  {
    "id": "767c6688-9c13-46e1-8e68-f900ec39444e",
    "query": "treatments for Alzheimer's disease",
    "results_count": 20,
    "quality_score": 0.9776,
    "refined": false,
    "created_at": "2026-08-13T15:50:30.000000Z"
  }
]
```

---

### `DELETE /api/v1/history/{record_id}` — Delete a history record

**Path Parameter:** `record_id` — UUID from the history list

**Response `204`** — No content

**Errors**
- `404` — Record not found or doesn't belong to user

---

## Feedback

> Authentication is optional — feedback can be submitted anonymously.

### `POST /api/v1/feedback` — Submit feedback

Submit a rating and optional comment for a search session.

**Optional:** `Authorization: Bearer <access_token>`

**Request Body**
```json
{
  "rating": 4,
  "comment": "Great results, but could use more recent papers.",
  "session_id": "abc-123",
  "query": "treatments for Alzheimer's disease"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `rating` | `integer` | ✅ | 1 (worst) to 5 (best) |
| `comment` | `string?` | ❌ | Max 2000 characters |
| `session_id` | `string?` | ❌ | Links feedback to a search session |
| `query` | `string?` | ❌ | The search query that was rated |

**Response `201`**
```json
{
  "id": "a1b2c3d4-...",
  "rating": 4,
  "created_at": "2026-08-13T15:52:00Z",
  "message": "Thank you for your feedback!"
}
```

---

## Users

> All endpoints require `Authorization: Bearer <access_token>`.

### `GET /api/v1/users/me` — Get user profile

**Response `200`**
```json
{
  "id": "ce10c82d-f51f-4bfe-b3c2-03abc72ea937",
  "email": "researcher@university.edu",
  "full_name": "Dr. Jane Smith",
  "is_active": true,
  "created_at": "2026-08-13T08:00:00Z",
  "last_login_at": "2026-08-13T15:30:00Z"
}
```

---

### `PATCH /api/v1/users/me` — Update user profile

Currently allows updating `full_name`.

**Request Body**
```json
{
  "full_name": "Dr. Jane A. Smith"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `full_name` | `string?` | ❌ | Min 2, max 100 characters |

**Response `200`** — Same shape as `GET /users/me`

---

## Common Data Types

### `HealthStatus`
```json
{
  "status": "ok | degraded",
  "version": "0.1.0",
  "dependencies": {
    "database": true,
    "redis": true,
    "pinecone": false
  }
}
```

### `SearchIntent` (PICO structure)
```json
{
  "population": "elderly patients | null",
  "intervention": "exercise | null",
  "condition": "Alzheimer's disease | null",
  "outcome": "cognitive improvement | null",
  "study_type": "randomized controlled trial | null",
  "timeframe": "last 5 years | null"
}
```

### `SearchQuality`
```json
{
  "score": 0.9776,
  "level": "high | medium | low",
  "refined": false,
  "refinement_count": 0
}
```

---

## Quick-Start Recipes

### 1. Register and search (authenticated)

```javascript
// Step 1: Register
const res = await fetch('/api/v1/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123!',
    full_name: 'Dr. Smith'
  })
});
const { access_token, refresh_token } = await res.json();

// Step 2: Search
const search = await fetch('/api/v1/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    query: "treatments for Alzheimer's disease",
    top_k: 20
  })
});
const data = await search.json();
// data.results → array of papers
// data.ai_summary → AI-generated narrative
// data.session_id → save for follow-ups
```

### 2. Anonymous search (no account needed)

```javascript
const search = await fetch('/api/v1/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "exercise and depression in elderly patients",
    filters: { year_from: 2020, study_type: "randomized_controlled_trial" },
    top_k: 10
  })
});
const data = await search.json();
```

### 3. Refresh token before expiry

```javascript
const tryRefresh = async () => {
  const res = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: storedRefreshToken })
  });
  if (res.ok) {
    const { access_token, refresh_token } = await res.json();
    // Store new tokens
  }
};
```

### 4. Ask a follow-up question

```javascript
// After getting a search result with session_id = "abc-123"
const followUp = await fetch('/api/v1/research/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    session_id: 'abc-123',
    question: 'Which study had the largest sample size?'
  })
});
const { answer, citations } = await followUp.json();
```

### 5. Save a paper from search results

```javascript
const pmid = data.results[0].pmid; // from search result
await fetch(`/api/v1/papers/${pmid}/save`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${access_token}` }
});
```

---

## Rate Limits

| Endpoint Group | Limit |
|---|---|
| General API | 100 requests / minute per IP |
| Search (`/api/v1/search`) | 20 requests / minute per user |

---

## CORS

The API allows requests from the following origins in development:
- `http://localhost:3000`
- `http://localhost:3001`

Credentials (cookies/auth headers) are allowed. The `X-Request-ID` header is exposed.