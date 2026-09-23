# TSUJI WORLD — V1 Technical Architecture Specification

| | |
|---|---|
| **Status** | Technical contract, v1.0. Appendix A locked (see Appendix A) |
| **Date** | 24 September 2026 |
| **Scope** | V1: Edition 01 (Birthday Edition, 20 December 2026) and the platform beneath it |
| **Authority** | Locked principles P1–P15 (§1) → this specification → implementation |
| **Not in this document** | UI design, artwork records, artwork titles, historical facts, code |

> The artwork is the interface. The archive is the foundation. The family is the soul.

**Conventions.** MUST, MUST NOT, SHOULD and MAY are used in their RFC 2119 sense. `[P#]` tags trace a clause to a locked principle. "Steward" means the person designated by the project lead to operate the archive and pipeline. Role assignments live in `docs/runbook`, not in this contract.

---

## 0. Derivations to confirm before lock

The locked principles fix the direction. Turning them into a precise contract required the choices below. Each goes slightly beyond the wording of P1–P15 and is listed here so nothing is locked silently.

| # | Derivation | Why |
|---|---|---|
| N1 | Visibility has **four levels**: `public`, `archive` (reserved, unused in V1), `family`, `private` (steward-only) | P8 distinguishes FAMILY from PRIVATE. Without a separate `family` level, the family edition could expose steward-only material |
| N2 | **Publication is an act of an edition release, not a record status.** Record workflow is `draft → under_review → approved → withdrawn` | P3 makes Edition first-class. A record cannot be "published" without saying where |
| N3 | Fifth voice type: **Associate Memory** (知人・関係者の記憶) | P7 asks for a proposal (§4.5) |
| N4 | Rights and consent are one entity, **Permission**, with an immutable `basis` | Same shape, uniform gate logic, distinct bases |
| N5 | **Approval binds to a content hash.** Any edit after approval returns the record to `under_review` | Prevents silent change after sign-off |
| N6 | **Quotation is by reference to an approved excerpt**, never by retyping | Prevents altered quotes |
| N7 | **Fixture data lives in a physically separate namespace** and cannot enter a real edition | Tests must not consume real IDs or pollute the archive |
| N8 | Documentation status gains **`disputed`** | Conflicting sources are certain in any archive |
| N9 | An edition has **releases** (`ED-000001.r1`, `.r2`…), each frozen | Corrections without mutating a released edition |

---

## 1. Locked principles

| # | Principle |
|---|---|
| **P1** | Source Material → Archive / Verified Record → Curated Digital Art Book / Experience |
| **P2** | The Archive is continuous and living from Day 1. The Digital Art Book is an edition of the Archive. The Museum is a future consumer/context of the Archive |
| **P3** | Edition is a first-class concept. The Birthday Edition (20 December 2026) is Edition 01. It is not a separate application or throwaway prototype |
| **P4** | Permanent opaque IDs. IDs never encode year, title, theme, location or other mutable meaning |
| **P5** | Curatorial groupings (Worlds, Journey chapters, themes) belong to the Experience layer. They are not factual properties of an artwork unless independently documented |
| **P6** | Artist Voice, Family Memory, Student Memory and Expert Commentary remain distinct typed entities. Artist Voice requires a direct artist source. Reported statements never automatically become Artist Voice |
| **P7** | Guest/Colleague memories remain distinguishable from the four existing voice types (fifth category proposed in §4.5) |
| **P8** | Visibility and documentation status are independent. PRIVATE ≠ VERIFIED. FAMILY access does not make information factual. "Under review" material stays explicitly labelled |
| **P9** | The publish gate is outside the frontend framework. The frontend receives only a validated published dataset |
| **P10** | Preservation masters, archive derivatives and web derivatives remain separate. Masters are never exposed through the website |
| **P11** | V1 has no database, Supabase, CMS, admin dashboard, custom authentication, IIIF, Deep Zoom infrastructure, WebGL or AI archive chatbot |
| **P12** | The public experience feels like a premium Japanese digital art book. The archive appears quietly through catalogue records, chronology, exhibition history, references and colophon, not a dashboard |
| **P13** | Astro is the provisional V1 framework. The core data, validation, publishing and asset pipeline stay framework-independent |
| **P14** | Hosting is a soft decision |
| **P15** | The Birthday Edition MUST be reproducible and frozen, and MUST be able to exist as an offline/static presentation for the family |

---

## 2. System architecture

### 2.1 Overview

```
CONTRIBUTORS ─▶ INTAKE ─▶ ┌──────── ZONE A: STEWARD (credentials, private) ─────────────┐
                          │ source/   receipts + tool-written manifests                  │
                          │ archive/  verified records (typed, statused, sourced)        │
                          │ book/     editions, worlds, chapters, stories, UI strings    │
                          │ storage:  masters · archive derivatives · release bundles    │
                          │                                                              │
                          │ CORE (framework-independent):                                │
                          │   validate → gate → project → derive → proof → lock          │
                          └───────────────┬──────────────────────────────────────────────┘
                                          │ PUBLISHED DATASET + web assets + routes + RELEASE.json
                                          ▼   (the only thing that crosses the boundary)
                          ┌──────── ZONE B: RENDERER (no credentials, no archive access) ┐
                          │ Astro (provisional) ─▶ static site                            │
                          └───────────────┬──────────────────────────────────────────────┘
                                          ▼
              FROZEN RELEASE BUNDLE ─▶ family origin (edge-identity access)
                                     ├▶ public origin
                                     └▶ offline package (encrypted in transit)

BACKUP: masters 3-2-1 · fixity checks · Git mirror · archive export · release snapshots
```

### 2.2 Components

| Component | Responsibility | Framework-dependent? |
|---|---|---|
| **Archive repository** | Source of truth for records (text only) | No |
| **Object storage** | Binaries: masters, archive derivatives, release bundles | No |
| **Core** | Schema, ID registry, ingest, derivatives, validation, gate, projection, proof sheet, lock, snapshot, fixity | No |
| **Published dataset** | Versioned JSON contract between Zone A and Zone B | No |
| **Renderer** | Turns dataset into static pages | Yes (Astro, replaceable) |
| **Release bundle** | Frozen, checksummed output of one edition release | No |
| **Access layer** | Edge identity control for non-public origins | Provider soft [P14] |

### 2.3 System invariants

| # | Invariant |
|---|---|
| I1 | Only Core reads `source/`, `archive/`, `book/` and storage masters. Only the renderer reads the dataset [P9] |
| I2 | Data flows one way: Source → Archive → Experience → Dataset → Site [P1] |
| I3 | Every output records its inputs: archive commit, book commit, core version, renderer version, dependency lockfile hashes |
| I4 | Masters never leave Zone A [P10] |
| I5 | Every check fails closed. No partial output is emitted |
| I6 | The renderer holds no secrets and no credentials |
| I7 | Released bundles are immutable [P3, P15] |
| I8 | Canonical URLs are produced by Core (`routes.json`), not by the renderer |

---

## 3. Source / Archive / Experience boundaries [P1, P2, P5]

| | **SOURCE MATERIAL** | **ARCHIVE / VERIFIED RECORD** | **CURATED EXPERIENCE** |
|---|---|---|---|
| **Is** | Evidence exactly as received | Attributed, sourced, statused records about works, people, events and statements | An edition: selection, sequence, editorial words, design |
| **Contains** | Masters; scans; recordings; catalogue and clipping scans; intake sheets and forms; permission documents; **Receipts** (who gave what, when, how) | Artwork, Exhibition, Event, Person, Series, Source, Asset, five voice types, Permission, Provenance | Edition, World, Chapter, Story (foreword, essay, chapter intro, caption, site copy), UI strings, design tokens |
| **Never contains** | Edits, crops, colour changes, interpretation | Narrative copy, curatorial grouping, ordering, promotion, layout | Independent facts. Every date, dimension, name and number resolves to an archive record |
| **Mutability** | Immutable, append-only | Versioned; corrections logged; approval bound to hash | Rebuildable; released editions frozen |
| **Default visibility** | `private` | `private` until approved | Set by the edition's ceiling |
| **Stored in** | Object storage (binaries) + `source/` (text manifests and receipts) | `archive/` (Git) | `book/` (Git) + release bundles (storage) |

