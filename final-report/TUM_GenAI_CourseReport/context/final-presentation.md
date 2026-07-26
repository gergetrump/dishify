# Dishify — Final Presentation Context

Extracted from **Dishify Final.pdf** (final presentation, Group 01). Use this file as shared context when writing the course report (`content/*.tex`). Slide 8 (*System Decomposition*) was a diagram with no extractable text; the **System decomposition** section below is supplemented from the repo README and architecture diagram.

**Source:** `/Users/georgetrump/Downloads/Dishify Final.pdf` (13 slides)

---

## Report mapping (where to reuse this content)

| Presentation topic | Report chapter | File |
|--------------------|----------------|------|
| Problem, vision, demo | User Guide (pitch) | `content/01-user-guide.tex` |
| Timeline, roles, AI pipeline, architecture | Project Management | `content/02-project-management.tex` |
| UAT approach, scores, learnings | User Acceptance Testing | `content/03-user-acceptance-testing.tex` |
| Safety/evaluation, retention, improvements | Safety & Reflection | `content/04-safety-reflection.tex` |
| Multimodal pipeline, differentiation | Novelty & Value | `content/05-novelty-value.tex` |
| Demo video URL | PM § Pitch Video + Moodle attachment | `content/02-project-management.tex` |

---

## Slide 1 — Title

- **Product:** Dishify
- **Group:** 01

---

## Slides 2–3 — The Problem

- Core user question: **“So… what do I eat…?”**
- Gap: **There aren’t really any tools that let you search recipes by ingredients** (pantry-first discovery is underserved).

---

## Slide 4 — Dishify (Solution hook)

- **What if there was an automatic tool that solved this problem?**

---

## Slide 5 — Project Vision

- **Vision:** A **multi-modal automatic recipe generator**

---

## Slide 6 — Team Roles & Collaboration

**Process:** Peer programming sessions for the backend architecture.

### Before midterm

| Area | Members |
|------|---------|
| **Frontend** | Georg Tichy, Maria Chatzipavlou Arvaniti |
| **Backend** | Can Lin, George Trump |
| **Infrastructure** | Jay Zhou (Chengjie Zhou), Aymen Faouel |

### After midterm

- Roles continued / evolved (slide shows “AFTER MIDTERM” header; assign concrete post-midterm tasks in the report team chart).

---

## Slide 7 — Project Timeline

Status at time of final presentation:

### Done

| Workstream | Description |
|------------|-------------|
| **Data preprocessing** | Gather and clean the existing dataset for more insights |
| **Pipeline creation** | End-to-end pipeline of the AI system |
| **Infrastructure set up** | Docker, database, cached vector store management |
| **Quality check** | Check the quality of the preliminary output |
| **API surface** | Core API endpoints |

### To be done (at presentation time)

| Workstream | Description |
|------------|-------------|
| **Backend integration** | Construction of the backend interface using the API endpoints |
| **Platform** | Application infrastructure for deployment and orchestration |
| **Evaluation** | Evaluation of safety, review and rate system outputs |
| **Product polish** | Integration of all components with possible extension |
| **Documentation** | Clear and detailed documentation of the entire framework |

> **Report note:** Update “Current Progress and Future Plans” to reflect what was completed *after* the presentation (e.g. web/iOS polish, guardrails, final report, GitLab LRZ submission).

---

## Slide 8 — AI Pipeline (5 stages)

### Input

1. Natural language query, available ingredients  
2. Diets & allergies in stored user preferences  

### Retrieve

- Embed query + pantry with **all-MiniLM** (slides: “mMiniLM” → **sentence-transformers/all-MiniLM-L6-v2** in repo)
- Nearest-neighbor search in **Qdrant** over **~2.2M pre-indexed recipes**
- **Hard filter** on unsafe recipes based on diets & allergies

### Rank

- Compare recipe candidate’s parsed ingredients to user’s pantry
- **Score: 70% semantic + 30% inventory overlap**
- Re-order candidates for more cookable recipes

### Explain

- LLM generates structured **“Why it fits” / “what is missing”** per recipe
- Top recipes sent to model; **instant inventory-based fallback** if LLM unavailable

### Output

- Ranked recipe list with blended scores and per-recipe quick overview
- Each result includes:
  - matched / missing ingredients
  - fit reasoning
  - estimated time
  - augmented directions

---

## Slide 9 — System Decomposition

