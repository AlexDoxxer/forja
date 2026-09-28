# Changelog

All notable changes to Forja are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-28

### Data Ingestion

- **Exercise database**: Ingested 1.324 exercises from `hasaneyldrm/exercises-dataset` (commit
  `7455efae41b3`) with all fields normalized and enriched.
- **Vocabulary mapping**: 100% of exercise body parts, equipment, targets and muscle groups
  mapped through `specs/muscle-normalization.yaml` and `specs/equipment-normalization.yaml`.
- **Spanish translations**: All 1.324 exercise names translated to Spanish and stored in
  `specs/overrides/names_es.json` with zero inconsistencies against `specs/glossary-es.yaml`.
- **Enrichment**: Deterministic enrichment pipeline with 6 derived fields per exercise
  (movement_pattern, mechanic, role, difficulty, laterality, load_type, is_staple) verified
  against `specs/overrides/enrichment-overrides.yaml` and 100% test coverage.
- **Media verification**: 2.648 media files (1.324 GIFs + 1.324 thumbnails) downloaded at
  180×180 px, SHA-256 checksums verified, served with mandatory Gym visual attribution.
- **Alternative suggestions**: Pre-calculated top 8 alternatives per exercise by pattern
  similarity, target muscle overlap, and difficulty.

### Routine Engine (forja_engine v0.1.1)

- **Deterministic generation**: Complete 9-step pipeline (normalize → split → volume → allocate
  → select → prescribe → timefit → periodize → compose) guaranteed to produce identical programs
  byte-for-byte from the same seed and inputs.
- **Input validation**: All 1.890 combinations (6 goals × 7 days/week × 3 levels × 3 sexes × 5
  equipment presets) validated and passing golden snapshot tests with subject-matter expert
  review.
- **Volume management**: Automatic calculation of weekly volume targets by muscle group
  per goal; distribution across days with ≤10 effective sets per group and session.
- **Exercise selection**: Scoring-based with pattern matching (+40), staple preference (+15),
  progression difficulty limits, and fallback relaxation chain (difficulty → staple → target
  muscle → affinity pattern) with full visibility of applied relaxations.
- **Periodization**: Automatic progression through accumulation/intensification phases with
  weekly volume increases, deload week with 55% load, and optional daily undulation for strength.
- **Sex-aware defaults**: Preselectes emphasis (lower_glutes for females, balanced otherwise),
  adjusts rest times and exercise demonstration preference; **never excludes exercises or limits
  loads based on sex**.
- **Accessibility features**: Plan operations (regenerate_day, swap_exercise, rebalance_after_edit,
  validate_plan) expose full programmatic control; all warnings and violations documented in
  machine-readable format.

### Nutrition Engine (forja_nutrition v0.2.1)

- **Energy calculation**: Mifflin-St Jeor BMR formula with activity-adjusted GET and
  goal-based targets (−15% gentle loss, +10% gentle gain, −5% to 0% recomposition).
- **Macro targets**: Flexible protein (1.6–2.2 g/kg), minimum fat floors (≥0.8 g/kg and ≥20%
  kcal), carbohydrate remainder, fiber targets.
- **Safety floors**: Blocks plans for minors, pregnancy, lactation; enforces calorie minimum
  (max(BMR, 1200/1500/1350 by sex)); prevents aggressive deficits and extreme diets.
- **Meal planning**: Mediterranean meal template (protein + carb + vegetable/fruit + healthy
  fat) repeated 7 days with seeded randomization and weekly repetition penalty.
- **Macronutrient fitting**: Constrained least-squares optimization (scipy.optimize.lsq_linear)
  to hit daily targets within ±5% calories and ±10% macros, with feedback loop and re-verification.
- **Food database**: 193 foods from USDA FoodData Central (SR Legacy 2018-04) with real `fdc_id`,
  Spanish names, dietary compatibility (omnivore/pescatarian/vegetarian/vegan), allergen flags,
  portion sizes and household units.
- **Shopping list**: Weekly aggregation by store category with user-friendly portion formatting.
- **Food substitution**: Within-category swaps preserving daily macro targets while respecting
  dietary restrictions and allergen exclusions.

