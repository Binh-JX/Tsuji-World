# TSUJI WORLD — V1 Implementation Contract

| | |
|---|---|
| **Status** | Implementation contract derived from the locked TSUJI WORLD V1 Technical Architecture Specification |
| **Version** | 1.0 |
| **Scope** | V1 — Edition 01 (Birthday Edition, 20 December 2026) and the platform beneath it |
| **Languages** | `ja`, `en`, `el` — all required; Vietnamese (`vi`) is not part of the project |
| **Authority** | The locked Technical Architecture Specification is the source of truth. This document translates it into implementation instructions for Copilot. |
| **Implementation target** | M0 → M8 vertical-slice implementation |
| **Primary coding agent** | GitHub Copilot Premium |
| **Architecture authority** | Claude, subject to human approval where required |
| **Project owner / final human decision** | Project Lead |

> **The artwork is the interface. The archive is the foundation. The family is the soul.**

---

## 1. Purpose

This document is the implementation contract for building TSUJI WORLD V1.

It does **not** redesign, reinterpret, or replace the Technical Architecture Specification.

Copilot MUST implement the locked architecture as specified and MUST stop when implementation conflicts with the specification.

The implementation must prove the architecture end-to-end before real content is ingested at volume.

## 2. Non-negotiable implementation rules

1. **Do not redesign the locked architecture.**
2. **Do not silently change schema, IDs, workflow, visibility, rights, publication rules, language architecture, or edition semantics.**
3. **Do not introduce a database, Supabase, CMS, admin dashboard, custom authentication, IIIF, Deep Zoom, WebGL, 3D, AI archive chatbot, analytics dashboard, or other V1 non-goal.**
4. **Do not add Vietnamese.** Edition 01 languages are exactly `ja`, `en`, `el`.
5. **Do not publish `ai_draft` text, translations, transcripts, captions, or alt text.**
6. **Do not expose preservation masters or archive derivatives.**
7. **Do not put archive/source data into the renderer.**
8. **Do not allow the renderer to read `archive/`, `source/`, `book/`, or master storage.**
9. **Do not use real artwork records, historical facts, family material, or real IDs as fixture data.**
10. **Do not invent artwork titles, dates, dimensions, provenance, ownership, exhibition history, quotations, or artist statements.**
11. **Do not silently infer rights or consent.**
12. **Do not silently change an approved record. Any content change must invalidate approval and return the record to `under_review`.**
13. **Do not retype quotations. Quotations must resolve through approved excerpt IDs.**
14. **Do not create new voice types without a formal specification change.**
15. **Do not create a new edition application or code fork.**
16. **Do not weaken a fail-closed rule.**
17. **There is no override flag for any validation Fail.**
18. If implementation conflicts with the specification: **STOP, report the conflict, and wait for an architectural decision.**

## 3. Source of truth hierarchy

When instructions appear to conflict, use this order:

1. Human-approved locked architecture decisions
2. `TSUJI_WORLD_V1_Technical_Architecture_Specification.md`
3. `TSUJI_WORLD_IMPLEMENTATION_CONTRACT.md`
4. `ARCHITECTURE_DECISIONS.md`
5. `IMPLEMENTATION_STATUS.md`
6. Existing implementation/code
7. Copilot assumptions

Code MUST NOT override the specification.

## 4. Architecture boundary

```text
ZONE A — STEWARD
source/
archive/
book/
storage/
core/

        validate → gate → project → derive → proof → lock

                 ↓ published dataset

ZONE B — RENDERER
site/ (Astro, provisional)

                 ↓

static site / family origin / offline package
```

Core is framework-independent and contains schema, registry, ingest, derive, validate, gate, dataset, proof, snapshot, fixity and CLI.

Astro is the provisional renderer. The renderer receives only the published dataset and web assets; it has no credentials or archive/source/master access.

## 5. Repository contract

```text
tsuji-world/
├─ source/
│  ├─ receipts/RC-NNNNNN/record.yaml
│  └─ manifests/AST-NNNNNN.json
├─ archive/
│  ├─ _registry/
│  ├─ artworks/ exhibitions/ events/ people/ series/ sources/ assets/
│  ├─ voices/{artist,family,student,expert,associate}/
│  ├─ permissions/
│  └─ provenance/
├─ book/
│  ├─ editions/ED-NNNNNN/
│  ├─ worlds/ chapters/ stories/
│  ├─ themes.yaml
│  └─ ui/{ja,en,el}.json
├─ core/
│  ├─ schema/ registry/ ingest/ derive/ validate/ gate/
│  ├─ dataset/ proof/ snapshot/ fixity/ cli/
│  └─ fixtures/
├─ site/
└─ docs/
```