### Boundary rules

| # | Rule |
|---|---|
| B1 | Dependency is one-way: Experience → Archive → Source. The archive never reads the book; a record never cites an edition |
| B2 | The book layer's schema has **no fact fields** (no date, dimension or attribution fields) |
| B3 | Curatorial classification lives only in `book/`. A World lists its works; an artwork carries no World, Chapter or theme. Only a **documented** Series may be stored on an artwork [P5] |
| B4 | Editorial text pulls structured facts by reference (§9.4). Prose claims pass the proof sheet |
| B5 | Corrections flow upstream. A wrong fact is fixed in the archive with a source, then rebuilt. Copy is never patched |
| B6 | An editorial claim absent from the archive is either added to the archive with a source or removed |
| B7 | **Rebuildability test:** deleting all outputs and rebuilding from archive + book yields an identical dataset |
| B8 | **Independence test:** given only the archive folder, without the website, a curator can produce a catalogue entry for every published work |
| B9 | **Editorial voice is not a Voice.** Forewords, letters and chapter copy are Stories in the experience layer, attributed to their authors. They are never archived as testimony about the artist |

---

## 4. Entity model

### 4.1 Catalogue

| Entity | Prefix | Layer | Purpose | Visibility floor* | V1 |
|---|---|---|---|---|---|
| Receipt | `RC` | Source | A batch received from one contributor on one occasion | `private` | Yes |
| Artwork | `TSJ` | Archive | A work, catalogued | `public` | Yes |
| Exhibition | `EXH` | Archive | An exhibition and the works it listed | `public` | Yes |
| Event | `EVT` | Archive | A documented life or career event (not an exhibition) | `public` | Yes |
| Person | `PER` | Archive | A person or organisation (`kind`) | `public` | Yes |
| Series | `SER` | Archive | A **documented** grouping; created on demand | `public` | On demand |
| Source | `SRC` | Archive | A documentary or oral source (publication, catalogue, poster, letter, recording, session…) | `public` | Yes |
| Asset | `AST` | Archive | A digital file object; points at its master | `public` | Yes |
| Artist Voice | `AV` | Archive | The artist's own words, direct source | `public` | Yes |
| Family Memory | `FM` | Archive | A family member's memory or testimony | `public` | Yes |
| Student Memory | `SM` | Archive | A student's memory of teaching and learning | `public` | Yes |
| Expert Commentary | `EC` | Archive | Professional commentary or criticism | `public` | Yes |
| Associate Memory | `AM` | Archive | A friend's, acquaintance's, guest's or colleague's memory, greeting or tribute | `public` | Yes |
| Permission | `PRM` | Archive | A grant of rights or consent (§6) | `private` | Yes |
| Provenance | `PRV` | Archive | Ownership and location history | `private` | Schema only; not populated |
| Edition | `ED` | Experience | A named edition and its releases | `public`† | Yes |
| World | `WLD` | Experience | A thematic curatorial grouping | n/a | Yes |
| Chapter | `CHP` | Experience | A chronological Journey chapter | n/a | Yes |
| Story | `STY` | Experience | Editorial text written for the book | n/a | Yes |

\* The **floor** is the most open visibility a record type may ever have. It is enforced at type level regardless of the record's own setting.
† Edition manifests are not themselves displayed. Their colophon-facing fields are projected.

### 4.2 Common envelope (every archive and book record)

| Field | Rule |
|---|---|
| `id`, `type`, `schema_version` | `type` MUST match the ID prefix and is immutable |
| `workflow` | `draft` · `under_review` · `approved` · `withdrawn` |
| `approval` | `{approved_by, approved_on, approved_hash, evidence}`; valid only while the record hash equals `approved_hash` |
| `visibility` | `public` · `archive` · `family` · `private`. Default `private` |
| `fixture` | Boolean. `true` only inside the fixture namespace (§8.6) |
| `notes_internal` | Never projected to any dataset |
| `legacy_refs` | Original filenames and spreadsheet keys received. Never an ID |

### 4.3 Claims (fact fields)

Core catalogue facts are **claims**, not bare values.

| Claim part | Rule |
|---|---|
| `value` | Structured (see §9.3) |
| `doc_status` | `documented` · `partially_documented` · `family_record` · `to_verify` · `disputed` · `unknown` (§5) |
| `sources` | Source IDs. `documented` requires at least one Source of a documentary kind |
| `alternatives` | Optional competing claims, each with sources. Required when `disputed` |
| `reviewed_by`, `reviewed_on` | Required for `documented` |

**A bare value is never projected.** Only a claim with a displayable status can appear in a dataset (§5.3).

### 4.4 Entity notes

| Entity | Key fields (beyond the envelope) |
|---|---|
| **Artwork** | `title` (localized claim; `original` flagged; translations carry origin/review); `title_variants[]` (as exhibited, with Exhibition ref); `date`, `medium`, `dimensions` (claims); `series` (documented Series ref, optional); `accession_number` (reserved, null). **No** image, World, Chapter, theme, owner or location field |
| **Asset** | `kind` (`photograph`, `scan`, `video`, `audio`, `document`); `role` (`full_view`, `detail`, `reverse`, `installation_view`, `document_page`…); `depicts[]`; `detail_of` + `region` (reserved for details); `photographer` (Person); `captured_on` (claim); `description`, `alt_text` (localized, with origin flags); `identifiable_persons[]`; `source_ref` (the Source it copies); `receipt_ref`; `permissions[]`; master reference (from the generated manifest, §11) |
| **Source** | `kind` (`publication`, `catalogue`, `poster`, `periodical_clipping`, `certificate`, `letter`, `photograph_print`, `recording`, `interview_session`, `oral_account`, `web_resource`, `other`); bibliographic fields as stated; `third_party_rights_holder`. Sources of kind `oral_account` cannot lift a claim to `documented` |
| **Exhibition** | `title`, `dates` (claims); `venue` (embedded: name, city, country as stated); `organiser` (Person); `works[]` = `{artwork, catalogue_no_as_stated, title_as_exhibited, note}` |
| **Event** | `kind` (`award`, `membership`, `education`, `publication`, `milestone`, `other`); `date` claim; `participants[]`; `description_neutral` (claim). No addresses. Place at city level at most |
| **Person** | `kind` (`person`, `organisation`); `names` (ja, reading, en, el); `relationships[]` (structured); `age_class` (`adult`, `minor`, `unknown`); `is_artist`; optional life-date claims; `contact` (private-only block, never projected) |
| **Series** | `name` (localized); `documented_by` (Sources). Members derive from `Artwork.series` |
| **Provenance** | Ownership and location. `private` floor. **Never** enters any dataset |
| **Receipt** | Contributor (Person), date, channel, items received (Asset/Source refs), rights and consent **as stated by the contributor** (documents attached), original language |

### 4.5 Voice entities [P6, P7]

**Five distinct types.** Each has its own collection, its own ID prefix, its own schema extension and its own defaults. They share one base schema and one code path. A type is immutable; changing it is a logged re-issue (§8.5).

#### Shared base

`author` (Person; or anonymous by recorded permission) · `author_display` (named / initials / anonymous, per Permission) · `relationship` (structured; must satisfy type constraint) · `language_original` · `form` · `medium` (text/audio/video) · `body` (`text.<lang>.md` or Asset refs) · `transcript` (derived, origin-flagged) · `translations` (each with origin/review) · `recorded_by` · `recorded_on` (claim) · `occasion` · `subjects[]` · `sources[]` · `excerpts[]` (§9.5) · `sensitivity` (third-party info, minor info, other) · `reports_words_of[]` (Person; non-artist types only) · `classification_note`.

**What documentation status means for a voice.** It covers *who said it, when, and whether the transcript and translation are accurate*. It never states that what was said is true.

#### Type definitions