*No text on slide (diagram only). Use [README.md](../../../README.md) request flow and `Ressourcen/dishify_arch.png` in the report.*

### Components (from repo)

| Layer | Components |
|-------|------------|
| **Clients** | React web client, SwiftUI iOS app |
| **Edge** | Caddy reverse proxy |
| **Gateway** | Public API, Keycloak JWT validation, service proxying |
| **Core services** | Recommendation (orchestration), Retrieval (Qdrant), Reasoning (LLM), Ingest (Gemini voice/vision), User (preferences), Indexing (offline) |
| **Data / infra** | Qdrant, Postgres, Keycloak, Docker Compose |
| **GenAI** | Gemini (transcribe, vision, voice JSON), OpenRouter-compatible models (reasoning, augmentation) |

### Request flow (short)

1. Client authenticates via gateway / Keycloak  
2. `/recommend` → retrieval → ranking → optional reasoning  
3. `/voice`, `/vision/ingredients` → ingest (Gemini)  
4. `/recipes/augment` → enhanced directions and tips  

---

## Slide 10 — Demo

| Resource | URL / address |
|----------|----------------|
| **Demo video (YouTube Shorts)** | https://www.youtube.com/shorts/XWc4LrsOffw?feature=share |
| **Live app** | `167.233.165.44` |

> Use the YouTube link in **Pitch Video** (PM report) and Moodle video submission if still current.

---

## Slide 11 — User Acceptance Testing

### Approach

| Item | Detail |
|------|--------|
| **Target users** | Regular home cooks — **4 daily + 5 weekly** (cooking frequency) |
| **Participants** | **9 respondents** |
| **Method** | Task-based usability test + survey |

### Main pain points (before / general)

- Don’t know what to cook — **5/9**
- Recipes take too long — **4/9**

### Results summary (Likert, /5)

| Metric | Score |
|--------|-------|
| Explanation clarity | **4.11** |
| Allergy & diet trust | **4.44** |
| Recommendation process | **4.56** |
| Ease of use | **4.67** |
| Substitution quality | **3.88** |
| Recipe relevance | **4.00** |
| Likelihood to reuse | **3.67** |

---

## Slide 12 — Learnings

### What users liked

- Removes **decision fatigue**
- Reduces **food waste**
- **Explanations build trust** in recommendations

### Main improvement opportunity

- **Increase long-term user retention**

### Issues to address

- Generation is **too slow**
- Ingredient matching is **too literal**
- Instructions need **more detail**
- **Better substitutions** needed
- **Clearer onboarding**

### Most requested features

- Save / bookmark recipes
- Cooking time filter
- Difficulty filter
- Health-goal filters
- Recipe photos
- Print-friendly recipe view

---

## Slide 13 — Closing

- Thank you — Group 01

---

## Suggested copy-paste snippets for report authors

### One-paragraph vision (PM § Overall Project Vision)

Dishify helps home cooks answer “what do I eat?” by recommending recipes from the ingredients they already have. Unlike generic recipe apps, it combines semantic search over a large recipe index (~2.2M recipes), pantry-aware ranking, hard dietary/allergy filtering, and optional multimodal input (voice and image) plus LLM explanations. The vision is a multi-modal automatic recipe generator that reduces decision fatigue and food waste while keeping users safe and informed about fit and missing ingredients.

### UAT headline (UAT § Result Analysis)

Nine participants completed a task-based usability test and survey. Mean scores were strongest for ease of use (4.67/5) and recommendation process (4.56/5); substitution quality (3.88/5) and likelihood to reuse (3.67/5) indicate room to improve retention-oriented features.

### Progress framing (PM § Current Progress)

At the final presentation, the team had completed data preprocessing, the end-to-end AI pipeline, Docker/Qdrant infrastructure, quality checks, and core API endpoints. Subsequent work focused on client integration, platform deployment, safety evaluation, product polish, and course documentation.

---

## Open items for the team to confirm in the report

- [ ] Post-midterm role assignments (slide 6 “AFTER MIDTERM” was not detailed in PDF text)
- [ ] Exact UAT dates, task script, and participant demographics (expand beyond slide bullets)
- [ ] Whether demo URL and server IP are still valid for submission
- [ ] Gantt chart dates aligned with “Done / To be done” milestones above
- [ ] System decomposition figure: ensure report uses `dishify_arch.png` or export from slide 8