Additional implementation files may be added only when consistent with the locked architecture.

## 6. Data model contract

The implementation must support:

- Receipt `RC`
- Artwork `TSJ`
- Exhibition `EXH`
- Event `EVT`
- Person `PER`
- Series `SER`
- Source `SRC`
- Asset `AST`
- Artist Voice `AV`
- Family Memory `FM`
- Student Memory `SM`
- Expert Commentary `EC`
- Associate Memory `AM`
- Permission `PRM`
- Provenance `PRV`
- Edition `ED`
- World `WLD`
- Chapter `CHP`
- Story `STY`

The five voice types are closed:

```text
AV — Artist Voice
FM — Family Memory
SM — Student Memory
EC — Expert Commentary
AM — Associate Memory
```

## 7. ID contract

IDs follow:

```text
PREFIX-NNNNNN
```

Fixture IDs:

```text
FX-<PREFIX>-NNNNNN
```

IDs are minted by Core only, assigned at receipt, permanent, never reused after tombstoning, and must never encode mutable meaning.

Type/prefix mismatches fail. Type changes require re-issue with a new ID. Fixtures never enter a real edition.

## 8. Record and content contract

Every record is:

```text
<collection>/<ID>/record.yaml
```

Long text:

```text
text.<lang>.md
```

Use strict YAML 1.2 subset, CommonMark, UTF-8, NFC normalization and LF line endings. No anchors, tags, merge keys, MDX or framework-specific content components.

## 9. Status and gate contract

Independent axes:

**Documentation status**
`documented`, `partially_documented`, `family_record`, `to_verify`, `disputed`, `unknown`

**Workflow**
`draft`, `under_review`, `approved`, `withdrawn`

**Visibility**
`public`, `archive`, `family`, `private`

**Rights/consent**
`cleared`, `pending`, `denied`, `unknown`, `withdrawn`, `expired`

**Text origin**
`human_written`, `human_reviewed`, `ai_draft`

No axis may silently imply another.

## 10. Approval contract

An approved record requires named approver, date, evidence, current content hash and `approved_hash`.

Any change to an approved record returns it to `under_review`.

Approval is not factual verification.

## 11. Rights and consent contract

Nothing is presumed. Copilot must not infer copyright ownership, reproduction permission, likeness consent, publication consent, third-party permission, credit-line rights or name-display rights.

Permission coverage is evaluated against:

```text
subject × audience × edition × use × language
```

## 12. Multilingual contract

Edition 01 is exactly:

```text
ja
en
el
```

All three are required.

Japanese is canonical and requires native Japanese editorial review. English and Greek must be `human_written` or `human_reviewed`.

Vietnamese (`vi`) is **not part of TSUJI WORLD V1**. Do not create Vietnamese files, routes, translations or edition requirements.

`ai_draft` blocks release. Missing translation falls back to the original with a visible marker. Never machine-translate at build or runtime.

## 13. Archive / Experience contract

Dependency direction:

```text
Source → Archive → Experience → Dataset → Site
```

The archive never reads the book. Book records contain no independent fact fields. Curatorial groupings belong to the experience layer.

## 14. Editorial text contract

Core resolves:

```text
{{ref:ID}}
{{fact:ID.claim}}
```

at compile time.

Unresolved or non-displayable references fail the build. Editorial prose containing dates, numbers or superlatives is flagged for proof-sheet acknowledgement.

## 15. Quotation contract

Quotations are referenced by approved excerpt IDs. Do not retype quotations into Stories or renderer content.

## 16. Asset contract

Three tiers:

```text
PRESERVATION MASTER
        ↓
ARCHIVE DERIVATIVE
        ↓
WEB DERIVATIVE
```

Masters are original, immutable, SHA-256 protected and never exposed. Archive derivatives remain private. Web derivatives are sRGB, metadata-stripped, GPS/personal-EXIF-free, with AVIF/WebP/JPEG fallback and versioned derivative profiles.

The interface never crops, filters or colour-adjusts an artwork. A crop/detail is a separate labelled detail asset.

## 17. Published dataset contract

The dataset is the only content contract crossing from Core to Renderer:

```text
dataset/
├─ manifest.json
├─ records/<type>/<ID>.json
├─ assets.json
├─ routes.json
├─ strings/<lang>.json
└─ schema/
```