| | **Artist Voice** `AV` | **Family Memory** `FM` | **Student Memory** `SM` | **Expert Commentary** `EC` | **Associate Memory** `AM` |
|---|---|---|---|---|---|
| **Statement basis** | The artist speaking or writing directly | Lived family life | Learning or teaching with him | Professional or critical assessment given in a professional capacity | Personal recollection, greeting or tribute from someone who knew or met him in another capacity |
| **Who may author** | Only a Person with `is_artist` | A family member | A student | A named professional | A friend, acquaintance, colleague, association member, invited guest or exhibition associate |
| **Provenance rule** | **Direct source required:** `recorded`, `written_by_artist`, or `published_verbatim` (flag `mediated: true`, with citation) | Testimony. May report his words via `reports_words_of` | Testimony. May report his words | Often a publication with its own Source; or commissioned for an edition | Testimony or greeting. May report his words |
| **Type-specific fields** | `attribution_mode`; `confirmed_by_artist` (bool, date) | `relationship_detail`; `household_context` (no addresses) | `teaching_context` (period, class, venue as stated) | `affiliation_as_stated`; `publication_ref`; `quotation_limit` (from Permission) | `association_context`; `form` includes `greeting`, `tribute` |
| **Consent basis** | The artist's own | Author + any named third parties | Author + any visible students | Author + publisher where pre-existing | Author + any named third parties |
| **Default visibility** | `private` | `private` | `private` | `private` | `private` |
| **Display label key** | `voice.artist` | `voice.family` | `voice.student` | `voice.expert` | `voice.associate` |

#### Classification test (applied to the *statement*, not the person)

1. Directly the artist's own recorded or written words? → **Artist Voice**.
2. Otherwise, what is its primary basis?
   - lived family life → **Family Memory**
   - learning or teaching → **Student Memory**
   - professional or critical assessment → **Expert Commentary**
   - personal recollection, greeting or tribute from his wider circle → **Associate Memory**
3. Ties are decided by the steward and recorded in `classification_note`.

The same person may author several records of different types. `relationship` may hold several values.

#### Voice rules

| # | Rule |
|---|---|
| VR1 | Reported speech is never Artist Voice. It is carried by the reporting type with `reports_words_of` and displayed as reported |
| VR2 | An Artist Voice with no direct source fails validation |
| VR3 | An Artist Voice translation MUST be `human_reviewed` by a fluent reviewer. `confirmed_by_artist` SHOULD be sought |
| VR4 | Expert Commentary that reproduces a publication requires a Permission with basis `third_party_publication_permission` |
| VR5 | A voice with `sensitivity` flags cannot enter any edition until each flag is cleared by a Permission or an approved excerpt |
| VR6 | The type list is closed. Adding a type is a specification change |
| VR7 | "Voice" survives only as a **derived view** ("everything said about TSJ-…"), computed across the five collections at build time |

### 4.6 Experience entities

| Entity | Content |
|---|---|
| **World** | Thematic grouping: localized name; ordered `placements[]` (archive refs, each with an optional Story ref); introduction Story. No facts |
| **Chapter** | Chronological Journey grouping: localized name; display span as text; ordered placements. No facts |
| **Story** | `kind` (`foreword`, `essay`, `chapter_intro`, `caption`, `site_copy`); author (Person); text files per language; `origin` and `review` per language; `cites[]` (archive IDs it depends on) |
| **Edition** | See §7 |

Themes are a vocabulary list in `book/themes`. They are tags used by editions, not entities.

### 4.7 Relationship ownership

Each relationship is stored **once**, on the side that owns the evidence. The inverse is computed at build time.

| Relationship | Stored on | Inverse (derived) |
|---|---|---|
| Exhibition lists Artwork | Exhibition | Artwork's exhibition history |
| Asset depicts Artwork/Person/Event | Asset | Artwork's images |
| Voice is about Artwork/Exhibition/Event | Voice | "Voices about X" view |
| Artwork belongs to Series | Artwork | Series membership |
| World / Chapter contains Artwork | World / Chapter placements | Where a work appears |
| Edition selects World / Chapter / Story | Edition | Edition membership |
| Claim cites Source | The claim | Source usage |
| Asset copies Source | Asset | Source scans |
| Permission covers Asset / Voice / Story | Permission `subjects[]` | Coverage view |

**Which image represents a work in an edition is an experience-layer choice** (a placement). The archive stores only each asset's documentary `role`.

---

## 5. Status model [P8]

Five independent axes plus one text attribute. **No axis implies another.**

| Axis | Question | Values | Applies to |
|---|---|---|---|
| **A. Kind** | What is this? | Entity type; voice type; Source `kind`; Story `kind` | Structural, immutable |
| **B. Documentation status** | How well is this claim substantiated? | `documented` · `partially_documented` · `family_record` · `to_verify` · `disputed` · `unknown` | Each claim; voice attribution/transcript accuracy |
| **C. Workflow** | Where is this record in review? | `draft` · `under_review` · `approved` · `withdrawn` | Every record |
| **D. Visibility** | What is the widest audience it may ever reach? | `public` · `archive` · `family` · `private` | Every record and asset |
| **E. Rights & consent** | May this use be shown? | Derived from Permissions: `cleared` · `pending` · `denied` · `unknown` · `withdrawn` · `expired` | Assets, voices, stories, persons named or depicted |
| **F. Text origin** | Who wrote or translated this? | `human_written` · `human_reviewed` · `ai_draft` | Every text and every translation |

### 5.1 Independence, illustrated

| Combination | Meaning |
|---|---|
| `private` + `documented` | Verified but not for any audience. **PRIVATE ≠ hidden-because-unverified** |
| `family` + `to_verify` | Shown in the family edition, **always labelled**. Family access does not make it factual |
| `public` + `family_record` | Allowed publicly, **labelled** |
| `public` + `to_verify` | **Impossible.** The gate rejects it |
| `approved` + `cleared` + `to_verify` claim | Approval does not verify a claim. It approves the record *as labelled* |

### 5.2 Workflow rules

| # | Rule |
|---|---|
| W1 | `approved` requires a named approver, a date, evidence (e.g., signed-off proof sheet) and the record's current content hash |
| W2 | Any change to an `approved` record changes its hash, which returns it to `under_review` automatically [N5] |
| W3 | `withdrawn` retires a record from all **future** releases. It is preserved, and its ID stays reserved |
| W4 | There is no `published` status. Publication is a release of an edition (§7) |
| W5 | Approver roles by type: family material → designated family approver; Artist Voice → the artist or his designated family approver; all → steward for final approval. Named in `docs/runbook` |

### 5.3 Core Display Policy

This policy is fixed in Core. An edition may **tighten** it and MUST NOT loosen it.

| Documentation status | Edition ceiling `public` | Edition ceiling ≥ `family` | Label |
|---|---|---|---|
| `documented` | Shown | Shown | None |
| `partially_documented` | Shown **with label** | Shown with label | `label.partial` |
| `family_record` | Shown **with label** | Shown with label | `label.family_record` |
| `to_verify` | **Never** | Only if the edition opts in; **always labelled** | `label.to_verify` |
| `disputed` | **Never** | Only if the edition opts in; labelled, alternatives shown | `label.disputed` |
| `unknown` | Not shown (absence) | Not shown | n/a |

- The dataset marks every displayed claim with `must_label` and a label key. The renderer MUST render it. A conformance test enforces this (§20).
- A record enters an edition only if all of that edition's `required_claims` for its kind are displayable under this policy. An artwork whose title is `to_verify` cannot enter a public edition.
- A **Level 1** presentation MAY omit a labelled claim. It MUST NOT show it unlabelled.

---

## 6. Rights and consent model [N4]

### 6.1 Permission entity