### Backend API (v1.2.0)

- **Complete REST API**: 59 endpoints across auth, profile, catalog, routine generation,
  routine management, session tracking, progress analytics, nutrition (optional), data
  export/import, and admin functions.
- **Database schema**: PostgreSQL 16 with UUID v7 primary keys, full-text search over exercises
  (unaccent), trigram indexes for fuzzy matching, and 14 core tables with audit trail support.
- **Authentication**: Argon2id password hashing with OWASP parameters, opaque session tokens
  with sliding 30-day expiration, revocation from settings, per-session IP hash logging.
- **CSRF protection**: Double-submit cookie validation (cookie + header) on all non-safe methods,
  automatic token rotation on login and password change.
- **Authorization**: Strict ownership verification on all user-scoped routes; attempts to access
  another user's resources return 404 (not 403) to prevent information leakage.
- **Rate limiting**: Per-IP rate limiting on login (5 attempts/min), registration (3 attempts/min),
  and generator preview (30 requests/min) with 429 response and `Retry-After` header.
- **Input validation**: Pydantic v2 with strict mode on all request bodies; file size limits (5 MB
  for imports) and chunked transfer encoding protection at the app layer.
- **Security headers**: CSP (`default-src 'self'`), HSTS, X-Content-Type-Options, Referrer-Policy,
  Permissions-Policy; Content-Security-Policy prevents inline scripts.
- **Data privacy**: Sensitive data (PAR-Q, weight, diet) never logged; PII-free JSON logs with IP
  hashes; full data export in JSON format for GDPR compliance.
- **Session management**: HTTP-only, secure cookies with SameSite=Lax; multiple active sessions
  tracked and revocable from settings.
- **Migrations**: Alembic reversible migrations with bloqueo consultivo (advisory lock) to prevent
  concurrent execution; all schema changes tested for upgrade and downgrade.

### Frontend PWA

- **Onboarding**: 4-step registration flow (account → profile → PAR-Q → equipment & limitations)
  with optional diet feature activation; safety warning on PAR-Q affirmative answers forces
  beginner level unless explicitly overridden.
- **Home (Hoy)**: Quick session status (scheduled/rest/no active program), workout start button,
  weekly summary (sessions done/planned, volume), recent personal record, and quick weight log.
- **Routine Generator (Generador)**: Interactive 6-step wizard with goal selection, frequency,
  sex (preselecteed from profile with explanation), level, duration, equipment, emphasis and
  limitations; live preview with exercise GIFs, sets×reps, rest times, estimated duration,
  volume distribution graph, rationale, and warnings; regenerate with new seed, regenerate day,
  swap exercise, save and activate.
- **Routine Editor (Editor)**: Drag-and-drop day editing with `dnd-kit` (mouse and keyboard
  accessible), block creation (warmup/main/superset/circuit/finisher/cooldown), exercise
  reordering, parameter editing (sets, reps, RIR, tempo, rest, notes), live validation with
  motor feedback, undo/redo support.
- **Session Player (Reproductor)**: Full-screen exercise GIF with attribution, current set count,
  target reps/RIR/suggested weight from progression, performance from previous session, numeric
  keypad for weight/reps entry, countdown rest timer (angled ring, ±15 s quick adjust, vibration,
  sound, background notification), warmup ramp with plate calculator, exercise alternatives on
  demand, step-by-step instructions in 10 languages, undo capability; session state persisted
  offline in IndexedDB.
- **Session Summary**: Instant local calculation (offline) of totals and personal records;
  finalization via `POST /sessions/{id}/finish` idempotent endpoint.
- **Exercise Library (Biblioteca)**: Full-text search (accent-insensitive, ES/EN), filter chips
  (body zone, equipment, pattern, difficulty, favorites), clickable muscle map (frontal/posterior,
  keyboard navigation), virtualized exercise grid with infinite pagination, animated GIF preview
  on hover/focus; detail view shows all muscles (primary/secondary highlighted on map), all 10
  languages for instructions, exercise variants (angle/demonstrator), suggested alternatives,
  personal history (1RM, set records).