Projection is allow-list based.

The dataset must not contain `PRM-`, `PRV-`, `RC-`, `notes_internal`, `contact`, master paths, archive-derivative paths or other prohibited private data.

## 18. Renderer contract

Astro is provisional.

The renderer must:

- consume only the dataset
- render real HTML
- work without JavaScript for reading content
- render every `must_label`
- honour reduced motion
- use Core-generated URLs
- support offline mode
- keep artwork uncropped/unfiltered

It must not read archive/source/book/master data, hold credentials, compute facts/statuses, generate canonical URLs, or call external services from islands.

## 19. Edition 01 contract

```text
ID: ED-000001
Title: TSUJI WORLD — Birthday Edition
Target release: 20 December 2026
Audience ceiling: family
Outputs: online + offline
Languages: ja + en + el
```

Edition 01 is not a separate application. It uses the same archive, schema, statuses, gate, pipeline, renderer and canonical paths.

## 20. Milestone implementation plan

### M0 — Foundations

Private repository, protected `main`, repository structure, family-owned account configuration, storage tiers, backup targets and runbook v0.

Exit: access can be recovered by a second person.

### M1 — Schema and Registry

All entity schemas, common envelope, claims, five voices, Permission, Edition, registry, minting, tombstones, fixtures, structural validation and data dictionary.

Tests: T09, T13 and structural rules.

### M2 — Ingest and Preservation

Receipt creation, asset minting, master ingest, SHA-256, manifests, XMP sidecars, archive derivatives, fixity, backup and restore.

Tests: T20 first pass, T06.

### M3 — Derivatives

Derivative profile v0, deterministic generation, metadata stripping, GPS/EXIF removal, AVIF/WebP/JPEG, width ladder and placeholders.

Tests: T06 and deterministic asset checks.

### M4 — Gate and Dataset

Edition eligibility, display policy, allow-list projection, rights/voice/language checks, excerpt/token resolution, `routes.json`, dataset schema and negative/leak tests.

Tests: T01–T15.

### M5 — Proof, Lock, Snapshot

Proof sheet, release lock, snapshot, bundle manifest, reproducibility and checksums.

Test: T16.

### M6 — Renderer Stub

Astro, dataset-only input, one plate page, Record panel, status labels, language fallback, Job B sandbox and types-only Core boundary.

Tests: T17, T18.

No visual design work yet.

### M7 — Access and Offline

Family origin integration, identity-based edge access, offline package, relative links, no external requests, public-ceiling build without deployment.

Test: T19.

### M8 — Scale Test

1,000 synthetic records × 3 languages. Record build time, memory and dataset size.

Test: T21.

Real intake starts after M2, in parallel with M3–M8.

## 21. Acceptance tests

| Test | Required behaviour |
|---|---|
| T01 | `to_verify` absent from public; family only when opted in and labelled |
| T02 | Public `opt_in_unverified` fails |
| T03 | Post-approval edit is excluded until re-approved |
| T04 | Asset without Permission fails |
| T05 | Identifiable minor without guardian consent fails |
| T06 | GPS/personal EXIF removed from web derivative; master unchanged |
| T07 | Required ineligible reference fails; optional one is dropped/logged |
| T08 | `ai_draft` / missing English fails; fallback shows original marker; no machine translation |
| T09 | Reported speech cannot become Artist Voice; type change requires re-issue |
| T10 | Receipt/Permission/Provenance/internal notes/contact never enter dataset |
| T11 | Master/archive-derivative paths never enter output |
| T12 | Fixture cannot enter real edition |
| T13 | Tombstoned ID / wrong prefix / wrong label fails |
| T14 | Invalid token / retyped quotation fails |
| T15 | Canonical path change fails unless redirect declared |
| T16 | Two builds from one lock are reproducible |
| T17 | Renderer cannot access archive; dataset-only rendering |
| T18 | Every `must_label` claim renders its label |
| T19 | Offline package works with network disabled |
| T20 | Restore from backup succeeds |
| T21 | 1,000 × 3-language scale test completes within agreed budget |

## 22. Copilot working protocol

Before every task, Copilot MUST:

1. Read the locked Technical Architecture Specification.
2. Read this Implementation Contract.
3. Read `docs/IMPLEMENTATION_STATUS.md`.
4. Read `docs/ARCHITECTURE_DECISIONS.md`.
5. Inspect existing implementation before modifying it.
6. Identify the current milestone.
7. Implement only the requested milestone/task.