| Field | Rule |
|---|---|
| `basis` (immutable) | `copyright_licence` · `reproduction_permission` · `likeness_consent` · `statement_publication_consent` · `contributor_agreement` · `third_party_publication_permission` |
| `grantor` | Person or organisation. For a depicted minor, a guardian |
| `subjects[]` | Asset / voice / Story / Person / Artwork IDs covered |
| `scope` | `max_visibility`; `editions` (any or named); `uses` (web display, excerpt only, translation, print, audio/video); `languages` |
| `conditions` | Localized credit line; name display (named / initials / anonymous); no-crop; quotation limit; other |
| `evidence` | Source ref: signed form, message, or recorded verbal grant |
| `state` | `pending` · `granted` · `denied` · `withdrawn` · `expired` |
| `granted_on`, `expires_on`, `recorded_by`, `reviewed_by` | Expiry is checked at build time against the release date |

### 6.2 Rules

| # | Rule |
|---|---|
| R1 | **Nothing is presumed.** An asset is `cleared` only through Permission records, including the artist's own works. The system never infers a rights holder |
| R2 | An asset in an edition needs a covering `copyright_licence` or `reproduction_permission` **and** a `likeness_consent` for each identifiable person depicted |
| R3 | A depicted person with `age_class` other than `adult` requires a guardian as grantor. `unknown` is treated as `minor` |
| R4 | A voice needs `statement_publication_consent` covering the edition's audience. If the consent is excerpt-only, only approved excerpts may appear |
| R5 | Third-party material (catalogues, posters, clippings) needs `third_party_publication_permission`. Without it, only a bibliographic citation is projected |
| R6 | A person named inside a statement needs consent or the statement is limited to excerpts that omit the name |
| R7 | Credit lines and name-display choices come **only** from Permission conditions |
| R8 | Coverage is per (subject × audience × edition × use × language). It is never a project-wide flag |
| R9 | **Withdrawal:** the Permission becomes `withdrawn`. All future releases exclude the subject. For a live public release, the steward issues a new release without it. The frozen snapshot moves to private cold storage |
| R10 | A public-ceiling release requires a recorded **clearance review** (§7.2) |
| R11 | Rights presumptions are legal questions. This specification provides the mechanism and is not legal advice |

---

## 7. Edition model [P3, P15]

### 7.1 Definition

An **Edition** is a configuration over the one archive: audience ceiling + selection + sequence + editorial copy + languages + policies + a release history. It is not a fork of code or data.

### 7.2 Edition record

| Field | Rule |
|---|---|
| `id`, display `name` (localized) | e.g., ID `ED-000001`; display name is editorial |
| `audience_ceiling` | `public` · `archive` · `family`. `private` is never a ceiling |
| `documentation_policy` | `opt_in_unverified` (boolean; **not permitted at ceiling `public`**); `required_claims` per record kind |
| `language_policy` | `required[]`, `optional[]`, fallback marker rules |
| `structure` | Front matter (foreword Story); Chapters; Worlds; Reference matter (chronology, exhibition history, catalogue, sources); colophon. Each entry is a placement |
| `outputs` | `online`; `offline` |
| `clearance_review` | `{required, reviewer, date, notes}`. **Required when ceiling is `public`** |
| `dates` | `content_freeze`, `build_freeze`, `target_release` |
| `derived_from` | Prior edition IDs, if any |
| `status` | `draft` · `candidate` · `approved` · `released` · `superseded` · `withdrawn` |

### 7.3 Releases

| Concept | Rule |
|---|---|
| **Release** | `ED-000001.r1`, `.r2`…. Each release is one frozen bundle |
| **Release lock** (`release.json`, in Git) | Archive commit, book commit, core version, renderer version, lockfile hashes, dataset hash, asset-manifest hash, approvals, proof-sheet reference, clearance review |
| **Bundle** (in storage) | Dataset, web assets, static site, offline package if requested, checksums, README |
| **Immutability** | A released bundle is never modified. Errors are corrected by a new release (`r2`) or a later edition, recorded as errata in the colophon |
| **Live pointer** | An origin serves one release of one edition. Rollback is a pointer change to an earlier release |

### 7.4 Edition 01

| Parameter | Value |
|---|---|
| ID / display | `ED-000001` / "Edition 01" |
| Title | TSUJI WORLD — Birthday Edition |
| Target release | 20 December 2026 |
| Audience ceiling | `family` |
| Outputs | `online` (identity-gated) and `offline` |
| Languages | `ja`, `en`, `el` (all required) |
| Same as every edition | Same archive, schema, statuses, gate, pipeline, renderer, canonical paths |
| Edition-specific | Selection, sequence, edition Stories (e.g., a letter), audience, launch date, access control |
| **Rule** | **An edition may widen what is shown. It MUST NOT loosen how it is labelled** |

### 7.5 Reproducibility [P15]

- Every input is pinned in the release lock. Builds run from the lock, not from "latest".
- **Target:** two builds from one lock produce a **byte-identical dataset** and an identical asset manifest. The static site SHOULD also be identical. Any nondeterminism found is documented, not hidden.
- Released bundles are copied to cold storage with checksums (§16).

---

## 8. ID strategy [P4]

### 8.1 Format

`PREFIX-NNNNNN`: an uppercase prefix, a hyphen and six digits. Example shape: `TSJ-000123`. Prefixes are listed in §4.1. Editions use the same format (`ED-000001`); "Edition 01" is a display name.

### 8.2 Rules

| # | Rule |
|---|---|
| ID1 | IDs are minted only by Core (`mint`). Never by hand |
| ID2 | IDs are **assigned at receipt** (RECEIVE), not at curation |
| ID3 | IDs encode **only** the entity type and registration sequence. They MUST NOT encode year, title, theme, World, location, owner, format or status |
| ID4 | IDs are permanent. **A tombstoned ID is never reused.** The registry keeps tombstones |
| ID5 | The counter and tombstones live in a Core-owned registry file. Minting is single-writer (the steward) |
| ID6 | Hand-typed IDs (intake sheets) MUST be accompanied by a human label. Ingest checks existence, prefix and label agreement |
| ID7 | Content references IDs, never URLs or filenames |

### 8.3 Names derived from IDs

| Thing | Pattern |
|---|---|
| Record folder | `archive/<collection>/<ID>/` |
| Master | `AST-NNNNNN.master.<ext>` (+ `.xmp` sidecar) |
| Archive derivative | `AST-NNNNNN.arch.<ext>` |
| Web derivative | `AST-NNNNNN.<width>.<contenthash>.<fmt>` |
| Canonical path | `/works/tsj-nnnnnn`, `/exhibitions/exh-nnnnnn`, …; generated in `routes.json` |
| Language paths | `ja` at root, `/en/…`, `/el/…` |

### 8.4 Filenames

All filenames are **ASCII**, derived from IDs. Japanese appears only inside content. This avoids Unicode normalization problems across operating systems.

### 8.5 Re-issue (type change or split)

The record gets a **new ID** with `supersedes`. The old ID is tombstoned with `superseded_by` and resolves as a redirect. Type change is therefore always a deliberate, logged act [P6].

### 8.6 Fixture namespace

Test data uses a separate registry and IDs shaped `FX-<PREFIX>-NNNNNN`, with `fixture: true`. Fixture records live in `core/fixtures/`, never in `archive/`. The gate rejects any fixture ID or fixture-flagged record in a non-fixture edition.

---

## 9. Content structure

### 9.1 Record layout

- **Every record is a folder:** `<collection>/<ID>/record.yaml`. Long text sits beside it as `text.<lang>.md`. Uniform structure beats clever structure.
- **Authored vs tool-written:** authored fields live in `record.yaml`. Generated fields (checksums, sizes, dimensions, derivative lists) live in tool-written sidecars in `source/manifests/` and are verified by CI.
- **Formats:** records in strict YAML 1.2 subset (no anchors, tags or merge keys), parsed by schema; long text in plain CommonMark. **No MDX. No components in content.**
- Encoding UTF-8, NFC-normalized, LF line endings.

### 9.2 Localized strings

Short strings are inline by language code, each with `origin` and `review`. Long text is per-language files. Every text item records `language_original`. See §12.

### 9.3 Claim value shapes