- **Progress (Progreso)**: 26-week heatmap calendar, weekly volume per muscle group (bar charts),
  1RM progression per exercise (line charts), personal records (all-time max weight/reps/volume),
  body weight graph with 7-day moving average; all charts rendered with Recharts in deferred
  chunks.
- **Nutrition (Nutrición)**: Goal display with neutral-tone macro rings, permanent safety notice,
  weekly meal plan by day/meal with macro alignment, in-place food swaps (automatic or manual),
  shareable shopping list (categories, checkboxes, IndexedDB-backed), nutrient settings and
  recalculation.
- **Profile (Perfil)**: User data edit (name, height, weight), locale and theme selection
  (dark/light/system), sonics and vibration toggles, default rest between sets, full data
  export (JSON), data import with schema validation, account deletion with password confirmation,
  active session management (revoke), offline library download, logout, and access to credits/licenses.
- **Admin**: User registration toggle, global diet feature toggle, user list (role, active status,
  search), ingest launch (dry-run or real) with live progress and execution history (row counts,
  checksums, errors, diffs).
- **Credits & Licenses**: MIT license for exercise dataset, Gym visual attribution with link,
  dataset commit SHA, health disclaimer.
- **PWA features**: Offline-first design with IndexedDB session state persistence, service worker
  (Workbox) with precached app shell, stale-while-revalidate for `/api/v1/exercises*`, cache-first
  for thumbnails (1.400 entry limit) and GIFs (300 MB configurable), automatic offline queue with
  exponential retry for session/set writes, Background Sync on reconnection, Web Manifest with
  standalone display mode and maskable icons.
- **Internationalization**: Spanish default with English fallback; all UI strings translated; 10
  languages available for exercise instructions (from dataset); locale-aware date/number formatting
  via `Intl`.
- **Accessibility**: WCAG 2.2 AA compliance with visible focus, logical tab order, `aria-live`
  announcements for timer, alt text for all exercise media, labeled form controls, no
  color-only information; `prefers-reduced-motion` respected (static image + play button).

### Deployment

- **Docker multi-stage builds**: Separate builder (uv, development tools) and runtime images
  (`python:3.12-slim`) for minimal footprint; API image shared by `api` and `ingest` services.
- **Docker Compose**: Isolated network (internal, no external egress except for `api`/`ingest` to
  fetch dataset), health checks on all services, `tools` profile for one-off ingesta tasks.
- **nginx configuration**: Serves static frontend with immutable caching (`max-age=31536000`),
  routes `/api` to FastAPI, routes `/media` with optional `auth_request` check, enforces
  `client_max_body_size 5m`, applies security headers, rate limits per IP.
- **Proxmox LXC guide**: Step-by-step instructions for Debian 12 with unprivileged container,
  Docker Engine installation, Forja clone and configuration, first-time bootstrap, TLS setup
  (reverse proxy or in-container nginx), operation (start/stop/logs/backup/restore/update).
- **Backup and restore**: Automated daily backups with 7-day retention and 4-week weekly rotation,
  `pg_dump -Fc` binary format, offline testable restore procedure, media regenerated on ingest
  (not part of backup).
- **Environment configuration**: All settings via `.env` file (generated from `.env.example`):
  database URL, secret key, public base URL, media authentication, dataset commit, registration
  open flag, diet feature enabled flag, locale, log level, Gunicorn worker count.
- **Health checks**: `/api/v1/health` (app alive), `/api/v1/ready` (database + media ready).
- **Observability**: JSON logs to stdout, request ID propagated, optional Prometheus metrics at
  `/metrics`.

### Security

- **Penetration testing**: Comprehensive security audit covering authentication, authorization,
  input validation, CSRF, SQLi, SSRF/RCE, IDOR, PII handling, rate limiting, and dependency
  scanning (`pip-audit`, `npm audit`, Trivy). Results: 0 critical/high vulnerabilities in
  production code.