The repository documents are the shared memory; previous conversation is not the source of truth.

## 23. Task granularity

Do not request “Build the entire TSUJI WORLD.”

Use:

```text
Implement M0.
```

then M1, M2, etc.

Within a milestone, use small tasks, test after each task, and report results.

## 24. Copilot implementation report

After every milestone or significant task, report:

```text
## Implementation Report

### Milestone
M#

### Completed
- ...

### Files created
- ...

### Files modified
- ...

### Tests executed
- Txx: PASS
- Txx: FAIL

### Architecture compliance
PASS / FAIL

### Deviations
None
OR
- ...

### Known issues
None
OR
- ...

### Architecture conflicts
None
OR
- ...

### Next task
...
```

A milestone is complete only when its exit criterion and required tests pass.

## 25. Architecture conflict protocol

If Copilot encounters a conflict:

```text
ARCHITECTURE CONFLICT

Specification section:
...

Current implementation:
...

Conflict:
...

Why implementation cannot satisfy the current rule:
...

Possible options:
...

STATUS: STOP
ARCHITECTURAL DECISION REQUIRED
```

Copilot must not choose an architecture change itself.

If the specification changes, update the specification, Appendix A if affected, `ARCHITECTURE_DECISIONS.md`, this contract if affected, tests, and implementation before resuming.

## 26. Architecture Decision Record

Use:

```text
docs/ARCHITECTURE_DECISIONS.md
```

Each decision records:

```text
ADR-ID
Date
Decision
Reason
Affected sections
Affected tests
Status
Approver
```

Do not hide architecture changes inside code commits.

## 27. Implementation status

Maintain:

```text
docs/IMPLEMENTATION_STATUS.md
```

Initial state:

```text
M0 — NOT STARTED
M1 — NOT STARTED
M2 — NOT STARTED
M3 — NOT STARTED
M4 — NOT STARTED
M5 — NOT STARTED
M6 — NOT STARTED
M7 — NOT STARTED
M8 — NOT STARTED
```

A milestone is marked COMPLETE only after its exit criteria and required tests pass.

## 28. Git and change discipline

- `main` is protected.
- Changes to approved records or edition records require review.
- No binaries or masters in Git.
- Core and site remain separable.
- Keep commits focused.
- Do not mix architecture changes, real content ingestion and visual design in one step.
- Do not delete historical data to make tests pass.
- Preserve tombstones.

## 29. Real-content boundary

Real content follows:

```text
COLLECT
→ INGEST
→ VERIFY
→ CURATE
→ TRANSLATE
→ REVIEW RIGHTS
→ APPROVE
→ COMPILE
→ PROOF
→ RENDER
→ RELEASE
```

No shortcut may be introduced for deadline pressure.

## 30. Definition of Done

V1 implementation is complete only when:

- Edition 01 has a complete release lock.
- Edition 01 can be reproduced.
- Every displayed claim/text passes the gate.
- Every non-`documented` claim is labelled.
- Masters satisfy 3-2-1 preservation.
- Restore drill passes.
- Offline package passes on the actual target device.
- Runbook is complete.
- Accounts are family-owned.
- Recovery keys are held by at least two designated people.
- Proof sheet is signed.
- A curator can use the archive alone to produce a catalogue entry for every published work.

## 31. V1 non-goals

Do NOT implement:

- database / Supabase
- CMS
- admin dashboard
- custom authentication
- IIIF
- Deep Zoom
- tiling infrastructure
- WebGL
- 3D
- virtual gallery rooms
- AI archive chatbot
- unreviewed AI narrative/translation/caption/transcript
- visible archive search/faceted browsing
- comments/guestbook/user-contributed content
- e-commerce/ticketing/donations
- collection management/loans/condition reports/insurance
- per-edition code/data forks
- client-side password security
- automatic unreviewed data sync to public origins
- analytics dashboards
- third-party trackers in non-public editions

## 32. Final implementation principle

```text
SOURCE MATERIAL
      ↓
ARCHIVE / VERIFIED RECORD
      ↓
CURATED EXPERIENCE / EDITION
      ↓
VALIDATED PUBLISHED DATASET
      ↓
STATIC RENDERER
      ↓
FROZEN RELEASE
```

> **Claude designs and protects the architecture.**
>
> **Copilot implements and tests it.**
>
> **The project owner makes final human decisions.**
>
> **Architecture conflicts stop the implementation rather than silently changing the contract.**