| Claim | Value |
|---|---|
| **Date** | `{as_stated, era_text?, earliest, latest, precision, circa}`. Original wording is preserved next to the normalized Gregorian range |
| **Dimensions** | `{as_stated, h_cm?, w_cm?, d_cm?, order: "H×W", canvas_number_as_stated?}`. Recorded as stated. Centimetres are never derived from a canvas number or vice versa |
| **Title** | `{original: {lang, text, reading?}, translations: {…}, variants[]}` |

### 9.4 Editorial text tokens

Editorial text refers to the archive by token, resolved by **Core at compile time**, not by the renderer:

- `{{ref:ID}}` → a link plus the localized name or title
- `{{fact:ID.claim}}` → a claim's displayable value

An unresolvable token, or one that points at a claim not displayable in that edition, **fails the build**. Prose claims not expressible as tokens go through the proof sheet.

### 9.5 Excerpts [N6]

A voice may hold `excerpts[]`: approved sub-texts with their own IDs (`e1`, `e2`…), each carrying its own approval, visibility and Permission scope. Editions quote **by excerpt ID**. Quoted text is never retyped.

---

## 10. Repository structure

One private Git repository holds all **text**. Binaries live in object storage.

```
tsuji-world/
├─ source/
│  ├─ receipts/RC-NNNNNN/record.yaml
│  └─ manifests/AST-NNNNNN.json          tool-written: storage key, sha256, bytes, dims, ingest info
├─ archive/
│  ├─ _registry/                         ID counters + tombstones (Core-owned)
│  ├─ artworks/  exhibitions/  events/  people/  series/  sources/  assets/
│  ├─ voices/{artist,family,student,expert,associate}/
│  ├─ permissions/
│  └─ provenance/                        private floor; never projected
├─ book/
│  ├─ editions/ED-NNNNNN/{edition.yaml, releases/rN.release.json}
│  ├─ worlds/  chapters/  stories/
│  ├─ themes.yaml
│  └─ ui/{ja,en,el}.json                 UI string catalogues (renderer-independent)
├─ core/                                 framework-independent (§17)
│  ├─ schema/  registry/  ingest/  derive/  validate/  gate/
│  ├─ dataset/  proof/  snapshot/  fixity/  cli/
│  └─ fixtures/                          synthetic data, FX- namespace
├─ site/                                 renderer (Astro), styles, tokens, islands
└─ docs/                                 data dictionary, runbook, rights policy, style guide, glossary
```

| # | Rule |
|---|---|
| RS1 | `main` is protected. Changes to `approved` records or any edition record require review by a role named in `docs/runbook` |
| RS2 | No binaries in Git. Masters are never in the repository |
| RS3 | Nothing private lives under any web root. `site/` never contains archive data |
| RS4 | The repository is mirrored to a second remote (§16) |
| RS5 | `site/` and `core/` are separable: `core/` MUST run and pass its tests without `site/` |

---

## 11. Asset and image pipeline [P10]

### 11.1 Tiers

| Tier | Purpose | Stored | Visibility |
|---|---|---|---|
| **Preservation master** | Original as received. **Never modified** | Private, versioned storage; SHA-256 recorded | Never exposed |
| **Archive derivative** | Full-quality, colour-managed, for internal or archive-edition viewing. Carries embedded metadata (ID, creator, rights) | Private storage | Never public |
| **Web derivative** | Delivery images: sRGB, metadata stripped (no GPS or personal EXIF), AVIF + WebP + JPEG fallback, width ladder, small placeholder | Per-release bundle; copied to the public origin **only** for public releases | Per edition ceiling |

### 11.2 Ingest

