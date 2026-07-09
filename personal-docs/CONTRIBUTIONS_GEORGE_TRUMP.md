# George Trump — Dishify Contributions

**Author:** George Trump (`georgetrump` / `gergetrump`)  
**Email:** george.jin@tum.de  
**Period:** April 2026 – June 2026  
**Repository:** [gergetrump/dishify](https://github.com/gergetrump/dishify)

---

## Executive Summary

George Trump is a **founding contributor and primary architect** of Dishify, an AI-powered recipe recommendation platform. Over roughly three months, he built the core recommendation engine—from vector search and dietary hard-filtering through inventory-based re-ranking and optional LLM reasoning—and then led a major repo restructure that established the current microservices backend, API contract, iOS client, and team collaboration workflow.

His work spans **461 files touched**, with **~28,400 lines added** across backend services, shared libraries, notebooks, infrastructure, documentation, and a production-grade SwiftUI iOS app.

---

## What Dishify Is

Dishify recommends recipes based on:

1. **Ingredients the user has** (pantry inventory)
2. **Natural-language queries** (“something quick and spicy”)
3. **Hard dietary constraints** (allergies, vegetarian, halal, etc.)

The pipeline George designed and implemented:

```
User query + pantry + restrictions
        ↓
   Vector retrieval (Qdrant, 2.2M recipes)
        ↓
   Hard filtering (allergy / diet tags)
        ↓
   Inventory re-ranking (match available ingredients)
        ↓
   Optional LLM reasoning (explain fit + substitutions)
        ↓
   Ranked recipe results with explanations
```

This pipeline is codified in `notebooks/end_to_end_pipeline.ipynb` and mirrored in the production microservices under `backend/services/`.

---

## Contribution Timeline

| Period | Focus |
|--------|-------|
| **Apr 2026** | Project initialization, README, CI scaffolding, normalization service stub |
| **May 2026** | Vector DB (Qdrant), retrieval, hard filtering, ranking, LLM reasoning, end-to-end notebook |
| **Jun 2026** | Repo cleanup & MVP restructure, microservices architecture, iOS app, Keycloak, 2M-recipe scale-up, documentation |
| **Post-Jun 2026** | Core pipeline unchanged; teammates added auth hardening, web/iOS polish, CI/CD deployment, multimodal ingest, recipe augment |

### Commits by Month

| Month | Commits |
|-------|---------|
| 2026-04 | 3 |
| 2026-05 | 10 |
| 2026-06 | 14 |
| **Total** | **27** (excluding merge commits) |

---

## Major Areas of Work

### 1. Project Foundation (April 2026)

**Commits:** `init`, `init2`, `readme updated`

- Created the initial repository structure with FastAPI backend stubs, Docker Compose, and service placeholders (`retrieval`, `ranking`, `explanation`, `normalization`).
- Added CI workflow (`.github/workflows/ci.yml`), `.gitignore`, and `.env.example`.
- Wrote the first project README describing the Dishify vision and setup.

---

### 2. Vector Search & Retrieval Engine (May 2026)

**Commits:**
- `qdrant cloud set up and smoke test for indexing 10000 recipes and retrieval successful`
- `migrated vector_db and models into backend/app. hard filtering works successfully`
- `created a search endpoint for testing retrieval of vector db`
- `included filtering for excluded_ingredients in the retrieval. weighted the title of a recipe 2x for indexing for better retrieval quality`
- `fixed qdrant. moved away from qdrant cloud to local`

**What was built:**

| Component | Location | Description |
|-----------|----------|-------------|
| `RecipeVectorStore` | `backend/shared/dishify-vector-store/` | Qdrant client wrapper with SentenceTransformer embeddings (`all-MiniLM-L6-v2`) |
| Recipe parsing | `backend/app/vector_db/parsing.py` | CSV → structured recipe objects with NER ingredients |
| Indexing pipeline | `backend/services/indexing/` | Batch upload of recipe vectors to Qdrant |
| Retrieval service | `backend/services/retrieval/` | FastAPI service exposing semantic search |
| Search API | `backend/app/api/routes/recipe.py` | HTTP endpoint for testing retrieval |

**Key technical decisions:**

- **Title 2× weighting** in embedding text to improve retrieval quality for named dishes.
- **Payload indexes** on Qdrant for fast hard-filter queries (allergy/diet tags).
- **Migration from Qdrant Cloud → local Docker** for cost control and team reproducibility.
- **Shared `dishify-vector-store` library** extracted for reuse across indexing and retrieval services.

---

### 3. Hard Filtering (Allergies & Dietary Restrictions) (May 2026)

**Commits:**
- `functioning hard filter with allergies`
- `included filtering for excluded_ingredients in the retrieval`

**What was built:**

- Qdrant `Filter` conditions using `MatchAny` on payload fields for restriction tags.
- Integration with `data/restriction_rules.json` (allergy and diet rule definitions).
- Support for `exclusion_restrictions` in the retrieval API (e.g. `nut_allergy`, `vegetarian`, `halal`).
- Test coverage in `backend/app/vector_db/retrieval_test.py` validating filtered results.

Hard filtering ensures recipes containing forbidden ingredients or violating dietary rules are **never returned**, regardless of semantic similarity.

---

### 4. Post-Retrieval Ranking (May 2026)

**Commit:** `created a first version of post-retrieval ranking`

**What was built:**

| Component | Location | Description |
|-----------|----------|-------------|
| `score_recipes_by_inventory` | `backend/shared/dishify-ranking/dishify_ranking/ranking.py` | Re-ranks retrieved recipes by pantry overlap |
| Search orchestration | `backend/app/services/search.py` | Combines retrieval + ranking in one call |
| API models | `backend/app/models/api.py`, `retrieval.py` | Request/response schemas |

**Ranking logic:**

- Compares user's available ingredients against recipe NER-parsed ingredients.
- Weighted score: **70% semantic similarity + 30% inventory match**.
- Tracks `inventory_matched` and `inventory_missing` per recipe for downstream LLM reasoning.
- Optional quantity/unit checks when pantry items include amounts.

---

### 5. LLM Reasoning Layer (May 2026)

**Commits:**
- `end_to_end_pipeline notebook created and tested`
- `end to end pipeline notebook`
- `fixed llm reasoning in notebook`

**What was built:**

| Component | Location | Description |
|-----------|----------|-------------|
| `llm_reasoning.py` | `backend/services/reasoning/app/` | OpenRouter/Gemini integration for recipe explanations |
| `chatbot_reasoning.ipynb` | `notebooks/` | Prototype for LLM prompt design |
| `end_to_end_pipeline.ipynb` | `notebooks/` | Full pipeline demo: retrieve → rank → explain |

**LLM output per recipe:**

- **Positive reasoning** — why the recipe fits (ingredient match, dietary compliance).
- **Negative reasoning** — missing ingredients, potential substitutions.
- **Fallback reasoning** — deterministic explanations when LLM is unavailable.

---

### 6. End-to-End Pipeline Notebook (May 2026)

**File:** `notebooks/end_to_end_pipeline.ipynb`

George created and iteratively refined the **reference implementation** of the Dishify recommendation pipeline. This notebook:

- Loads recipes from the annotated dataset.
- Runs vector retrieval against Qdrant.
- Applies hard filters and inventory re-ranking.
- Optionally calls the LLM for explanations.
- Was the **source of truth** when backend microservices were built (referenced in `docs/API.md` and `backend/README.md`).

> **Note (current `main`):** Root `README.md` marks this notebook as reference-only after the repo cleanup. The **production pipeline** lives in `backend/services/recommendation/app/pipeline.py` and still follows the same retrieve → rank → explain stages.

---

### 7. Repository Restructure & Microservices Architecture (June 2026)

**Commits:**
- `reset repo - remove broken backend, docs, and frontend. slimmed everything down to essentials`
- `cleanup`
- `feat(backend): MVP scaffold with /health and /recommend`
- `backend reorganize`
- `chore: add API contract and collaboration rules`

**What changed:**

George led a **major repo cleanup** that removed broken legacy code (Angular frontend, monolithic services, obsolete tests) and replaced it with a clean microservices architecture:

| Service | Port | Role |
|---------|------|------|
| `gateway` | 8000 | Public API, JWT auth, CORS |
| `recommendation` | 8001 | Pipeline orchestrator (retrieve → rank → explain) |
| `retrieval` | 8002 | Embeddings + Qdrant search |
| `reasoning` | 8003 | Optional LLM reasoning (OpenRouter) |
| `user` | 8004 | Registration, login, preferences |
| `indexing-worker` | — | Offline batch indexing |

**Shared libraries created:**

- `shared/dishify-contracts` — Pydantic models shared across services
- `shared/dishify-ranking` — Inventory re-ranking logic
- `shared/dishify-vector-store` — Qdrant + embedding wrapper

This microservices layout is still the production architecture on `main` today. Teammates later added **`ingest` (:8005)** for multimodal input without changing the core recommend path.

**Collaboration infrastructure:**

- `docs/API.md` — Frozen API contract (v1.3) for team coordination
- `docs/INTEGRATION.md` — Integration notes for frontend/backend teammates
- `AGENTS.md` — Cursor agent scope rules for parallel development

---

### 8. iOS Client (June 2026)

**Commits:**
- `feat(ios): SwiftUI app with Keycloak login and API client`
- `init` (iOS revamp — ~5,884 lines)

**What was built:**

A **production-grade native SwiftUI app** (`ios/Dishify/`) with:

| Module | Files | Description |
|--------|-------|-------------|
| **Core** | `APIClient.swift`, `AuthService.swift`, `SessionStore.swift`, `KeychainStore.swift` | Gateway API client, token management, secure storage |
| **Auth** | `AuthView.swift` | Register / login via gateway REST endpoints |
| **Recommend** | `RecommendView.swift`, `PantryEditor.swift`, `ResultDetailView.swift` | Cook flow, pantry input, recipe results |
| **Preferences** | `PreferencesView.swift` | Diet/allergy hard filters via `/me/preferences` |
| **Theme** | `Theme.swift`, color assets | Consistent visual design system |
| **Tests** | `DishifyTests/` (8 test files) | API client, auth, model decoding, async state |

**Additional deliverables:**

- Xcode project with Debug / Release / Staging configurations
- `ios/IMPLEMENTATION_PLAN.md` — Feature roadmap and architecture notes
- `ios/scripts/validate_release.sh` — Pre-release validation script

---

### 9. Authentication & Keycloak Integration (May–June 2026)

**Commits:**
- `cleanup. keycloak prep`
- `bug fix keycloak`
- `fix(user): align user_to_preferences return type with load_preferences`

**What was built:**

- Keycloak realm provisioning script (`keycloak/create-realm.sh`) with web and iOS OIDC clients.
- User profile schema (`keycloak/dishify-user-profile.json`) for preference attributes.
- User microservice (`backend/services/user/`) with:
  - Registration and login via Keycloak admin API
  - Postgres-backed preference storage (`user_preferences` table)
  - JWT validation and `/me/*` endpoints
- Gateway auth middleware (`backend/services/gateway/app/auth.py`).

---

### 10. Production Scale: 2.2M Recipe Index (June 2026)

**Commits:**
- `changed workflow from using recipe_10000 to recipe_full (2mio recipes)`
- `fixed qdrant. moved away from qdrant cloud to local`

**What was done:**

- Scaled from 10,000-recipe dev sample to **full 2.2M recipe corpus** (`recipes_full` collection).
- Created shared Qdrant volume archive workflow (`data/qdrant_volume.tar.gz`, ~7 GB) for team onboarding.
- Updated Docker Compose, env vars, and indexing scripts for local Qdrant.
- Documented restore/index procedures in `backend/README.md` and `backend/services/indexing/README.md`.

---

### 11. Documentation (April–June 2026)

**Commits:** `readme updated`, `updated all readme files`

George authored or substantially rewrote:

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview, quick start, architecture diagram |
| `backend/README.md` | Microservices guide, Qdrant restore, API testing |
| `ios/README.md` | iOS build/run instructions, configuration |
| `web-client/README.md` | Web client setup (updated for consistency) |
| `docs/API.md` | Frozen REST API contract v1.3 *(now v1.4 with multimodal sections added by team)* |
| `docs/INTEGRATION.md` | Cross-team integration notes |
| `AGENTS.md` | AI agent collaboration rules |
| `backend/services/indexing/README.md` | Indexing worker documentation |

---

### 12. Developer Tooling & Scripts

| Script | Purpose |
|--------|---------|
| `backend/scripts/index_recipes.py` | Index dev sample into Qdrant |
| `backend/scripts/index_full_recipes.py` | Index full 2.2M corpus |
| `backend/scripts/smoke_test_api.py` | End-to-end API smoke test |
| `backend/scripts/workflow_test.py` | Pipeline integration test |
| `start.sh` | Python venv bootstrap |

---

## Pull Requests Merged

George's branches were merged into `main` via the following pull requests:

| PR | Branch | Description |
|----|--------|-------------|
| #2 | `feat/data_cleaning_pipeline` | Data cleaning pipeline (collaborative) |
| #3 | `feat/setup-infra` | Infrastructure setup (collaborative) |
| #4 | `feature/keycloak` | Keycloak integration |
| #5 | `repo-full-cleanup` | Major repo restructure |
| #6 | `repo-full-cleanup` | Backend microservices + shared libs |
| #7 | `feature/web-frontend` | Web frontend (collaborative) |
| #8 | `main` | Integration merge |
| #11 | `feature/full_indexing` | Full corpus indexing |
| #12 | `main` | Integration merge |
| #13 | `feature/ios-frontend` | iOS app |
| #14–#15 | `feature/auth_hardening` | Auth hardening (collaborative — Jay) |
| #16 | `feature/deployment` | CI/CD deployment (collaborative — Jay) |
| #17 | `fix/qdrant` | Local Qdrant migration + shared vector store (George) |

---

## Team Extensions (Built on George's Foundation)

After the core pipeline and microservices architecture landed, teammates extended the product **without changing** the retrieve → rank → explain flow:

| Area | Author | What was added |
|------|--------|----------------|
| **Multimodal input** | lincanNerd | `ingest` service (:8005): `POST /transcribe`, `/voice`, `/vision/ingredients` (Gemini); API v1.4 |
| **Recipe augmentation** | lincanNerd | `POST /recipes/augment` — LLM expands terse directions into detailed steps + tips (reasoning service) |
| **Auth hardening** | Jay | JWT validation, security features, `KEYCLOAK_PUBLIC_URL` fixes (PRs #14–#15) |
| **iOS revamp** | Jay | Expanded SwiftUI app — navigation, tests, theme (PR #13; builds on George's initial iOS scaffold) |
| **Web client** | Jay | React + Vite app — Cook, Preferences, Profile, multimodal UI (PR #7) |
| **CI/CD & deployment** | Jay | GitHub Actions deploy workflow, lint, pipeline tests (PR #16) |
| **Explain optimization** | Team | `explain_max_recipes=2` — only top 2 ranked recipes sent to slow LLM; rest use inventory fallback |

George's **core contribution remains the recommendation engine and architecture**; these are additive product and ops layers on top.

---

## Key Files & Modules Authored

### Backend — Core Pipeline

```
backend/services/recommendation/app/pipeline.py    # Orchestrator: retrieve → rank → explain
backend/services/retrieval/app/routes.py         # Vector search API
backend/services/retrieval/app/store.py          # Qdrant store binding
backend/services/reasoning/app/llm_reasoning.py   # LLM explanation generation
backend/services/gateway/app/routes.py           # Public API routes
backend/services/gateway/app/auth.py             # JWT validation
backend/services/user/app/preferences_service.py # User preference CRUD
backend/services/indexing/app/main.py            # Batch indexing worker
```

### Shared Libraries

```
backend/shared/dishify-vector-store/dishify_vector_store/vector_store.py
backend/shared/dishify-ranking/dishify_ranking/ranking.py
backend/shared/dishify-contracts/dishify_contracts/models.py
backend/shared/dishify-contracts/dishify_contracts/restrictions.py
```

### iOS App

```
ios/Dishify/Core/AuthService.swift
ios/Dishify/Core/APIClient.swift
ios/Dishify/Core/SessionStore.swift
ios/Dishify/Features/Recommend/RecommendView.swift
ios/Dishify/Features/Recommend/PantryEditor.swift
ios/Dishify/Features/Preferences/PreferencesView.swift
ios/DishifyTests/APIClientTests.swift
ios/DishifyTests/AuthServiceTests.swift
```

### Notebooks & Data Pipeline

```
notebooks/end_to_end_pipeline.ipynb
notebooks/chatbot_reasoning.ipynb
notebooks/scoring.ipynb
```

### Infrastructure & Config

```
docker-compose.yml
keycloak/create-realm.sh
keycloak/dishify-user-profile.json
.env.example
docs/API.md
AGENTS.md
```

---

## Technical Highlights

1. **Semantic + structured hybrid search** — Combines dense vector retrieval with payload-based hard filters for safety-critical dietary constraints.

2. **Two-stage ranking** — Semantic retrieval followed by inventory-aware re-ranking produces results that are both relevant and practical.

3. **Graceful LLM degradation** — Pipeline works without LLM; falls back to deterministic reasoning from inventory match data.

4. **Microservices with shared contracts** — `dishify-contracts` ensures type-safe communication between services without a monolith.

5. **Team-scale onboarding** — Pre-built Qdrant volume archive lets new developers skip 2M-recipe indexing.

6. **API-first collaboration** — Frozen `docs/API.md` enabled parallel iOS, web, and backend development.

---

## Contribution Statistics

| Metric | Value |
|--------|-------|
| Total commits | 27 (+ 2 merge commits) |
| Files touched | 461 |
| Lines added | ~28,426 |
| Lines deleted | ~33,332 (mostly cleanup) |
| Active period | Apr 24 – Jun 21, 2026 |
| Primary languages | Python, Swift, Jupyter, Shell, Markdown |

---

## Role Summary

George Trump served as the **backend architect and ML pipeline engineer** for Dishify, with significant ownership of:

- The entire recommendation engine (retrieval, filtering, ranking, reasoning)
- Backend microservices architecture and shared libraries
- The native iOS client (initial implementation)
- API contract and team collaboration infrastructure
- Production-scale vector indexing (2.2M recipes)
- Project documentation and developer onboarding

His work established the technical foundation that the rest of the team built upon — web client, auth hardening, CI/CD deployment, and multimodal ingest/augment features all plug into the gateway and services architecture he defined.

---

*Generated from git commit history. Last synced with `main`: 2026-07-08.*