- **Credentials**: No hardcoded secrets, all rotated on deployment, password policy enforced
  (≥10 chars, common password check).
- **Dependencies**: Locked versions (`uv.lock`, `package-lock.json`), vendored (Radix UI
  primitives, MSW), no unpinned dev/test dependencies.
- **Container security**: Non-root user (UID 10001), read-only filesystems where possible,
  minimal base images (`python:3.12-slim`, `nginxinc/nginx-unprivileged:1.27-alpine`),
  no capability escalation.

### Testing & Quality

- **Unit test coverage**: Routine engine 100% lines / ≥95% branches, nutrition engine 100% lines,
  backend ≥90% lines and branches, frontend ≥85% lines; all tests passing with thresholds
  enforced in CI.
- **Integration tests**: Database fixtures with testcontainers, async API tests with `httpx`,
  OpenAPI contract validation.
- **E2E tests**: Playwright (Chromium + WebKit mobile) covering onboarding → generate → activate
  → train (full session with rest timer, weight/rep entry) → view progress, offline session
  player, diet flow, and admin ingest.
- **Accessibility**: Axe Core tests on all major routes (0 critical/serious violations).
- **Performance**: Lighthouse CI with thresholds (≥90 performance/accessibility/best practices/PWA),
  JS bundle <200 KB gzip (code-split by route), LCP <2.5s on 4G throttle.
- **Code quality**: Lint (`ruff`, `eslint`) and strict type checking (`mypy --strict`, `tsc --strict`)
  enforced in CI; no `TODO`, `# type: ignore`, or `# noqa` without justification.
- **Contract compliance**: OpenAPI schema exported from FastAPI, diffed against
  `contracts/openapi.yaml` in CI to detect inadvertent breaking changes.

### Documentation

- **README.md**: Project overview, tech stack, structure, development setup, and license summary.
- **MASTER_PROMPT.md**: Complete specification (vision, scope, constraints, stack, domain model,
  ingestion, engines, API, frontend screens, security, deployment, testing, multiagent execution).
- **ORCHESTRATION.md**: Phase definitions, gate criteria, handoff protocol, and coordination rules.
- **docs/USER_GUIDE.md**: Spanish user guide for self-hosting (what is Forja, deployment, first
  startup, screen tour, export/import, account management).
- **deploy/lxc/README.md**: Step-by-step Proxmox LXC deployment with Docker, reverse proxy setup,
  operation commands, and Gym visual licensing warning.
- **ADRs** (`docs/adr/`): 12 architectural decision records covering monorepo structure, single
  source of nutrition tables, CSRF strategy, Radix UI, optional dependencies, and PWA strategies.
- **Handoff records** (`docs/handoffs/`): Phase 0–3 completion reports detailing changes, tests,
  decisions, and verification steps for each subsystem.

### Known Limitations

- **Export features (próximamente)**: MASTER_PROMPT §1.7 specifies PDF export for routines and
  ICS export for calendars; backend endpoints exist (`GET /programs/{id}/export.pdf`,
  `/calendar.ics`) but frontend UI links and handlers are pending (branch `f4/frontend-gaps`).
- **Diet disable toggle (próximamente)**: Diet feature can be activated during onboarding but
  currently cannot be toggled off per-user in Profile settings (Admin can disable globally).
  Frontend UI control pending (branch `f4/frontend-gaps`).
- **Gym visual media licensing**: App serves 180×180 GIF and thumbnail files without modification,
  with mandatory attribution on all views. Public exposure requires review of Gym visual terms of
  use (https://gymvisual.com/content/3-terms-and-conditions-of-use) and compliance verification
  by the deployer.
- **No data migration from v0**: This is the v1.0.0 release; upgrading from beta/alpha versions
  may require manual data migration.
- **No native apps**: v1 ships as a PWA (progressive web app) only; native iOS/Android apps
  deferred to future releases.
- **No real-time multiplayer**: Session tracking is per-user only; family members share workouts
  via shared account or separate accounts.

---

[1.0.0]: https://github.com/forja-kit/forja-kit/releases/tag/v1.0.0