1. Mint `AST` ID; write `Receipt`. 2. Copy the original to master storage; compute SHA-256; verify the stored copy. 3. Write the tool-written manifest (original filename, size, dimensions, format, capture metadata as found). 4. Write an XMP **sidecar** next to the master (the master's bytes stay untouched). 5. Create a `draft` Asset record, `visibility: private`. 6. Generate the archive derivative.

### 11.3 Derivatives

- Generated only from masters, by Core, using a **versioned derivative profile** (widths, formats, quality). Profile version is recorded in each manifest. The profile is a soft decision.
- Web derivatives are generated **per release**, only for assets the gate admitted.
- Filenames include a content hash. Assets are immutable and cache-forever.
- **The interface never crops, filters or colour-adjusts an artwork.** A crop is a `detail` and is labelled.

### 11.4 Reserved for later (no infrastructure in V1) [P11]

`detail_of` + `region` fields exist on Asset. No tiling, no IIIF, no Deep Zoom pipeline. If a future master is large enough and zoom is intended, tiles become a derivative type built from the same masters.

### 11.5 Video and audio

Masters preserved untouched. Core produces an MP4 access copy and a poster frame. Transcripts are derived, origin-flagged records. **Hosting method is a soft decision.**

### 11.6 Storage layout (object storage, not Git)

```
masters/         private, versioned          AST-NNNNNN/AST-NNNNNN.master.<ext> (+ .xmp)
archive/         private                     AST-NNNNNN/AST-NNNNNN.arch.<ext>
releases/        private until deployed      ED-NNNNNN/rN/ {dataset, web, site, offline, checksums}
web-public/      public origin storage       only assets from public releases
web-family/      identity-gated              only assets from family releases
backups/         see §16
```

Storage provider and bucket technology are soft [P14].

---

## 12. Multilingual architecture

| Rule | Detail |
|---|---|
| **Facts neutral, words localized** | IDs, dates, dimensions, relationships and media are stored once. Titles, descriptions, captions and stories are per language |
| **Original is canonical** | Each text records `language_original`. Translations are marked as translations |
| **Storage** | Short strings inline by code (`ja`, `en`, `el`). Long text as `text.<lang>.md` beside its record. **No parallel per-language trees** |
| **Text origin gate** | Only `human_written` or `human_reviewed` text is eligible. `ai_draft` blocks the release. Applies to translations, transcripts and alt text |
| **Edition language policy** | Each edition declares `required` and `optional` languages. `ja` is required in every edition |
| **Fallback** | Missing translation → show the original with a visible marker. **Never machine-translate at build or at runtime** |
| **Names** | `{ja, reading, en, el?}`. English uses Western order (Tsukasa Tsuji) |
| **Titles** | `original`, `reading?`, translations, and as-exhibited variants |
| **UI strings** | `book/ui/<lang>.json`, renderer-independent |
| **URLs** | Core-generated. `ja` at root; `/en/…`, `/el/…`. Correct `lang` and `hreflang` in the dataset |
| **Review** | A native Japanese editor reviews all Japanese editorial text before `approved` |
| **Greek** | `el` is required in Edition 01 (Appendix A, A6) |

---

## 13. Publishing pipeline

### 13.1 Stages

| # | Stage | Input → Output | Control | Role |
|---|---|---|---|---|
| 0 | **COLLECT** | Contributors → intake channel (shared folder + intake sheet) | Naming convention | Contributor, family |
| 1 | **INGEST** | Intake → Receipt, IDs, masters, manifests, `draft` records (`private`) | ID rules; checksum verify | Steward |
| 2 | **VERIFY** | Draft → claims with sources and `doc_status` | V-G5 | Steward, family approver |
| 3 | **CURATE** | Archive → edition structure, Worlds, Chapters, Stories | B1–B6 | Steward, editors |
| 4 | **TRANSLATE** | Text → translations with origin/review | V-T1, V-T2 | Translators, native Japanese editor |
| 5 | **REVIEW RIGHTS** | Assets, voices, Stories → Permissions | R1–R11 | Steward, family approver |
| 6 | **APPROVE** | Record → `approved` bound to hash | W1–W5 | Named approvers |
| 7 | **COMPILE** | Core: validate → gate → project → derive → proof → lock | §14 | Automated (Zone A) |
| 8 | **PROOF (校正)** | Proof sheet → human sign-off | Acknowledge items | Steward, family approver |
| 9 | **RENDER** | Dataset → static site | §17 | Automated (Zone B) |
| 10 | **RELEASE** | Bundle frozen, checksummed, deployed by pointer, copied to cold storage | I7, V-D2 | Steward |
| 11 | **MAINTAIN** | Errata, corrections, fixity, backups | §16 | Steward |

### 13.2 CI structure

| Job | Zone | Credentials | Produces |
|---|---|---|---|
| **A: compile** | A | Yes (archive, storage) | Dataset, web assets, `routes.json`, proof sheet, lock, `RELEASE.json` |
| **B: render** | B | **None** | Static site from A's artifact only |
| **C: release** | A | Deploy only | Frozen bundle, deployment pointer, cold-storage copy |

Job B receives **only** A's artifact. The renderer cannot read `archive/`, `source/`, `book/` or any master path. This is enforced by the job's filesystem, not by convention [P9]. Job C re-verifies `RELEASE.json` hashes before deploying.

### 13.3 Proof sheet

A human-readable static document, `private`, listing:

- **Newly included** vs the previous release: records, assets, displayed claims (with status and label), quotations (by excerpt ID), permission coverage.
- **Excluded and why**: every record the gate rejected, with the failing rule.
- **Changed text** with before/after.
- **Editorial prose that states numbers, dates or superlatives** (V-T5), each to be acknowledged.
- Counts, warnings, and the sign-off block.

---

## 14. Validation and fail-closed rules [P8, P9, P10]

**Semantics.** Any **Fail** aborts the run: non-zero exit, **no dataset emitted**, no deployment. **Acknowledge** items must be signed off in the proof sheet before release. **There is no override flag for any Fail rule.** Changing a rule is a specification change made through review.

### 14.1 Schema and structure

| ID | Rule | Sev. |
|---|---|---|
| V-S1 | Every record validates against the schema for its `type` and `schema_version`. Unknown fields are rejected | Fail |
| V-S2 | ID format and prefix match the type; IDs unique, registered, not tombstoned | Fail |
| V-S3 | `type` is immutable. A prefix/type mismatch, or a type change without re-issue, is rejected | Fail |
| V-S4 | Records use the strict YAML subset. Filenames are ASCII | Fail |

### 14.2 References and layers

| ID | Rule | Sev. |
|---|---|---|
| V-R1 | All references resolve | Fail |
| V-R2 | A **required** reference to a record ineligible for the edition fails the record. An **optional** reference is dropped and logged | Fail / Log |
| V-R3 | Relationships are stored only on the owning side (§4.7) | Fail |
| V-R4 | No archive record references a `book/` record (B1) | Fail |
| V-R5 | Book records contain no fact fields (B2) | Fail |
| V-R6 | No curatorial field on Artwork; `series` refers only to a documented Series (B3) | Fail |

### 14.3 Gate

| ID | Rule | Sev. |
|---|---|---|
| V-G1 | `workflow = approved` **and** `approved_hash` equals the current content hash | Fail |
| V-G2 | Record visibility is within the edition ceiling and no more open than its type floor | Fail |
| V-G3 | Every displayed claim satisfies the Core Display Policy; the edition's `required_claims` are displayable | Fail |
| V-G4 | `opt_in_unverified` is not set on a `public` ceiling | Fail |
| V-G5 | `documented` requires at least one documentary Source, a reviewer and a date; `oral_account` alone is insufficient; `disputed` carries alternatives | Fail |
| V-G6 | Fixture IDs or fixture-flagged records never enter a non-fixture edition | Fail |
| V-G7 | Withdrawn records are excluded; a placement of a withdrawn required record fails | Fail |
| V-G8 | Edition record `approved`; a `public` ceiling has a completed clearance review | Fail |
| V-G9 | Every displayed non-`documented` claim carries `must_label` and a label key | Fail |

### 14.4 Rights and consent

| ID | Rule | Sev. |
|---|---|---|
| V-P1 | Each displayed asset has granted, unexpired Permissions covering audience × edition × use × language | Fail |
| V-P2 | Each identifiable depicted person has likeness consent; `minor` or `unknown` requires a guardian grantor | Fail |
| V-P3 | Each voice has publication consent covering the audience; excerpt-only consent is honoured; named third parties and sensitivity flags are cleared | Fail |
| V-P4 | Third-party material without permission is projected as a citation only | Fail (for full text) |
| V-P5 | Credit lines and name display come only from Permissions | Fail |

### 14.5 Voices

| ID | Rule | Sev. |
|---|---|---|
| V-V1 | Artist Voice requires a direct source (`recorded`, `written_by_artist` or `published_verbatim` with `mediated: true`) and an `is_artist` author | Fail |
| V-V2 | Reported speech appears only through `reports_words_of` on non-artist types | Fail |
| V-V3 | Each type's required fields are present | Fail |
| V-V4 | An Artist Voice translation is `human_reviewed` | Fail |

### 14.6 Text

| ID | Rule | Sev. |
|---|---|---|
| V-T1 | No `ai_draft` text or translation appears in any displayed field | Fail |
| V-T2 | Required languages present. Fallback shows the original with a marker. No machine translation | Fail |
| V-T3 | Every `{{ref}}` and `{{fact}}` token resolves to something displayable in this edition | Fail |
| V-T4 | Quotations reference approved excerpt IDs only | Fail |
| V-T5 | Editorial prose containing numbers, dates or superlatives is flagged | Acknowledge |

### 14.7 Assets

| ID | Rule | Sev. |
|---|---|---|
| V-A1 | Every master exists and its SHA-256 matches its manifest | Fail |
| V-A2 | Web derivatives are sRGB, contain no GPS or personal metadata (verified by reading the outputs), and record their profile version | Fail |
| V-A3 | No master path and no archive-derivative path appears in any output | Fail |
| V-A4 | Every displayed image has human-approved alt text | Fail |
| V-A5 | Derivative sizes within budget | Acknowledge |

### 14.8 Output and reproducibility

| ID | Rule | Sev. |
|---|---|---|
| V-O1 | Dataset objects are built by **allow-list projection** per type and audience. A field not on the list cannot pass | Fail |
| V-O2 | Output scan: no `PRM-`, `PRV-`, `RC-` IDs; no `notes_internal`; no `contact`; nothing above the ceiling; no file outside the manifest | Fail |
| V-O3 | Dataset validates against the published dataset JSON Schema | Fail |
| V-O4 | `routes.json` complete and unique. A canonical path for an existing ID never changes without a declared redirect | Fail |
| V-O5 | Offline output has relative links and makes no network requests | Fail |
| V-O6 | Non-public releases contain no third-party scripts or trackers | Fail |
| V-D1 | Release lock complete; rebuild yields a byte-identical dataset | Fail |
| V-D2 | Release bundle checksums are recorded and re-verified after copy to cold storage | Fail |

---

## 15. Public / family / private architecture [P8, P14, P15]

### 15.1 Levels

| Visibility | Audience | Editions | Notes |
|---|---|---|---|
| `public` | Anyone | Public edition | Public origin; no authentication |
| `archive` | Invited curators, researchers | **Reserved.** No V1 edition | Level exists in the schema so it need not be added later |
| `family` | Named family | Edition 01 | Separate origin, identity-gated; and the offline package |
| `private` | Steward only | **Never in any edition** | Stored, preserved, reachable only through Core tooling |

Ordering: `public < archive < family < private`. A record is eligible when its visibility is at or below the edition's ceiling. `private` is never a ceiling.

### 15.2 Deployment matrix

| Edition | Origin | Access | Storage prefix |
|---|---|---|---|
| Public | Public domain | None | `web-public/` |
| Family (Edition 01) | Separate origin | **Identity-based access control at the edge** | `web-family/` |
| Offline package | Physical | Handed over privately; **encrypted in transit** | n/a |

### 15.3 Access-control requirements (provider is soft)

- Identity-based (e.g., emailed one-time code or equivalent), with per-person revocation.
- Usable by non-technical recipients, including an elderly viewer.
- No secret in client code. Default deny.
- A separate origin from the public site; separate storage prefix.
- **A hidden route or `noindex` is not access control.** No client-side password gate is used as security.

### 15.4 Privacy invariants

| # | Invariant |
|---|---|
| PV1 | Ownership, current location and provenance are never in any dataset. The floor of `Provenance` is `private` |
| PV2 | No addresses, valuations, insurance or health information are stored at all (data minimisation) |
| PV3 | Home photographs: no address; GPS stripped from derivatives; the steward reviews for revealing detail (entrances, layouts, security) before approval |
| PV4 | Identifiable minors require a guardian's likeness consent (R3). Default `private` |
| PV5 | Raw interviews and recordings stay `private`. Only approved excerpts travel |
| PV6 | Contact details live only in `Person.contact`, never projected |
| PV7 | Family and offline releases contain no third-party scripts (V-O6) |
| PV8 | An offline package can be copied. Content is placed at `family` only if the family is comfortable with that |

---

## 16. Preservation and backup architecture [P10, P15]

| Item | Protection |
|---|---|
| **Masters** | Three copies, two media types, one offsite. Versioned storage plus two independent copies (for example, a family-held drive and a second provider or offline drive stored elsewhere) |
| **Fixity** | Scheduled checksum verification of every master and every release bundle against manifests; at least yearly, plus after every copy or migration |
| **Records** | Git repository mirrored to a second remote. Periodic **archive export**: a self-describing package containing all records, manifests, data dictionary, schema and checksums, with a plain-language README, readable **without the website** |
| **Releases** | Every release bundle copied to cold storage with checksums. Released editions are kept forever, including superseded ones |
| **Metadata** | Preserved four ways: in the ID-named filename, in the XMP sidecar, in the tool-written manifest and in the record |
| **Formats** | Open formats. Originals retained. Documents as PDF/A where derived. Audio and video keep the original plus an access copy |
| **Encryption** | Private tiers encrypted at rest. Recovery keys held by at least two designated people. Key custody is documented |
| **Continuity** | Domain, repository organisation and storage accounts are **family-owned**. `docs/runbook` covers accounts, renewals, restore, roles and a successor procedure |
| **Tombstones** | The ID registry is part of the backup set. Tombstones are permanent |
| **Restore drill** | Restoring from backups alone MUST succeed (T20) and is repeated on a schedule |
| **Principle** | The public site is never the only copy |

---

## 17. Astro boundary and the framework-independent core [P9, P13]

### 17.1 Core (no framework dependency)

| Module | Responsibility |
|---|---|
| `schema` | Entity schemas, `schema_version`, migrations, published dataset JSON Schema |
| `registry` | Minting, tombstones, lookups |
| `ingest` | Receipts, masters, manifests, sidecars |
| `derive` | Derivative profiles and generation |
| `validate` | §14 rules |
| `gate` | Eligibility, Core Display Policy, allow-list projection, token and excerpt resolution |
| `dataset` | Dataset emission, `routes.json` |
| `proof` | Proof sheet |
| `snapshot` | Release lock, bundle freezing, archive export |
| `fixity` | Checksum verification |
| `cli` | Commands over the above |

Core is written in TypeScript and MUST build and pass its tests **without `site/`** (RS5). It publishes a **types-only package** generated from the dataset schema.

### 17.2 Dataset contract

```
dataset/
├─ manifest.json        dataset_version, edition, release, lock hash, languages, counts
├─ records/<type>/<ID>.json     projected, allow-listed, localized, tokens resolved
├─ assets.json          per asset: derivative ladder (path, width, format, bytes, hash), placeholder, alt, credit
├─ routes.json          canonical path per record per language (generated by Core)
├─ strings/<lang>.json  UI catalogues
└─ schema/              JSON Schema for every file above
```

Records carry displayed claims with `status`, `must_label` and label keys, resolved localized text, minimal summaries of referenced records, evidence-type label keys and credit lines.

### 17.3 Renderer boundary (Astro, provisional)

| | |
|---|---|
| **Inputs** | The dataset, its web assets, `book/ui` strings (via the dataset) and design tokens |
| **Outputs** | A static site, in `online` and `offline` modes |
| **MUST NOT** | Read `archive/`, `source/`, `book/` or any master; hold credentials; compute facts, statuses or URLs; contain content; import Core except the types package |
| **MAY** | Templates, CSS, islands (interactive pieces). Islands MUST NOT read the archive or call external services |
| **MUST** | Render every `must_label` label (V-G9, T18). Function without JavaScript for reading content. Honour reduced motion. Emit only URLs from `routes.json`. Support the offline mode (17.5) |

### 17.4 Renderer requirements

- Content pages are real HTML that reads without JavaScript. Interactivity enhances.
- **The artwork is never cropped, filtered or overlaid with text.**
- No MDX or content components. No framework-specific content formats.
- Design tokens live in a plain CSS custom-properties file.
- Targets, not guarantees (soft): hero image ≈ 400 KB or less; initial JavaScript ≈ 100 KB or less on content pages; heavier islands lazy-loaded; self-hosted subset fonts.
- **Page inventory the renderer must be able to render from the dataset:** cover; foreword; Journey (chapters); Worlds; work plate with Record panel; artist; the House; Future Museum; Reference (chronology, exhibition history, catalogue of published works, sources); colophon; a table-of-contents index. The Artist, House and Future Museum pages are Stories placed in the edition structure. They are not new dataset types [P12].

### 17.5 Offline mode [P15]

Relative links resolving to concrete files; no network requests; no third-party resources; no reliance on a service worker or runtime `fetch` of local files. It MUST be verified on the **actual target device** (T19). Packaging (folder, archive, or bundled minimal local server) is decided at M7 against that device.

### 17.6 Independence

- The dataset is self-sufficient, and the renderer holds no logic that another renderer could not reproduce from the dataset.
- **Reconsider Astro** if any of these becomes true: persistent app-like client state becomes central to most pages; the maintainers are React-only and will not work in Astro templates; authenticated dynamic experiences are wanted inside the same app.

---

## 18. V1 scope

### 18.1 In scope

| Area | V1 |
|---|---|
| **Core** | All modules in §17.1; all entity schemas (Provenance schema only) |
| **Preservation** | Ingest, masters, manifests, fixity, backups, archive export, restore drill, runbook |
| **Pipeline** | Gate, projection, proof sheet, release lock, snapshots, reproducibility |
| **Edition 01** | Released: identity-gated online **and** offline package |
| **Public ceiling** | The build path is implemented and leak-tested with fixtures. An actual public release is gated by the clearance review and content readiness, not by engineering |
| **Renderer** | The page inventory in §17.4, unpolished until content and design are fixed |
| **Languages** | Edition 01: `ja`, `en`, `el` (all required) |
| **Capacity** | Sized for about five representative works, and tested at 1,000 records × 3 languages (T21) |

### 18.2 V1 definition of done

- [ ] Edition 01 released with a complete release lock, and reproduced (T16).
- [ ] Every displayed claim and text passes the gate; every non-`documented` claim is labelled.
- [ ] Masters preserved 3-2-1; restore drill passed (T20).
- [ ] Offline package verified on the target device (T19).
- [ ] Runbook complete; accounts family-owned; recovery keys held by two people.
- [ ] Proof sheet signed by the named approvers.
- [ ] A curator given only the archive folder can produce a catalogue entry for every published work (B8).

---

## 19. Explicit non-goals [P11]

V1 does **not** include:

- A database or Supabase; a CMS; an admin dashboard; custom authentication
- IIIF; Deep Zoom or tiling infrastructure
- WebGL, 3D, or virtual gallery rooms
- An AI archive chatbot, or any AI-generated narrative, translation, caption or transcript published without human review
- A visible archive search or faceted-browsing interface
- Comments, guestbooks or user-contributed content on the site
- E-commerce, ticketing or donations
- Collection management, loans, condition reports or insurance
- Per-edition forks of code or data, or a separate "birthday app"
- Client-side password gates presented as security
- Automatic sync of unreviewed data to any public origin
- Analytics dashboards; third-party trackers in non-public editions

---

## 20. First vertical slice

### 20.1 Purpose and constraints

Prove the architecture end to end **before any real content is ingested at volume**.

- **Fixtures only.** The slice uses `core/fixtures/` with clearly synthetic content and the `FX-` namespace. It consumes no real IDs, creates no real artwork records, and states no artwork title or historical fact.
- Fixture set: one synthetic artwork with claims in every status; one fixture voice of each of the five types; a synthetic image containing embedded GPS metadata; permissions in mixed states; one synthetic edition per ceiling (`public`, `family`).
- **No design work.** The renderer stub proves the contract, nothing more.

### 20.2 Milestones

| M | Deliverable | Exit criterion |
|---|---|---|
| **M0 Foundations** | Private repository, protected `main`, family-owned accounts (domain, repository organisation, storage), storage tiers and backup targets provisioned, roles named, runbook v0 | Access can be recovered by a second person |
| **M1 Schema and registry** | Schemas for all entities; ID registry with mint and tombstone; structural validation; generated data dictionary; fixture archive | T09, T13 partially, S-rules pass |
| **M2 Ingest and preservation** | Fixture ingest: masters, manifests, sidecars, archive derivatives, fixity, first backup and restore drill | T20 (first pass); T06 (master unchanged) |
| **M3 Derivatives** | Derivative profile v0; metadata stripping; deterministic output | T06, T16 (assets) |
| **M4 Gate and dataset** | Eligibility, Core Display Policy, allow-list projection, tokens and excerpts, `routes.json`, dataset schema; negative (leak) tests | T01–T05, T07–T15 |
| **M5 Proof, lock, snapshot** | Proof sheet; release lock; snapshot freeze; reproducibility check | T16 |
| **M6 Renderer stub** | Astro consumes the dataset only: one plate page, Record panel, status labels, language fallback. Job B sandbox | T17, T18 |
| **M7 Access and offline** | Family origin behind identity control (provider chosen here); offline package on the target device; public-ceiling build produced but **not deployed**, diff verified | T19 |
| **M8 Scale test** | 1,000 synthetic records × 3 languages; build time, memory and dataset size recorded; thresholds agreed | T21 |

**Real intake starts after M2**, in parallel with M3–M8, because masters, IDs and preservation are then ready. The long pole is verification and rights, not engineering.

### 20.3 Acceptance tests

| Test | Scenario | Expected |
|---|---|---|
| T01 | `to_verify` claim on an approved record | Absent from the public dataset. In the family dataset only if the edition opts in, and labelled |
| T02 | Public edition sets `opt_in_unverified` | Fails (V-G4) |
| T03 | Record edited after approval | Excluded; run fails until re-approved (V-G1) |
| T04 | Asset without covering Permission | Fails (V-P1) |
| T05 | Identifiable minor without guardian consent | Fails (V-P2) |
| T06 | Image with embedded GPS and personal EXIF | Web derivative contains none; master bytes unchanged (hash) |
| T07 | Required reference to an ineligible record / optional reference | Fails / dropped and logged |
| T08 | `ai_draft` translation; missing English | Fails; fallback shows the original with a marker, no machine translation |
| T09 | Reported speech typed as Artist Voice; type change without re-issue | Both fail; each type's required fields enforced |
| T10 | Receipt, Permission, Provenance, `notes_internal`, `contact` at ceiling `family` | Never present in any dataset |
| T11 | Output scan for master and archive-derivative paths | None found |
| T12 | Fixture record placed in a real edition | Fails (V-G6) |
| T13 | Mint a tombstoned ID; hand-typed ID with wrong prefix or label | Refused / fails |
| T14 | Token pointing at a non-displayable claim; retyped quotation | Fails (V-T3, V-T4) |
| T15 | Canonical path changes for an existing ID between releases | Fails unless a redirect is declared |
| T16 | Two builds from one lock | Byte-identical dataset and asset manifest |
| T17 | Renderer stage tries to read `archive/`; dataset schema conformance | Access denied; renderer builds from dataset alone; only types imported |
| T18 | Every `must_label` claim in the rendered output | Label present (automated check) |
| T19 | Offline package on the target device with the network disabled | Opens fully; no external requests; relative links |
| T20 | Restore from backups alone | Master checksums match; dataset rebuilds identically; archive export readable without the site |
| T21 | 1,000 × 3 languages | Build within the agreed budget; results recorded |

### 20.4 Schedule constraints

- Edition 01 target release is **20 December 2026**.
- **Proposed** (to be confirmed by the project lead, not locked here): content freeze in mid-November; build freeze in the first week of December; on-device rehearsal in the week before release; M0–M5 complete before real content volume peaks.
- Scope of Edition 01 is defined by **what is approved by the content freeze**, not by a feature list. Deadline pressure MUST NOT lower any gate.

---

## 21. Traceability

| Principle | Implemented in |
|---|---|
| P1 | §3, B1–B9; §2.3 I2 |
| P2 | §1; §3; §7; §15 |
| P3 | §7 (Edition, releases, Edition 01); §13 |
| P4 | §8; §10; §11.6 |
| P5 | §3 B3; §4.4 (Artwork); §4.6; V-R6 |
| P6 | §4.5; VR1–VR7; V-V1–V-V4 |
| P7 | §4.5 (Associate Memory, classification test) |
| P8 | §5; §5.3; §15; V-G2–V-G9 |
| P9 | §2.3 I1, I6; §13.2; §17.3; T17 |
| P10 | §11; §16; V-A1–V-A3 |
| P11 | §19 |
| P12 | §17.4; §3 B8 |
| P13 | §17 |
| P14 | §11.6; §15.3; §20 M7 |
| P15 | §7.5; §17.5; §16; T16; T19 |

---

## Appendix A. Confirmations (final)

**Status legend.** **LOCKED**: frozen; changing it requires a formal specification change. **SOFT**: deliberately unlocked; may change without a specification change. **PROPOSED**: a proposal awaiting explicit confirmation.

| # | Item | Decision | Status | Effect |
|---|---|---|---|---|
| A1 | ID format | `PREFIX-NNNNNN`: uppercase prefix, hyphen, six digits. Prefixes as in §4.1. Rules ID1–ID7 (§8) | **LOCKED** | The first real ID may be minted once the registry exists (M1). The format cannot change afterwards |
| A2 | Fifth voice type | **Associate Memory** (`AM`, 知人・関係者の記憶), with the classification test in §4.5 | **LOCKED** | Intake forms may be issued with five types. The type list is closed (VR6) |
| A3 | Visibility levels | `public` · `archive` · `family` · `private`; ordering and ceilings per §15.1. `private` is never a ceiling | **LOCKED** | M1 schema-lock precondition met |
| A4 | Publication model | Edition-based release. No `published` record status. Record workflow: `draft` · `under_review` · `approved` · `withdrawn` (§5.2, §7.3) | **LOCKED** | M1 schema-lock precondition met |
| A5 | Rights and consent | Single **Permission** entity with an immutable `basis` (§6) | **LOCKED** | M1 schema-lock precondition met |
| A6 | Edition 01 languages | **`ja`, `en`, `el`: all required.** Vietnamese (`vi`) is not part of the project | **LOCKED** | Under V-T1/V-T2 every text displayed in Edition 01 must exist in all three languages, each `human_written` or `human_reviewed`. Body amended by substitution only: every `vi` reference is now `el`; the Vietnamese row is removed |
| A7 | Approver roles | Roles as defined in the specification: steward; family approver; Artist Voice approval by the artist or his designated family approver (W5); native Japanese editor (§12); clearance reviewer (§7.2; needed only for a `public` ceiling) | **LOCKED** (roles) · **OPEN** (human names) | The specification contains no human names, by design. Assignments are recorded in `docs/runbook` before the first approval |
| A8 | Hosting and access provider | Not selected. Requirements in §15.3 stand | **SOFT** | Decided at M7 |
| A9 | Derivative profile values | Not fixed. The profile is versioned (§11.3) | **SOFT** | Decided at M3 |
| A10 | Schedule dates | Target release **20 December 2026** is fixed (P3, §7.4). Content freeze mid-November, build freeze first week of December, on-device rehearsal the week before release, and M0–M5 complete before content volume peaks (§20.4) | **PROPOSED** | Unlocked until confirmed by the project lead |
