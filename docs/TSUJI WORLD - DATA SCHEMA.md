# TSUJI WORLD — DATA SCHEMA
## Version 1.0

**Status:** Implementation Contract  
**Project:** TSUJI WORLD  
**Parent Documents:**
- `TSUJI_WORLD_V1_Technical_Architecture_Specification.md`
- `TSUJI_WORLD_IMPLEMENTATION_CONTRACT.md`

---

# 1. Purpose

This document defines the canonical data model for TSUJI WORLD.

It specifies:

- core entities
- entity identifiers
- relationships
- lifecycle states
- provenance requirements
- visibility rules
- publication states
- edition and release relationships
- asset relationships
- multilingual representation
- permission relationships

This document does **not** define:

- historical facts
- artwork content
- exhibition narratives
- visual design
- page layout
- CSS
- typography
- final editorial wording
- undocumented biographical claims

Those belong to the appropriate source, editorial, design, or content layers.

---

# 2. Schema Principles

## 2.1 Stable Identity

Every persistent entity MUST have a stable machine-readable ID.

IDs MUST NOT depend on:

- display names
- translated names
- URLs
- filenames
- page titles

Changing a display name MUST NOT change the entity ID.

Example:

```text
person_001
artwork_001
exhibition_001
source_001
asset_001
edition_001
release_001
________________________________________
3. Entity Layers
TSUJI WORLD uses the following conceptual layers:
SOURCE
  │
  ▼
ARCHIVE
  │
  ▼
KNOWLEDGE / ENTITY
  │
  ▼
CURATION
  │
  ▼
EDITION
  │
  ▼
RELEASE
  │
  ▼
PUBLIC EXPERIENCE
The public website MUST NOT become the canonical source of historical data.
The renderer consumes approved publication data.
________________________________________
4. Core Entities
The canonical entity set is:
Person
Artwork
Exhibition
Event
Theme
Source
Asset
Permission
Provenance
Edition
Release
Voice
Additional entities MAY be introduced only when required by the architecture.
A new entity MUST NOT be introduced merely to simplify UI implementation.
________________________________________
5. Person
Represents a historical or contemporary person referenced by TSUJI WORLD.
Person:
  id: string
  canonical_name: string
  alternate_names: []
  name_localized: {}
  birth:
    date: optional
    place: optional
  death:
    date: optional
    place: optional
  description: optional
  status: enum
  visibility: enum
  provenance: []
  permissions: []
Required
•	id
•	canonical_name
•	status
•	visibility
•	provenance reference
Rules
A Person record MUST NOT contain unsupported historical claims.
A person's display name MAY be localized.
The ID remains language-neutral.
________________________________________
6. Artwork
Represents an artwork or other curated creative work.
Artwork:
  id: string
  title:
    original: string
    localized: {}
  creator_ids: []
  date:
    start: optional
    end: optional
    display: optional
  medium: optional
  dimensions: optional
  description:
    original: optional
    localized: {}
  source_ids: []
  asset_ids: []
  provenance_ids: []
  permission_ids: []
  status: enum
  visibility: enum
Required
•	id
•	title
•	creator relationship
•	status
•	visibility
•	provenance
•	source reference
Rules
Artwork metadata MUST be traceable to a source or approved editorial record.
An image asset MUST NOT automatically imply that the artwork itself is approved for publication.
Artwork permission and image permission are separate concerns.
________________________________________
7. Exhibition
Represents an exhibition, presentation, or curated grouping.
Exhibition:
  id: string
  title:
    original: string
    localized: {}
  description:
    original: optional
    localized: {}
  artwork_ids: []
  person_ids: []
  theme_ids: []
  source_ids: []
  asset_ids: []
  provenance_ids: []
  permission_ids: []
  status: enum
  visibility: enum
An Exhibition MAY contain:
•	artworks
•	people
•	themes
•	supporting assets
•	source references
The exhibition record MUST NOT duplicate canonical artwork metadata unnecessarily.
________________________________________
8. Event
Represents a dated event relevant to the project.
Event:
  id: string
  title:
    original: string
    localized: {}
  date:
    start: optional
    end: optional
  place: optional
  description:
    original: optional
    localized: {}
  person_ids: []
  artwork_ids: []
  exhibition_ids: []
  source_ids: []
  provenance_ids: []
  status: enum
  visibility: enum
Dates MUST preserve uncertainty where the source is uncertain.
The schema MUST NOT force an exact date when the source provides only an approximate date.
________________________________________
9. Theme
Represents a curated conceptual grouping.
Theme:
  id: string
  name:
    original: string
    localized: {}
  description:
    original: optional
    localized: {}
  related_entity_ids: []
  source_ids: []
  provenance_ids: []
  status: enum
  visibility: enum
Themes are editorial structures.
They MUST NOT be treated as historical facts unless supported by sources.
________________________________________
10. Source
Represents the origin of information.
Source:
  id: string
  type: enum
  title: string
  author: optional
  publisher: optional
  date: optional
  url: optional
  archive_location: optional
  citation: optional
  language: optional
  reliability_status: enum
  access_status: enum
  notes: optional
Source Types
The implementation SHOULD support at least:
book
catalogue
museum_record
archive_record
academic_publication
newspaper
interview
letter
photograph
official_website
private_archive
oral_history
other
The implementation MUST allow additional source types without breaking existing records.
________________________________________
11. Provenance
Provenance explains where a data statement came from and how it entered the system.
Provenance:
  id: string
  entity_id: string
  source_id: string
  statement: string
  excerpt: optional
  location: optional
  captured_at: optional
  verified_by: optional
  verification_status: enum
  notes: optional
Verification Status
unverified
under_review
verified
disputed
rejected
disputed MUST remain a valid state.
The system MUST NOT silently convert disputed information into verified information.
________________________________________
12. Asset
Represents a digital file associated with an entity.
Asset:
  id: string
  type: enum
  master_path: optional
  derivative_paths: {}
  mime_type: string
  checksum:
    algorithm: string
    value: string
  dimensions:
    width: optional
    height: optional
  file_size: optional
  source_id: optional
  permission_id: optional
  visibility: enum
  status: enum
Asset Types
image
audio
video
document
scan
thumbnail
illustration
map
other
Asset Rules
The master asset MUST NOT be exposed directly through the public web root unless explicitly approved.
Public derivatives MUST be traceable to the master asset.
Checksum MUST be generated for preservation-critical assets.
________________________________________
13. Permission
Permission controls whether an entity or asset may be used.
Permission:
  id: string
  subject_type: enum
  subject_id: string
  rights_holder: optional
  permission_type: enum
  scope: enum
  territory: optional
  start_date: optional
  end_date: optional
  evidence_source_id: optional
  status: enum
  notes: optional
Permission Types
copyright
image_right
publication
privacy
guardian_consent
trademark
archive_permission
other
Permission Scope
private
family
restricted
public
offline_only
edition_specific
Permission is not equivalent to visibility.
A record MAY be historically relevant but not publishable.
________________________________________
14. Visibility
Visibility is a publication/access classification.
Canonical values:
private
family
restricted
public
Default value:
private
The system MUST follow:
Default deny.
A record MUST NOT become public merely because it exists in the database.
________________________________________
15. Publication Status
Every publishable entity MUST have an explicit lifecycle state.
Canonical states:
draft
review
approved
published
archived
withdrawn
Optional content-review states MAY include:
unverified
disputed
These are verification states, not substitutes for publication status.
________________________________________
16. Entity Status Rules
An entity can only be published when:
status = approved
AND
visibility = public
AND
required provenance exists
AND
required permissions exist
AND
publication gate passes
The implementation MUST NOT infer approval from:
•	presence of a source
•	presence of an image
•	completion of translation
•	inclusion in an exhibition
•	successful build
________________________________________
17. Edition
An Edition represents a defined publication scope.
Edition:
  id: string
  edition_number: string
  title: string
  description: optional
  entity_ids: []
  asset_ids: []
  language_set: []
  visibility: enum
  status: enum
  created_at: string
  approved_at: optional
  release_id: optional
An Edition is a curated publication boundary.
It MUST NOT be treated as the master database.
________________________________________
18. Release
A Release represents an immutable published state of an Edition.
Release:
  id: string
  edition_id: string
  version: string
  content_hash: string
  asset_manifest_hash: optional
  schema_version: string
  build_version: string
  created_at: string
  approved_at: optional
  released_at: optional
  status: enum
Once released, the Release MUST be immutable.
A correction requires a new Release.
________________________________________
19. Release States
draft
proof
approved
released
superseded
withdrawn
A released edition MUST retain its historical release record.
The system MUST NOT overwrite a previous release.
________________________________________
20. Voice
Voice represents an approved narrative mode.
Voice:
  id: string
  type: enum
  description: optional
  language: string
  status: enum
The implementation MUST support the project-defined voice types.
Voice is presentation metadata.
Voice MUST NOT alter factual provenance.
________________________________________
21. Multilingual Data
Entity IDs are language-neutral.
Localized values use language keys.
Example:
title:
  ja: "..."
  en: "..."
  vi: "..."
The canonical/original language MUST remain identifiable.
Translations MUST NOT replace the original value.
________________________________________
22. Translation Rules
Each translation SHOULD carry:
translation:
  language: string
  value: string
  source_language: string
  status: enum
Recommended states:
draft
review
approved
published
AI-generated translations MUST NOT automatically enter published.
________________________________________
23. Relationships
Relationships MUST use stable entity IDs.
Example:
creator_ids:
  - person_001

source_ids:
  - source_014

asset_ids:
  - asset_032

permission_ids:
  - permission_009
Do not duplicate complete entity objects merely to simplify rendering.
________________________________________
24. Relationship Integrity
The implementation MUST validate:
•	referenced IDs exist
•	no broken references
•	no circular dependency where prohibited
•	source references resolve
•	asset references resolve
•	permission references resolve
•	edition references resolve
•	release references resolve
A build with unresolved required references MUST fail.
________________________________________
25. Publication Gate
The publication layer MUST evaluate every record before release.
Conceptually:
ENTITY
  ↓
PROVENANCE CHECK
  ↓
PERMISSION CHECK
  ↓
VISIBILITY CHECK
  ↓
STATUS CHECK
  ↓
EDITION CHECK
  ↓
PUBLICATION APPROVED
The gate MUST be deterministic.
The same input dataset MUST produce the same gate result.
________________________________________
26. Publication Gate Result
Each checked item SHOULD produce:
GateResult:
  entity_id: string
  passed: boolean
  checks:
    provenance: boolean
    permission: boolean
    visibility: boolean
    status: boolean
    references: boolean
  errors: []
  warnings: []
Errors MUST block publication.
Warnings MAY be allowed only when explicitly classified as non-blocking.
________________________________________
27. Quotes and Excerpts
Quoted material MUST remain attributable.
A quote SHOULD contain:
Quote:
  id: string
  source_id: string
  text: string
  language: string
  location: optional
  permission_id: optional
  status: enum
A generated narrative MUST NOT create a quotation that does not exist in an approved source.
________________________________________
28. Source-to-Statement Traceability
For factual statements displayed publicly:
PUBLIC STATEMENT
      ↓
PROVENANCE
      ↓
SOURCE
The relationship MUST remain recoverable.
This enables later audit and correction.
________________________________________
29. Archive / Experience Separation
The canonical archive and the public experience MUST remain separate.
ARCHIVE DATA
     │
     ▼
APPROVED PROJECTION
     │
     ▼
PUBLIC EXPERIENCE
The renderer SHOULD consume a publication projection rather than querying raw archive data.
This prevents accidental publication of:
•	private records
•	rejected records
•	unverified records
•	restricted assets
•	internal notes
________________________________________
30. Publication Projection
A projection is a release-ready representation.
Example:
PublicationItem:
  entity_id: string
  entity_type: string
  title: {}
  description: {}
  asset_refs: []
  related_refs: []
  provenance_refs: []
  visibility: public
  status: published
Projection data MUST contain only information approved for that release.
________________________________________
31. Edition Snapshot
Before release, the system MUST create a snapshot containing:
schema version
edition ID
entity IDs
publication projection
asset manifest
content hashes
permission state
build version
timestamp
The snapshot becomes the basis for reproducible release.
________________________________________
32. Hashing
Hashing SHOULD be used for:
•	source files where appropriate
•	preservation-critical assets
•	publication datasets
•	release manifests
•	final release packages
The hash algorithm MUST be explicitly recorded.
Recommended default:
SHA-256
The implementation MUST NOT silently change the hash algorithm for existing release records.
________________________________________
33. Asset Derivatives
An asset MAY have multiple derivatives.
Example:
derivative_paths:
  web: "..."
  thumbnail: "..."
  offline: "..."
Each derivative MUST retain a relationship to its master asset.
The derivative pipeline MUST be reproducible.
________________________________________
34. Private and Public Data
Private data MUST be excluded from public projections.
The following are examples of potentially private data:
private contact information
private family notes
internal editorial comments
unreleased assets
rights documentation
private addresses
internal source notes
The public build MUST NOT rely on client-side hiding as a security mechanism.
________________________________________
35. Family / Restricted Publication
Restricted publication MUST be represented by explicit access classification.
It MUST NOT rely solely on:
hidden URL
robots.txt
noindex
unlinked page
obscure filename
These are not access controls.
________________________________________
36. Offline Package
An Edition MAY have an offline package.
The package SHOULD contain:
publication projection
approved assets
asset manifest
release metadata
schema version
checksums
Offline packages MUST NOT depend on external network requests for core content.
________________________________________
37. Fixture Data
Development fixtures MUST be clearly separated from real historical data.
Example:
fixtures/
  synthetic/
  validation/
  examples/
Synthetic fixture records MUST NOT be presented as real historical records.
Fixture IDs SHOULD use a recognizable namespace.
Example:
fixture_person_001
fixture_artwork_001
________________________________________
38. Data Validation
Schema validation MUST check:
Identity
•	unique IDs
•	valid ID format
References
•	all referenced IDs exist
Required fields
•	mandatory fields present
State
•	valid lifecycle state
Visibility
•	valid visibility value
Provenance
•	required provenance exists
Permission
•	required permission exists
Publication
•	publication gate passes
Localization
•	language structure is valid
________________________________________
39. Deterministic Build Requirement
Given:
same schema version
+
same source dataset
+
same approved projection
+
same asset set
+
same build configuration
the generated publication SHOULD be reproducible.
The release process MUST record the information necessary to reproduce the release.
________________________________________
40. Schema Versioning
Schema versions MUST be explicit.
Example:
schema_version: 1.0
Changes MUST be classified as:
PATCH
MINOR
MAJOR
PATCH
Non-breaking clarification or validation improvement.
MINOR
Backward-compatible addition.
MAJOR
Breaking structural change.
A released Edition MUST retain the schema version used to create it.
________________________________________
41. Migration
Schema changes MUST NOT silently rewrite historical releases.
Migration MUST be explicit.
Example:
v1.0
 ↓
migration_1.0_to_1.1
 ↓
v1.1
Migration scripts MUST be versioned with the repository.
________________________________________
42. Delete Policy
Published historical records SHOULD NOT be physically deleted merely because they are no longer preferred.
Use lifecycle states such as:
archived
withdrawn
superseded
Physical deletion is permitted only when required by:
•	legal obligation
•	rights requirement
•	privacy requirement
•	explicit preservation policy
________________________________________
43. Correction Policy
Corrections MUST preserve traceability.
Do not overwrite historical release data.
Instead:
Release 001
    ↓
Correction
    ↓
Release 002
The new record MUST preserve the relationship to the previous state where appropriate.
________________________________________
44. Canonical Ownership
The following ownership boundaries MUST remain clear:
Information	Canonical owner
Historical source	Source
Evidence	Provenance
Person identity	Person
Artwork identity	Artwork
Digital file	Asset
Rights	Permission
Publication grouping	Edition
Immutable publication	Release
Narrative mode	Voice
Public projection	Publication layer
No UI component becomes the canonical owner of historical data.
________________________________________
45. Forbidden Schema Shortcuts
The implementation MUST NOT:
1.	store important historical facts only inside page components
2.	use filenames as entity IDs
3.	use URLs as entity IDs
4.	use display names as primary keys
5.	publish directly from raw archive data
6.	treat image existence as publication permission
7.	treat source existence as verification
8.	treat translation completion as factual approval
9.	overwrite released editions
10.	silently discard disputed information
11.	expose private fields and hide them only with CSS
12.	create fake historical records for UI convenience
________________________________________
46. Minimum Required Entity Graph
A publishable artwork should be capable of resolving at least:
Artwork
 ├── Person
 ├── Source
 ├── Provenance
 ├── Asset
 ├── Permission
 └── Edition
       └── Release
The exact relationships MAY vary by record type.
________________________________________
47. Implementation Boundary
This schema defines data contracts.
It does not dictate:
•	React/Astro component design
•	CSS architecture
•	animation implementation
•	image composition
•	navigation design
•	typography
•	visual effects
•	hosting provider
•	CDN configuration
Those belong to implementation and experience specifications.
________________________________________
48. Agent Rules
Any AI coding agent working on TSUJI WORLD MUST:
1.	Read this schema before modifying data models.
2.	Preserve stable IDs.
3.	Validate references.
4.	Respect visibility and permission states.
5.	Never invent historical data.
6.	Never silently change schema semantics.
7.	Flag breaking changes.
8.	Update validation/tests when schema changes.
9.	Preserve release immutability.
10.	Report any conflict with the Architecture Specification or Implementation Contract.
The agent MUST NOT redesign the data model simply because an implementation appears easier with a different structure.
________________________________________
49. Schema Change Protocol
Before changing this schema, the agent MUST provide:
1. Reason for change
2. Affected entities
3. Breaking/non-breaking classification
4. Migration requirement
5. Test impact
6. Release impact
No breaking schema change may be introduced silently.
________________________________________
50. Definition of Schema Complete
The schema implementation is considered complete when:
•	all canonical entities are represented
•	stable IDs are enforced
•	references are validated
•	provenance is traceable
•	permissions are explicit
•	visibility is explicit
•	publication states are explicit
•	editions are separated from archive data
•	releases are immutable
•	multilingual structures are supported
•	asset relationships are validated
•	schema versioning is implemented
•	migration strategy exists
•	synthetic fixtures are separated from real data
•	publication projection can be generated deterministically
________________________________________
51. Final Rule
The schema is a contract, not a suggestion.
The public experience may evolve.
The visual design may evolve.
The implementation may evolve.
The data contract may evolve only through an explicit versioned change.
Every published item must remain:
IDENTIFIABLE
TRACEABLE
VERIFIABLE
PERMISSION-AWARE
VERSIONED
REPRODUCIBLE
________________________________________
END OF TSUJI_WORLD_SCHEMA.md
