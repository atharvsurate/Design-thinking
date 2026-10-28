# SIH26190 — Secure Digital Document Management System
## For Legal and Investigation Documents
### Architectural Blueprint & Technical Specification

---

> **Problem Statement ID:** SIH26190
> **Organization:** Ministry of Home Affairs (MHA), Government of India
> **Category:** Software | **Theme:** Miscellaneous
> **Hackathon:** Smart India Hackathon 2026
> **Submission Deadline:** 30 September 2026

---

> [!IMPORTANT]
> This document is the **authoritative specification for AI-assisted implementation**.
> Every design decision is final unless explicitly overridden by the team lead.
> Gemini must implement phases sequentially — **Phase N+1 never starts before Phase N verification passes.**

---

## Problem Context (MHA-Specific)

The Ministry of Home Affairs manages the most sensitive class of government documents in India — FIR records, charge sheets, witness statements, forensic reports, inter-agency intelligence memos, court submissions, and cross-border investigation dossiers. These documents are today managed through a patchwork of physical files, email attachments, and siloed departmental systems — creating risks of tampering, unauthorized disclosure, chain-of-custody breaks, and inadmissibility in court.

**SIH26190 demands a solution that solves four hard problems simultaneously:**

1. **Legal Admissibility** — Every document's integrity must be cryptographically provable in an Indian court of law under the Indian Evidence Act, 1872 (as amended by BSA 2023).
2. **Operational Security** — Documents must be accessible to the right officer at the right time with zero exposure to unauthorized parties, including IT staff.
3. **Compliance** — The system must comply with India's Digital Personal Data Protection (DPDP) Act 2023, the IT Act 2000/2008, and MHA data classification norms.
4. **Deployability** — Must run on **NIC MeghRaj Government Cloud** (on-premise compatible), not dependent on foreign cloud infrastructure.

---

## Section 1 — System Architecture & Tech Stack Selection

### 1.1 Recommended Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | Next.js 14 (App Router) + TypeScript | SSR minimizes client-side attack surface; strong type safety on sensitive data structures |
| **UI / i18n** | shadcn/ui + Tailwind CSS + `next-intl` | Accessible components; **Hindi + English bilingual UI** via `next-intl` |
| **API Layer** | FastAPI (Python 3.12) | Async-native, strict Pydantic validation, auto-generates OpenAPI docs |
| **Auth (Primary)** | Keycloak 24 — federated to **NIC Active Directory via LDAP** | Government officers log in with their existing NIC/departmental credentials; enforces MFA |
| **Auth (Fallback)** | Local Keycloak accounts + TOTP | For non-NIC-AD users (external experts, auditors) |
| **Primary DB** | PostgreSQL 16 + `pgaudit` + `pgcrypto` | ACID, Row-Level Security, column-level encryption, FTS |
| **Search** | OpenSearch 2.x (self-hosted) | Full-text search on extracted content; field-level ACL; entirely on-premise |
| **Object Storage** | MinIO (S3-compatible, self-hosted) **on NIC infrastructure** | WORM object locking, versioning, per-object encryption — no foreign dependency |
| **Secrets / KMS** | HashiCorp Vault OSS (self-hosted) | Transit encryption, dynamic DB credentials, PKI CA — runs on NIC infra |
| **Task Queue** | Celery + Redis | Async background processing: AV scan, OCR, PII detection, encryption |
| **File Processing** | Apache Tika (self-hosted) + ClamAV | Content extraction from 1000+ formats; mandatory AV scan before indexing |
| **PDF Engine** | LibreOffice headless + Gotenberg | Server-side PDF conversion and watermark stamping; no external SaaS |
| **Infrastructure** | Docker Compose (dev/demo) → Kubernetes + Helm (production NIC) | Reproducible; NIC-compatible container deployment |
| **Reverse Proxy** | Nginx + ModSecurity (OWASP CRS) | WAF, rate limiting, TLS termination |
| **Observability** | Prometheus + Grafana + OpenTelemetry → Loki | Metrics, logs, traces — all on-premise, shippable to NIC SOC |
| **OCR** | Tesseract OCR (Hindi + English trained models) | Extracts searchable text from scanned FIR/court documents in both scripts |

---

### 1.2 High-Level System Data Flow — Document Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                   OFFICER'S BROWSER (GOI Network)               │
└─────────────────────┬───────────────────────────────────────────┘
                      │  HTTPS / TLS 1.3 (GOI PKI Certificate)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Nginx WAF (ModSecurity + OWASP CRS)                │
│         Rate Limiter │ IP Allowlist │ Header Injection          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
  [Next.js Frontend]        [Keycloak IdP]
  (Bilingual UI)         (NIC-AD LDAP federation)
          │                        │
          │   JWT (15-min TTL)     │
          └───────────┬────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│                                                                 │
│  ① INPUT VALIDATION (Pydantic strict)                          │
│     └─ Reject: wrong MIME, oversized, malformed metadata       │
│                                                                 │
│  ② AUTHORIZATION (RBAC + PostgreSQL RLS)                       │
│     └─ Deny if role lacks permission; log DENIED event         │
│                                                                 │
│  ③ VIRUS SCAN (ClamAV — mandatory gate, async Celery)          │
│     └─ Infected → QUARANTINE bucket + alert SOC               │
│                                                                 │
│  ④ CONTENT EXTRACTION (Apache Tika + Tesseract OCR)            │
│     └─ Text extracted in Hindi/English; macros stripped        │
│                                                                 │
│  ⑤ PII DETECTION (spaCy + custom NER for Indian PII)           │
│     └─ Tag: Aadhaar, PAN, Mobile, Address, Name               │
│                                                                 │
│  ⑥ ENCRYPTION (AES-256-GCM envelope via Vault Transit)         │
│     └─ Unique DEK per document; DEK wrapped by case KEK        │
│                                                                 │
│  ⑦ SECURE STORAGE (MinIO — NIC infra, WORM for evidence)       │
│     └─ Encrypted blob stored; WORM lock if evidence=TRUE       │
│                                                                 │
│  ⑧ DATABASE RECORD (PostgreSQL)                                │
│     └─ Document row inserted; dual hash manifest signed        │
│                                                                 │
│  ⑨ SEARCH INDEXING (OpenSearch — async Celery)                 │
│     └─ Extracted text + metadata indexed; ACL embedded         │
│                                                                 │
│  ⑩ AUDIT LOG (append-only, hash-chained, Ed25519-signed)       │
│     └─ DOC_UPLOAD event logged with full context               │
└─────────────────────────────────────────────────────────────────┘
```

---

### 1.3 Deployment Topology (NIC MeghRaj Production)

```
GOI Network / NIC MPLS
       │
  [GOI PKI TLS]
       │
  [Nginx WAF Cluster]
       │
  ┌────┴────────────────────────────────────────────┐
  │                 Kubernetes (NIC Cloud)           │
  │                                                  │
  │  [Next.js Pods x2]   [FastAPI Pods x3]          │
  │  [Keycloak Pods x2]  [Celery Worker Pods x3]    │
  │                                                  │
  │  ── Persistent Storage (NIC-provisioned PVCs) ─  │
  │  [PostgreSQL Primary + Replica (Patroni)]        │
  │  [OpenSearch 3-node cluster]                     │
  │  [MinIO Erasure-coded 4+2 cluster]               │
  │  [Redis Sentinel Cluster]                        │
  │  [HashiCorp Vault HA (3 nodes)]                  │
  │  [ClamAV Service]  [Tika Server]                 │
  └──────────────────────────────────────────────────┘
       │
  [NIC SOC SIEM Integration]  [NIC-AD LDAP]
```

---

## Section 2 — Security, Compliance & Chain of Custody

### 2.1 Encryption Standards

#### 2.1.1 Encryption at Rest — Three-Layer Envelope Model

```
DOCUMENT PLAINTEXT
        │
        ▼
  AES-256-GCM  ◄──  Per-Document Data Encryption Key (DEK)
        │                       │
        ▼                       │ encrypted by
  [Encrypted Blob]        Case-Level Key Encryption Key (KEK)
  stored in MinIO                │
                           stored in Vault Transit
                                 │
                           Vault Master Key
                      (Shamir 5-key / 3-key quorum
                       — physically distributed across
                       MHA, NIC, and a designated officer)
```

- **Algorithm**: AES-256-GCM (provides authenticated encryption — any tampering invalidates the auth tag)
- **IV**: 96-bit random IV per encryption operation; stored alongside encrypted DEK in the `documents` table
- **DEK Uniqueness**: Every document gets a **unique DEK** — never reused across documents or versions
- **Key Rotation**: Case KEKs rotated every 90 days; Vault re-wraps all DEKs without decrypting the blobs
- **Database Column Encryption**: PII columns (names, Aadhaar, mobile) encrypted at column level using `pgcrypto` with a separate column-level key managed by Vault

#### 2.1.2 Encryption in Transit

| Connection | Standard |
|---|---|
| Browser ↔ Nginx | TLS 1.3 with GOI PKI-issued certificates (NIC CA) |
| Nginx ↔ FastAPI | TLS 1.2+ (internal) |
| FastAPI ↔ PostgreSQL | mTLS (client cert from Vault PKI, 72-hour TTL) |
| FastAPI ↔ MinIO | mTLS |
| FastAPI ↔ Vault | mTLS |
| FastAPI ↔ OpenSearch | TLS 1.2+ with transport security plugin |
| FastAPI ↔ Redis | TLS + auth token |
| All internal pods | Kubernetes NetworkPolicy — deny-all default, allow-listed services only |

#### 2.1.3 Document Integrity — Dual-Hash Manifest

Every stored document receives a cryptographically signed manifest at ingest:

```json
{
  "document_id": "uuid-v7",
  "sha256":      "e3b0c44298fc1c149afb...",
  "blake3":      "af1349b9f5f9a1a6a0954...",
  "size_bytes":  204800,
  "ingested_at": "2026-09-16T09:00:00Z",
  "ingested_by": "officer-uuid",
  "storage_path": "minio://case-{id}/docs/{doc-id}.enc",
  "manifest_sig": "<Ed25519 signature by backend signing key>"
}
```

- Manifest stored in PostgreSQL; also appended to the audit ledger
- On every download, hashes are recomputed and verified — mismatch triggers `INTEGRITY_VIOLATION_ALERT`

---

### 2.2 Immutable Audit Logging — Legal Admissibility Design

> The audit log is **primary legal evidence**. It must satisfy the Bharatiya Sakshya Adhiniyam (BSA) 2023 §65B requirements for electronic records to be admissible in Indian courts.

#### 2.2.1 Hash-Chaining (Blockchain-style)

```
Entry 1                Entry 2                 Entry 3
┌──────────────┐       ┌───────────────────┐   ┌──────────────────┐
│ prev_hash:   │       │ prev_hash:        │   │ prev_hash:       │
│ 0000...0000  │──────►│ SHA256(Entry 1)   │──►│ SHA256(Entry 2)  │
│ entry_hash:  │       │ entry_hash:       │   │ entry_hash:      │
│ SHA256(self) │       │ SHA256(self)      │   │ SHA256(self)     │
│ entry_sig:   │       │ entry_sig:        │   │ entry_sig:       │
│ Ed25519(...) │       │ Ed25519(...)      │   │ Ed25519(...)     │
└──────────────┘       └───────────────────┘   └──────────────────┘
```

Any insertion, deletion, or modification of any entry breaks the chain. The `GET /admin/audit/verify` endpoint recomputes the entire chain and flags the first broken link.

#### 2.2.2 Full Audit Event Catalogue

| Category | Events Logged |
|---|---|
| **Authentication** | LOGIN_SUCCESS, LOGIN_FAIL, MFA_CHALLENGE, MFA_SUCCESS, MFA_FAIL, SESSION_EXPIRED, LOGOUT, TOKEN_REFRESH, ACCOUNT_LOCKED |
| **Document Lifecycle** | DOC_UPLOAD, DOC_VIEW, DOC_DOWNLOAD, DOC_PRINT, DOC_METADATA_EDIT, DOC_VERSION_CREATE, DOC_SHARE_LINK, DOC_EXPORT_PDF, DOC_SOFT_DELETE, DOC_HARD_DELETE, DOC_RESTORE, DOC_WORM_LOCK |
| **Evidence Handling** | EVIDENCE_FLAGGED, EVIDENCE_CHAIN_EXPORT, EVIDENCE_INTEGRITY_VERIFIED, EVIDENCE_INTEGRITY_FAIL |
| **Case Management** | CASE_CREATE, CASE_CLOSE, CASE_ARCHIVE, CASE_LEGAL_HOLD_APPLY, CASE_LEGAL_HOLD_RELEASE, CASE_PERMISSION_GRANT, CASE_PERMISSION_REVOKE |
| **Search** | SEARCH_QUERY (query string logged), SEARCH_RESULT_CLICKED |
| **Privilege** | DOC_PRIVILEGE_SET, DOC_PRIVILEGE_REMOVE, PRIVILEGE_OVERRIDE_REQUESTED, PRIVILEGE_OVERRIDE_APPROVED, PRIVILEGE_OVERRIDE_DENIED |
| **Admin / Security** | USER_CREATE, USER_DISABLE, USER_ENABLE, ROLE_ASSIGN, KEY_ROTATION, BACKUP_CREATE, BACKUP_RESTORE, CONFIG_CHANGE, RATE_LIMIT_HIT, FORBIDDEN_ACCESS, INTEGRITY_VIOLATION_ALERT, AV_SCAN_QUARANTINE |

#### 2.2.3 Audit Log Retention

| Tier | Storage | Retention |
|---|---|---|
| **Hot** | PostgreSQL partitioned table (monthly) | Last 2 years, fully queryable |
| **Warm** | Compressed JSONL → MinIO WORM bucket | Years 3–7 |
| **Cold** | GPG-signed archives → NIC tape/cold storage | 7–15 years (MHA record retention norms) |

#### 2.2.4 §65B BSA Certificate Generation

The system automatically generates a **§65B-compliant electronic record certificate** for any audit log export requested for court proceedings. The certificate includes:

- System identification (hostname, version, signing key fingerprint)
- Hash of the exported log segment
- Ed25519 signature by the system's long-lived signing key
- Timestamp from an NIC-approved RFC 3161 Timestamp Authority

---

### 2.3 Indian Compliance Framework

#### 2.3.1 Digital Personal Data Protection (DPDP) Act 2023

| Requirement | Implementation |
|---|---|
| **Data Minimization** | PII fields collected only when operationally required; NER scanner flags unnecessary PII |
| **Purpose Limitation** | Each case defines its `data_purpose` — documents can only be used for that purpose |
| **Data Principal Rights** | `legal_hold` flag blocks erasure; DPDP erasure requests logged and queued for legal review |
| **Security Safeguards** | AES-256-GCM encryption, mTLS, RBAC, audit log — satisfies §8(4) safeguards obligation |
| **Breach Notification** | INTEGRITY_VIOLATION_ALERT auto-generates a breach report template within 72 hours |
| **Data Fiduciary** | MHA designated as Data Fiduciary; system identifies them in all §65B certificates |
| **Cross-Border Transfer** | All data stays within NIC infra; no cross-border transfer by design |

#### 2.3.2 IT Act 2000 / IT (Amendment) Act 2008

| Section | Mechanism |
|---|---|
| §43A — Reasonable Security | AES-256, mTLS, Vault KMS, WAF, audit log — constitutes "reasonable security practice" |
| §72 — Breach of Confidentiality | RBAC + RLS + audit log provides accountability trail for §72 prosecution |
| §69 — Interception Orders | System provides `legal_hold` flag and court-ordered access audit trail |
| §85B — Digital Signature | Ed25519 audit log signatures admissible as electronic signatures under the Act |

#### 2.3.3 MHA Data Classification Norms

| Classification | Handling |
|---|---|
| **Top Secret** | Restricted to Lead IO + MHA nominee; offline export requires dual-approval |
| **Secret** | LEAD_IO + INVESTIGATOR access; all downloads watermarked |
| **Confidential** | Standard case-team access; PARALEGAL can view, not download |
| **Restricted** | Case-team + EXT_EXPERT; download limited to LEAD_IO |
| **Unclassified** | Default; full case-team access |

#### 2.3.4 Evidence Handling — MHA/CBI Protocol Alignment

- **Seizure Record**: Every evidence document upload requires: Seizure Date, Seizure Location, Seizing Officer ID, FIR/Case reference — mandatory fields enforced by schema
- **WORM Lock**: Applied immediately on `is_evidence = TRUE` — no application code path can unlock without Vault + MinIO quorum console access
- **Chain of Custody Certificate**: PDF listing every access, exportable by Investigating Officer — signed by system key + RFC 3161 timestamp
- **Hash Verification at Collection**: Officer provides expected SHA-256 at upload; system verifies before accepting evidence

---

## Section 3 — Role-Based Access Control (RBAC) Matrix

### 3.1 Role Definitions (MHA Context)

| Role ID | Name | Real-World MHA Equivalent |
|---|---|---|
| `SYSADMIN` | System Administrator | NIC/MHA IT cell — platform ops only, zero case content access |
| `LEAD_IO` | Lead Investigating Officer | SHO / CBI IO / IB Officer leading the investigation |
| `INVESTIGATOR` | Investigating Officer | Field officer collecting and analysing evidence |
| `PARALEGAL` | Case Support Officer | Ministerial staff — tagging, indexing, OCR correction |
| `EXT_EXPERT` | External Expert / Court Auditor | Forensic expert, court-appointed auditor, defence advocate (scoped) |

> [!NOTE]
> The original "Lead Attorney" role is renamed to `LEAD_IO` (Lead Investigating Officer) to reflect MHA's investigation-centric context. Legal counsel within MHA acts under the LEAD_IO designation.

### 3.2 Permission Matrix

> Legend: ✅ Allowed | ❌ Denied | ⚠️ Dual-Approval Required | 🔍 Metadata Only (no content)

#### Platform & Case Administration

| Permission | SYSADMIN | LEAD_IO | INVESTIGATOR | PARALEGAL | EXT_EXPERT |
|:---|:---:|:---:|:---:|:---:|:---:|
| Create / disable user accounts | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign global platform roles | ✅ | ❌ | ❌ | ❌ | ❌ |
| View system-wide audit logs | ✅ | ❌ | ❌ | ❌ | ❌ |
| Trigger audit chain verification | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage encryption keys (Vault) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Create new case | ✅ | ✅ | ❌ | ❌ | ❌ |
| Close / archive case | ✅ | ✅ | ❌ | ❌ | ❌ |
| Apply legal hold on case | ✅ | ⚠️ | ❌ | ❌ | ❌ |
| Release legal hold | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Grant case access to user | ✅ | ✅ | ❌ | ❌ | ❌ |
| Revoke case access | ✅ | ✅ | ❌ | ❌ | ❌ |
| View case member list | 🔍 | ✅ | ✅ | ✅ | ❌ |

#### Document Operations (within assigned case)

| Permission | SYSADMIN | LEAD_IO | INVESTIGATOR | PARALEGAL | EXT_EXPERT |
|:---|:---:|:---:|:---:|:---:|:---:|
| Upload document | ❌† | ✅ | ✅ | ✅ | ❌ |
| View document (browser) | ❌† | ✅ | ✅ | ✅ | ✅‡ |
| Download original file | ❌† | ✅ | ✅ | ⚠️ | ❌ |
| Print / export to PDF | ❌† | ✅ | ✅ | ⚠️ | ❌ |
| Bulk export (ZIP) | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| Edit document metadata | ❌ | ✅ | ✅ | ✅ | ❌ |
| Add annotations | ❌ | ✅ | ✅ | ✅ | ✅‡ |
| Upload new document version | ❌ | ✅ | ✅ | ❌ | ❌ |
| View version history | ❌ | ✅ | ✅ | ✅ | ✅‡ |
| Tag document / add to set | ❌ | ✅ | ✅ | ✅ | ❌ |
| Flag as **evidence** | ❌ | ✅ | ✅ | ❌ | ❌ |
| Flag as **privileged** | ❌ | ✅ | ❌ | ❌ | ❌ |
| Soft delete document | ❌ | ✅ | ❌ | ❌ | ❌ |
| Hard delete document | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Restore soft-deleted doc | ✅ | ✅ | ❌ | ❌ | ❌ |

#### Evidence & Privileged Documents

| Permission | SYSADMIN | LEAD_IO | INVESTIGATOR | PARALEGAL | EXT_EXPERT |
|:---|:---:|:---:|:---:|:---:|:---:|
| View evidence documents | 🔍 | ✅ | ✅ | ✅ | ✅‡ |
| Export Chain of Custody PDF | ❌ | ✅ | ✅ | ❌ | ❌ |
| View privileged documents | ❌ | ✅ | ❌ | ❌ | ❌ |
| Override privilege (emergency) | ❌ | N/A | ⚠️ | ⚠️ | ❌ |
| Verify document integrity | ✅ | ✅ | ✅ | ❌ | ✅‡ |

#### Search & Discovery

| Permission | SYSADMIN | LEAD_IO | INVESTIGATOR | PARALEGAL | EXT_EXPERT |
|:---|:---:|:---:|:---:|:---:|:---:|
| Full-text search within case | ❌ | ✅ | ✅ | ✅ | ✅‡ |
| Cross-case search | ✅ | ❌ | ❌ | ❌ | ❌ |
| View document metadata | 🔍 | ✅ | ✅ | ✅ | ✅‡ |
| View case-level audit trail | 🔍 | ✅ | ✅ | ✅ | ✅‡ |

> **†** SYSADMIN separation-of-duties: enforced at **PostgreSQL Row-Level Security layer** — not bypassable by application-level bypass.
> **‡** EXT_EXPERT access is scoped to a specific `document_set_id` assigned by LEAD_IO; time-limited (expiry date mandatory).

---

## Section 4 — Database Schema & API Design

### 4.1 Core PostgreSQL Schema

#### Table: `users`

```sql
CREATE TABLE users (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keycloak_id           VARCHAR(255) UNIQUE NOT NULL,  -- OIDC 'sub' claim
    nic_employee_id       VARCHAR(100),                  -- NIC/MHA employee ID (from LDAP)
    email                 BYTEA NOT NULL,                -- pgcrypto encrypted
    email_hash            VARCHAR(64) UNIQUE NOT NULL,   -- SHA-256 for lookups
    full_name             BYTEA NOT NULL,                -- pgcrypto encrypted
    full_name_hindi       BYTEA,                         -- Hindi name (Devanagari)
    designation           VARCHAR(255),                  -- "SHO", "DCP", "IO"
    department            VARCHAR(255),                  -- "CBI", "IB", "Delhi Police"
    global_role           VARCHAR(50) NOT NULL DEFAULT 'OFFICER'
                          CHECK (global_role IN ('SYSADMIN', 'OFFICER')),
    mfa_enforced          BOOLEAN NOT NULL DEFAULT TRUE,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until          TIMESTAMPTZ,                   -- account lockout
    last_login_at         TIMESTAMPTZ,
    password_changed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by            UUID REFERENCES users(id)
);

CREATE INDEX idx_users_email_hash   ON users(email_hash);
CREATE INDEX idx_users_keycloak_id  ON users(keycloak_id);
CREATE INDEX idx_users_nic_emp_id   ON users(nic_employee_id);
```

#### Table: `cases`

```sql
CREATE TABLE cases (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number           VARCHAR(200) UNIQUE NOT NULL, -- FIR/Case Ref no.
    title                 VARCHAR(500) NOT NULL,
    title_hindi           VARCHAR(500),                 -- Hindi case title
    description           TEXT,
    department            VARCHAR(255) NOT NULL,        -- "CBI", "Delhi Police", "MHA Intel"
    status                VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
                          CHECK (status IN ('ACTIVE','CLOSED','ARCHIVED','LEGAL_HOLD')),
    classification        VARCHAR(50) NOT NULL DEFAULT 'CONFIDENTIAL'
                          CHECK (classification IN (
                              'UNCLASSIFIED','RESTRICTED','CONFIDENTIAL',
                              'SECRET','TOP_SECRET')),
    data_purpose          TEXT NOT NULL,                -- DPDP Act purpose limitation
    data_residency_zone   VARCHAR(50) DEFAULT 'IN-NIC', -- always India
    kek_id                VARCHAR(255) NOT NULL,        -- Vault Transit KEK for this case
    legal_hold            BOOLEAN NOT NULL DEFAULT FALSE,
    legal_hold_reason     TEXT,
    legal_hold_order_ref  VARCHAR(255),                 -- Court order reference
    legal_hold_set_by     UUID REFERENCES users(id),
    legal_hold_set_at     TIMESTAMPTZ,
    lead_io_id            UUID NOT NULL REFERENCES users(id),
    fir_number            VARCHAR(200),                 -- FIR reference
    fir_police_station    VARCHAR(255),
    court_case_number     VARCHAR(200),                 -- linked court case
    opened_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at             TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by            UUID NOT NULL REFERENCES users(id)
);

CREATE INDEX idx_cases_status      ON cases(status);
CREATE INDEX idx_cases_lead_io     ON cases(lead_io_id);
CREATE INDEX idx_cases_fir         ON cases(fir_number);
CREATE INDEX idx_cases_dept        ON cases(department);
```

#### Table: `case_permissions`

```sql
CREATE TABLE case_permissions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role              VARCHAR(50) NOT NULL
                      CHECK (role IN (
                          'LEAD_IO','INVESTIGATOR','PARALEGAL','EXT_EXPERT')),
    document_set_id   UUID,                -- NULL = full case; set for EXT_EXPERT
    access_reason     TEXT NOT NULL,       -- mandatory justification for DPDP
    access_expires_at TIMESTAMPTZ,        -- mandatory for EXT_EXPERT
    granted_by        UUID NOT NULL REFERENCES users(id),
    granted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at        TIMESTAMPTZ,
    revoked_by        UUID REFERENCES users(id),
    revoke_reason     TEXT,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (case_id, user_id)
);

CREATE INDEX idx_cp_case_user ON case_permissions(case_id, user_id, is_active);
CREATE INDEX idx_cp_expiry    ON case_permissions(access_expires_at)
    WHERE access_expires_at IS NOT NULL AND is_active = TRUE;
```

#### Table: `document_sets`

```sql
CREATE TABLE document_sets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id      UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    created_by   UUID NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table: `documents`

```sql
CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(id),
    document_set_id     UUID REFERENCES document_sets(id),

    -- Identity
    title               VARCHAR(1000) NOT NULL,
    title_hindi         VARCHAR(1000),
    original_filename   VARCHAR(1000) NOT NULL,
    mime_type           VARCHAR(255) NOT NULL,
    size_bytes          BIGINT NOT NULL,
    language            VARCHAR(10) DEFAULT 'en', -- 'en', 'hi', 'bi'

    -- Storage
    storage_bucket      VARCHAR(255) NOT NULL,
    storage_key         VARCHAR(1000) NOT NULL,
    encrypted_dek       BYTEA NOT NULL,           -- DEK wrapped by case KEK via Vault
    iv                  BYTEA NOT NULL,           -- AES-GCM IV

    -- Integrity
    sha256_hash         VARCHAR(64) NOT NULL,
    blake3_hash         VARCHAR(64) NOT NULL,
    manifest_sig        BYTEA NOT NULL,           -- Ed25519 signature
    provided_hash       VARCHAR(64),             -- hash provided by officer at upload (evidence)
    hash_verified       BOOLEAN,                 -- TRUE if provided_hash matches sha256_hash

    -- Classification
    doc_type            VARCHAR(100),
    -- MHA doc types: FIR, CHARGE_SHEET, WITNESS_STATEMENT, FORENSIC_REPORT,
    --                COURT_ORDER, INTELLIGENCE_MEMO, SEIZURE_MEMO, CORRESPONDENCE, OTHER
    classification      VARCHAR(50) NOT NULL DEFAULT 'CONFIDENTIAL',
    is_privileged       BOOLEAN NOT NULL DEFAULT FALSE,
    is_evidence         BOOLEAN NOT NULL DEFAULT FALSE,
    is_worm_locked      BOOLEAN NOT NULL DEFAULT FALSE,
    pii_detected        BOOLEAN NOT NULL DEFAULT FALSE,
    pii_types           TEXT[],
    -- Indian PII types: AADHAAR, PAN, MOBILE, ADDRESS, PERSON_NAME, PASSPORT, VIN

    -- Evidence-specific metadata
    seizure_date        DATE,
    seizure_location    VARCHAR(500),
    seizing_officer_id  UUID REFERENCES users(id),
    evidence_ref_no     VARCHAR(200),

    -- Processing State
    status              VARCHAR(50) NOT NULL DEFAULT 'PROCESSING'
                        CHECK (status IN (
                            'PROCESSING','ACTIVE','QUARANTINED',
                            'SOFT_DELETED','ARCHIVED','INTEGRITY_FAILED')),
    av_scan_status      VARCHAR(50) NOT NULL DEFAULT 'PENDING'
                        CHECK (av_scan_status IN (
                            'PENDING','CLEAN','INFECTED','ERROR')),
    av_scanned_at       TIMESTAMPTZ,
    ocr_status          VARCHAR(50) NOT NULL DEFAULT 'PENDING'
                        CHECK (ocr_status IN ('PENDING','DONE','SKIPPED','ERROR')),
    indexed_at          TIMESTAMPTZ,

    -- Versioning
    version             INTEGER NOT NULL DEFAULT 1,
    parent_doc_id       UUID REFERENCES documents(id),

    -- Lifecycle
    tags                TEXT[],
    custom_metadata     JSONB,
    uploaded_by         UUID NOT NULL REFERENCES users(id),
    uploaded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at    TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ,
    deleted_by          UUID REFERENCES users(id),
    delete_reason       TEXT
);

-- ─── Row-Level Security ────────────────────────────────────────────────────────
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Base case-membership policy
CREATE POLICY doc_case_membership ON documents
    USING (
        case_id IN (
            SELECT cp.case_id FROM case_permissions cp
            WHERE cp.user_id = current_setting('app.current_user_id')::UUID
              AND cp.is_active = TRUE
              AND (cp.access_expires_at IS NULL OR cp.access_expires_at > NOW())
        )
    );

-- Privilege isolation policy (RESTRICTIVE = must pass in addition to base)
CREATE POLICY doc_privilege_isolation ON documents
    AS RESTRICTIVE
    USING (
        is_privileged = FALSE
        OR EXISTS (
            SELECT 1 FROM case_permissions cp
            WHERE cp.user_id = current_setting('app.current_user_id')::UUID
              AND cp.case_id = documents.case_id
              AND cp.role = 'LEAD_IO'
              AND cp.is_active = TRUE
        )
    );

-- SYSADMIN sees metadata only (enforced by VIEW for SYSADMIN, not base table)
CREATE POLICY doc_sysadmin_block ON documents
    AS RESTRICTIVE
    USING (
        NOT EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = current_setting('app.current_user_id')::UUID
              AND u.global_role = 'SYSADMIN'
        )
    );

-- ─── Indexes ──────────────────────────────────────────────────────────────────
CREATE INDEX idx_docs_case         ON documents(case_id);
CREATE INDEX idx_docs_status       ON documents(status);
CREATE INDEX idx_docs_evidence     ON documents(is_evidence) WHERE is_evidence = TRUE;
CREATE INDEX idx_docs_privileged   ON documents(is_privileged) WHERE is_privileged = TRUE;
CREATE INDEX idx_docs_uploaded_by  ON documents(uploaded_by);
CREATE INDEX idx_docs_doc_type     ON documents(doc_type);
CREATE INDEX idx_docs_tags         ON documents USING GIN(tags);
CREATE INDEX idx_docs_metadata     ON documents USING GIN(custom_metadata);
```

#### Table: `audit_logs` (Append-Only, Hash-Chained)

```sql
CREATE TABLE audit_logs (
    id              UUID NOT NULL DEFAULT gen_random_uuid(),
    seq             BIGSERIAL NOT NULL,
    prev_hash       VARCHAR(64),            -- SHA-256 of entry N-1
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id        UUID REFERENCES users(id),
    actor_ip_hash   VARCHAR(64),            -- SHA-256(IP + daily_salt) for privacy
    actor_role      VARCHAR(50),
    actor_dept      VARCHAR(255),           -- MHA dept at time of action
    session_id      VARCHAR(255),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     UUID,
    case_id         UUID,                   -- no FK — audit log must survive case deletion
    document_hash   VARCHAR(64),            -- doc SHA-256 at time of action
    outcome         VARCHAR(50) NOT NULL DEFAULT 'SUCCESS'
                    CHECK (outcome IN ('SUCCESS','FAILURE','DENIED')),
    metadata        JSONB,
    entry_hash      VARCHAR(64) NOT NULL,   -- SHA-256 of all fields above
    entry_sig       BYTEA NOT NULL,         -- Ed25519(entry_hash, signing_key)

    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Monthly partitions (automate with pg_partman)
CREATE TABLE audit_logs_2026_09 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

-- Hard immutability: no UPDATE or DELETE regardless of role
CREATE RULE audit_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

-- Role-based access
REVOKE ALL ON audit_logs FROM PUBLIC;
GRANT INSERT ON audit_logs TO audit_writer_role;   -- only Celery audit task
GRANT SELECT ON audit_logs TO audit_reader_role;   -- SYSADMIN, LEAD_IO (case-scoped)

CREATE INDEX idx_audit_actor    ON audit_logs(actor_id, timestamp DESC);
CREATE INDEX idx_audit_case     ON audit_logs(case_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_id, timestamp DESC);
CREATE INDEX idx_audit_action   ON audit_logs(action, timestamp DESC);
CREATE INDEX idx_audit_seq      ON audit_logs(seq);
```

#### Table: `document_annotations`

```sql
CREATE TABLE document_annotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id),
    author_id       UUID NOT NULL REFERENCES users(id),
    annotation_type VARCHAR(50) NOT NULL
                    CHECK (annotation_type IN (
                        'NOTE','HIGHLIGHT','REDACTION','FLAG','QUERY')),
    page_number     INTEGER,
    coordinates     JSONB,                  -- {x, y, width, height}
    content         TEXT,
    content_hindi   TEXT,                   -- bilingual annotation support
    is_privileged   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Table: `approval_requests` (Dual-Approval Workflow)

```sql
CREATE TABLE approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type    VARCHAR(100) NOT NULL,
    -- Types: DOWNLOAD_PARALEGAL, BULK_EXPORT, HARD_DELETE,
    --        LEGAL_HOLD_RELEASE, PRIVILEGE_OVERRIDE
    requested_by    UUID NOT NULL REFERENCES users(id),
    case_id         UUID REFERENCES cases(id),
    resource_id     UUID,
    resource_type   VARCHAR(50),
    justification   TEXT NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','APPROVED','DENIED','EXPIRED')),
    approver_1_id   UUID REFERENCES users(id),
    approver_1_at   TIMESTAMPTZ,
    approver_1_note TEXT,
    approver_2_id   UUID REFERENCES users(id),
    approver_2_at   TIMESTAMPTZ,
    approver_2_note TEXT,
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 4.2 OpenSearch Index Mapping (`legal_documents`)

```json
{
  "mappings": {
    "properties": {
      "doc_id":           { "type": "keyword" },
      "case_id":          { "type": "keyword" },
      "title":            { "type": "text", "analyzer": "english" },
      "title_hindi":      { "type": "text", "analyzer": "hindi_standard" },
      "content":          { "type": "text", "analyzer": "english",
                            "term_vector": "with_positions_offsets" },
      "content_hindi":    { "type": "text", "analyzer": "hindi_standard" },
      "doc_type":         { "type": "keyword" },
      "tags":             { "type": "keyword" },
      "classification":   { "type": "keyword" },
      "is_privileged":    { "type": "boolean" },
      "is_evidence":      { "type": "boolean" },
      "pii_detected":     { "type": "boolean" },
      "language":         { "type": "keyword" },
      "uploaded_by":      { "type": "keyword" },
      "uploaded_at":      { "type": "date" },
      "seizure_date":     { "type": "date" },
      "allowed_user_ids": { "type": "keyword" },
      "allowed_roles":    { "type": "keyword" }
    }
  },
  "settings": {
    "analysis": {
      "analyzer": {
        "hindi_standard": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "hindi_normalization"]
        }
      }
    }
  }
}
```

---

### 4.3 REST API Endpoints

> **All endpoints** require `Authorization: Bearer <JWT>` (15-min TTL).
> **All responses** include `X-Request-ID`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.
> **Endpoint versioning**: `/api/v1/` prefix throughout.

#### Auth (`/api/v1/auth`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/token` | Exchange OIDC authorization code for JWT (PKCE) |
| `POST` | `/auth/refresh` | Refresh access token using refresh token |
| `POST` | `/auth/logout` | Revoke session; add token to Redis blocklist |
| `GET` | `/auth/me` | Get current officer profile |

#### Case Management (`/api/v1/cases`)

| Method | Path | Min Role | Description |
|---|---|---|---|
| `POST` | `/cases` | LEAD_IO, SYSADMIN | Create new case; auto-generates Vault KEK |
| `GET` | `/cases` | All | List cases user has access to (RLS-filtered) |
| `GET` | `/cases/{case_id}` | Case member | Get case details |
| `PATCH` | `/cases/{case_id}` | LEAD_IO, SYSADMIN | Update case metadata |
| `POST` | `/cases/{case_id}/close` | LEAD_IO, SYSADMIN | Close case; sets read-only mode |
| `POST` | `/cases/{case_id}/legal-hold` | SYSADMIN (dual-approve) | Apply legal hold with court order ref |
| `DELETE`| `/cases/{case_id}/legal-hold` | SYSADMIN (dual-approve) | Release legal hold |
| `GET` | `/cases/{case_id}/audit` | LEAD_IO, SYSADMIN | Case-scoped audit trail |
| `POST` | `/cases/{case_id}/permissions` | LEAD_IO, SYSADMIN | Grant case access |
| `DELETE`| `/cases/{case_id}/permissions/{user_id}` | LEAD_IO, SYSADMIN | Revoke case access |
| `GET` | `/cases/{case_id}/permissions` | LEAD_IO, SYSADMIN | List case members and roles |
| `POST` | `/cases/{case_id}/document-sets` | LEAD_IO | Create document set for EXT_EXPERT scoping |

#### Document Operations (`/api/v1/cases/{case_id}/documents`)

| Method | Path | Min Role | Description |
|---|---|---|---|
| `POST` | `/documents/upload-url` | LEAD_IO, INVESTIGATOR, PARALEGAL | Get pre-signed upload URL (10-min TTL) |
| `POST` | `/documents/confirm-upload` | LEAD_IO, INVESTIGATOR, PARALEGAL | Trigger processing pipeline |
| `GET` | `/documents` | Case member | List documents (paginated, filtered) |
| `GET` | `/documents/{doc_id}` | Case member | Get document metadata |
| `GET` | `/documents/{doc_id}/view-url` | Case member | Pre-signed view URL (watermarked PDF, 2-min TTL) |
| `GET` | `/documents/{doc_id}/download-url` | LEAD_IO, INVESTIGATOR | Pre-signed download URL (1-min TTL, logs event) |
| `PATCH` | `/documents/{doc_id}/metadata` | LEAD_IO, INVESTIGATOR, PARALEGAL | Update metadata and tags |
| `PATCH` | `/documents/{doc_id}/classify` | LEAD_IO | Set classification, evidence, privilege flags |
| `POST` | `/documents/{doc_id}/versions` | LEAD_IO, INVESTIGATOR | Upload new version |
| `GET` | `/documents/{doc_id}/versions` | Case member | List all versions |
| `GET` | `/documents/{doc_id}/integrity` | Case member | Verify current document hash |
| `GET` | `/documents/{doc_id}/audit` | LEAD_IO, SYSADMIN | Document-level audit trail |
| `GET` | `/documents/{doc_id}/custody-certificate` | LEAD_IO, INVESTIGATOR | Export §65B-compliant CoC PDF |
| `DELETE`| `/documents/{doc_id}` | LEAD_IO | Soft delete (no deletion if WORM-locked) |
| `POST` | `/documents/{doc_id}/restore` | LEAD_IO, SYSADMIN | Restore soft-deleted document |
| `POST` | `/documents/{doc_id}/annotations` | Case member | Create annotation |
| `GET` | `/documents/{doc_id}/annotations` | Case member | List annotations |

#### Search (`/api/v1/search`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/search` | Full-text search across user's accessible cases |
| `POST` | `/search/cases/{case_id}` | Full-text search within a specific case |
| `GET` | `/search/suggest` | Bilingual autocomplete suggestions |

**Search Request Body:**
```json
{
  "query":   "string (supports Hindi/English)",
  "case_id": "uuid (optional)",
  "filters": {
    "doc_type":     ["FIR", "FORENSIC_REPORT"],
    "classification": ["CONFIDENTIAL"],
    "date_range":   { "from": "2026-01-01", "to": "2026-12-31" },
    "uploaded_by":  "uuid",
    "tags":         ["string"],
    "is_evidence":  true,
    "language":     "hi"
  },
  "highlight": true,
  "page": 1,
  "page_size": 25
}
```

#### Admin (`/api/v1/admin`) — SYSADMIN only

| Method | Path | Description |
|---|---|---|
| `POST` | `/admin/users` | Create new officer account |
| `GET` | `/admin/users` | List all users (PII decrypted for admin) |
| `GET` | `/admin/users/{user_id}` | Get officer profile |
| `PATCH` | `/admin/users/{user_id}` | Update officer details / role |
| `POST` | `/admin/users/{user_id}/disable` | Disable account immediately |
| `GET` | `/admin/audit` | Query system-wide audit logs |
| `GET` | `/admin/audit/verify` | Verify entire audit chain integrity |
| `POST` | `/admin/audit/export` | Export audit segment + §65B certificate |

#### Approvals (`/api/v1/approvals`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/approvals` | List pending approvals for current officer |
| `POST` | `/approvals/{id}/approve` | Approve a pending request |
| `POST` | `/approvals/{id}/deny` | Deny a pending request |

---

### 4.4 API Security Middleware Pipeline

```
Incoming Request
      │
      ├─► [1] TLS 1.3 Termination (Nginx)
      ├─► [2] WAF Rules (ModSecurity OWASP CRS) — block SQLi, XSS, path traversal
      ├─► [3] Rate Limiter — per IP: 100 req/min; per user: 200 req/min
      ├─► [4] Request Size Check — max 500MB (configurable per endpoint)
      ├─► [5] JWT Signature Validation (RS256, public key from Keycloak JWKS)
      ├─► [6] JWT Expiry + Issuer + Audience Check
      ├─► [7] Token Revocation Check (Redis blocklist — sub-millisecond)
      ├─► [8] MFA Assertion Check (amr claim must include 'otp' or 'hwk')
      ├─► [9] Account Status Check (is_active, locked_until)
      ├─► [10] RBAC Permission Check (role vs. endpoint permission table)
      ├─► [11] Case Membership Check (for case-scoped endpoints)
      ├─► [12] Input Sanitization (Pydantic strict validation)
      ├─► [13] Audit Log: REQUEST_START event
            │
            ▼
       [Handler Logic]
            │
      ├─► [14] Audit Log: REQUEST_OUTCOME event (SUCCESS/FAILURE/DENIED)
      ├─► [15] Sensitive Data Scrub (remove PII from response logs)
      └─► [16] Security Response Headers Injection
```

---

## Section 5 — Implementation Roadmap for Gemini

> [!IMPORTANT]
> Phases are **strictly sequential**. Each phase ends with a **verification checkpoint** — Gemini must run all verification steps and confirm they pass before writing a single line of Phase N+1 code.

---

### Phase 1 — Secure Infrastructure Foundation
**Duration: Week 1–2 | Output: Hardened skeleton with auth, audit scaffolding, and all services running**

#### Step 1.1 — Project Scaffolding
- [ ] Initialize monorepo with directories: `apps/backend/`, `apps/frontend/`, `infra/`, `scripts/`, `docs/`
- [ ] Configure `pyproject.toml`: `ruff` (linting), `mypy --strict` (type checking), `pytest` (testing), `pre-commit`
- [ ] Add `detect-secrets` pre-commit hook to prevent credential leaks
- [ ] Create `docker-compose.yml` with all services: PostgreSQL, Redis, MinIO, Keycloak, Vault, ClamAV, Tika, OpenSearch

#### Step 1.2 — HashiCorp Vault
- [ ] Initialize Vault with Shamir 5-of-3 (5 key shares, 3 required to unseal)
- [ ] Enable **Transit secrets engine** — create `case-master-kek` for new case KEK generation
- [ ] Enable **PKI secrets engine** — generate internal CA for mTLS certificates
- [ ] Enable **Database secrets engine** — configure PostgreSQL for dynamic credentials (30-min TTL for `app_writer`, `audit_writer`)
- [ ] Enable **KV v2** — store: Ed25519 signing key pair, daily audit salt, app secrets

#### Step 1.3 — PostgreSQL Setup
- [ ] Enable extensions: `pgaudit`, `pgcrypto`, `uuid-ossp`, `pg_partman`
- [ ] Run all schema DDL from Section 4.1 in migration order
- [ ] Create DB roles: `app_writer` (INSERT/UPDATE/SELECT), `app_reader` (SELECT), `audit_writer` (INSERT on audit_logs only), `audit_reader` (SELECT on audit_logs)
- [ ] Apply all RLS policies; write a RLS bypass test to confirm they work
- [ ] Configure `pg_partman` to auto-create monthly `audit_logs` partitions

#### Step 1.4 — Keycloak Configuration
- [ ] Create realm `mha-legal-docs`
- [ ] Configure PKCE flow; access token TTL = 15 min; refresh token TTL = 8 hours
- [ ] Enforce MFA: TOTP required; FIDO2 optional
- [ ] Configure LDAP federation → NIC Active Directory (in dev: use an OpenLDAP stub)
- [ ] Map LDAP attributes: `employeeID` → `nic_employee_id`, `department` → `department`
- [ ] Create realm roles mapping to RBAC roles; add to JWT `roles` claim

#### Step 1.5 — FastAPI Foundation
- [ ] Implement OIDC JWT validation middleware (RS256, JWKS endpoint, iss/aud checks)
- [ ] Implement Redis-based token revocation blocklist (checked on every request)
- [ ] Implement `require_permission(action)` dependency with RBAC lookup table
- [ ] Implement case-membership dependency: `require_case_access(case_id, min_role)`
- [ ] Implement per-user + per-IP rate limiter with Redis sliding window
- [ ] Implement `structlog` structured JSON logging; include `request_id`, `user_id`, `case_id` in every log line
- [ ] Implement `GET /health` and `GET /health/ready` (checks: DB, Redis, Vault, MinIO connectivity)

#### Step 1.6 — Audit Service
- [ ] Implement `AuditService` class:
  - `log_event(actor, action, resource, outcome, metadata)` → computes `entry_hash`, signs with Ed25519, chains `prev_hash`, writes via Celery task
  - `verify_chain(from_seq, to_seq)` → recomputes hash chain; returns first broken link or `VALID`
- [ ] Implement `POST /admin/audit/verify` endpoint
- [ ] Write unit test: generate 100 audit entries, tamper entry #50, verify chain detects the break

**✅ Phase 1 Checkpoint:**
- [ ] Login with Keycloak TOTP works; JWT issued and validated
- [ ] Tampered JWT returns 401; expired JWT returns 401
- [ ] Logged-out token (in Redis blocklist) returns 401
- [ ] User A cannot see User B's cases via direct API call (RLS test)
- [ ] SYSADMIN cannot fetch document content (RLS test)
- [ ] Every API request generates an audit log entry with correct `prev_hash` chaining
- [ ] Audit chain verification passes on 100-entry test set

---

### Phase 2 — Document Ingestion & Retrieval Pipeline
**Duration: Week 3–4 | Output: End-to-end encrypted upload → processing → search → download**

#### Step 2.1 — MinIO Setup
- [ ] Create bucket policy: `cases-{id}` (WORM-enabled, versioned, server-side encryption with Vault KMS)
- [ ] Create `temp-uploads` bucket (no WORM, 24-hour object TTL lifecycle rule)
- [ ] Configure MinIO to use Vault Transit for SSE-KMS (server-side encryption key management)
- [ ] Implement pre-signed URL generator: 10-min TTL for PUT, 1-min TTL for GET

#### Step 2.2 — Upload Pipeline (Celery Task Chain)
- [ ] `POST /documents/upload-url` — validate case access → generate pre-signed PUT URL for `temp-uploads` → return to client
- [ ] `POST /documents/confirm-upload` — enqueue Celery task chain:
  - **Task 1**: Download from temp bucket to in-memory stream (never write to disk)
  - **Task 2**: Validate true MIME type (`python-magic`); reject if mismatch
  - **Task 3**: ClamAV AV scan; if INFECTED → move to quarantine bucket, log `AV_SCAN_QUARANTINE`, abort
  - **Task 4**: Apache Tika content extraction; Tesseract OCR for scanned images/PDFs (Hindi + English)
  - **Task 5**: spaCy Indian-PII NER scan (Aadhaar pattern, PAN pattern, mobile, name); set `pii_detected`, `pii_types`
  - **Task 6**: Verify provided hash if `is_evidence=TRUE`; abort if hash mismatch, log `EVIDENCE_HASH_MISMATCH`
  - **Task 7**: Generate SHA-256 + BLAKE3 hashes of plaintext
  - **Task 8**: AES-256-GCM encrypt with unique DEK; request DEK wrapped by case KEK from Vault Transit
  - **Task 9**: Upload encrypted blob to `cases-{id}` bucket; apply WORM lock if `is_evidence=TRUE`
  - **Task 10**: Insert `documents` row (all metadata + hashes + encrypted DEK + IV)
  - **Task 11**: Enqueue OpenSearch indexing task
  - **Task 12**: Log `DOC_UPLOAD` audit event; delete temp object

#### Step 2.3 — Download & View Pipeline
- [ ] `GET /documents/{doc_id}/view-url`:
  - Validate access (RBAC + RLS)
  - Retrieve encrypted blob → decrypt in memory → convert to PDF if not already
  - Stamp watermark: officer name + badge number + timestamp + "CONFIDENTIAL - OFFICIAL USE ONLY"
  - Return watermarked PDF via streaming proxy; log `DOC_VIEW`
- [ ] `GET /documents/{doc_id}/download-url`:
  - Validate LEAD_IO or INVESTIGATOR role
  - Retrieve and decrypt in memory
  - Return original file via streaming response; log `DOC_DOWNLOAD`
- [ ] Implement integrity check on every retrieval: recompute SHA-256; if mismatch → block download, set `status = 'INTEGRITY_FAILED'`, log `INTEGRITY_VIOLATION_ALERT`

#### Step 2.4 — OpenSearch Indexing
- [ ] Deploy OpenSearch with security plugin; create index `legal_documents` with mapping from Section 4.2
- [ ] Implement Celery task: index extracted text (Hindi + English) + metadata; set `allowed_user_ids` per case permissions
- [ ] Implement `POST /search` with:
  - User-scoped query (filter by `allowed_user_ids` containing current user)
  - Exclude `is_privileged = TRUE` documents for non-LEAD_IO
  - Highlight matched terms; return paginated results
  - Log `SEARCH_QUERY` with full query string
- [ ] Re-index task: triggered when case permissions change (adds/removes users from `allowed_user_ids`)

#### Step 2.5 — Evidence Chain of Custody
- [ ] Implement `GET /documents/{doc_id}/custody-certificate`:
  - Fetch all audit log entries for `resource_id = doc_id`
  - Render PDF (using Gotenberg/LibreOffice) with: case details, document hashes, chronological access log
  - Sign PDF with system Ed25519 key; attach RFC 3161 timestamp
  - Return signed PDF; log `EVIDENCE_CHAIN_EXPORT`

**✅ Phase 2 Checkpoint:**
- [ ] Upload a multi-page Hindi PDF → verify text extracted in both Hindi/English → verify SHA-256 in DB matches local file hash
- [ ] Upload EICAR test virus → verify quarantine, no DB record created
- [ ] Upload DOCX with macro → verify macro stripped, content extracted
- [ ] Upload evidence file with `provided_hash` → verify hash comparison logged
- [ ] Download original file → decrypt → verify SHA-256 matches stored hash
- [ ] Watermarked PDF view shows officer name and timestamp
- [ ] Search "अभियोग" (Hindi for "prosecution") returns relevant results
- [ ] INVESTIGATOR search returns no privileged documents
- [ ] Privilege-flagged document is absent from PARALEGAL's search results
- [ ] Chain of Custody PDF generated with valid Ed25519 signature

---

### Phase 3 — RBAC Workflows, Case Management & Bilingual UI
**Duration: Week 5–6 | Output: Complete frontend application with full RBAC enforcement**

#### Step 3.1 — Case Management API
- [ ] Implement all `/cases` endpoints from Section 4.3
- [ ] On case creation: generate unique Vault Transit KEK for the case; store `kek_id` in `cases` table
- [ ] Implement legal hold: DB trigger blocks `UPDATE status` and `DELETE` on held cases
- [ ] Implement access expiry job: runs every 5 minutes, disables expired `case_permissions`, logs `CASE_PERMISSION_REVOKE`, triggers OpenSearch re-index

#### Step 3.2 — Dual-Approval Workflow
- [ ] Implement `approval_requests` table endpoints (Section 4.1)
- [ ] Implement approval gates for: PARALEGAL downloads, bulk exports, hard deletes, legal hold release, privilege override
- [ ] Implement in-app notification (WebSocket or SSE) when approval is requested or resolved
- [ ] Approvals expire after 24 hours; expired approvals are auto-denied with audit log entry

#### Step 3.3 — Frontend: Auth Flow
- [ ] Implement Keycloak PKCE login flow with `next-auth`
- [ ] Silent token refresh using refresh token; redirect to login on 401
- [ ] Language selector: English / हिंदी persisted per user in localStorage
- [ ] Display officer name, designation, and department in header

#### Step 3.4 — Frontend: Case Dashboard
- [ ] Case list: show case number, title (bilingual), status badge, classification badge, FIR number
- [ ] Create Case modal: all required fields including FIR number, court case number, data purpose
- [ ] Case detail: document count, member list with roles, classification indicator

#### Step 3.5 — Frontend: Document Management
- [ ] Drag-and-drop upload with chunked upload progress (for large files up to 500MB)
- [ ] Upload form: mandatory evidence fields (seizure date, location, officer) shown when `is_evidence` toggled
- [ ] Document list: filterable by doc_type, classification, language, date, tags
- [ ] Document detail panel: metadata, version history, annotation list
- [ ] In-browser PDF viewer (PDF.js) displaying watermarked proxy; disable right-click save, print only allowed for LEAD_IO/INVESTIGATOR
- [ ] Evidence badge (🔒 WORM) and Privilege badge (⚖️) clearly visible
- [ ] Chain of Custody certificate download button (LEAD_IO, INVESTIGATOR only)
- [ ] Integrity status indicator (green tick / red warning) on document list

#### Step 3.6 — Frontend: Admin Panel
- [ ] User management: create officer, assign global role, disable/enable account, view login history
- [ ] Audit log viewer: filter by actor, case, action, date range; display hash chain validity indicator
- [ ] System health dashboard: Vault status, MinIO status, OpenSearch status, ClamAV status

**✅ Phase 3 Checkpoint:**
- [ ] Log in as each of 5 roles → verify correct UI features visible/hidden for each
- [ ] Attempt cross-case document access via Postman → 403 + audit log entry
- [ ] Set EXT_EXPERT access with 1-minute expiry → verify denied after expiry
- [ ] Trigger PARALEGAL download → verify approval request created → approve it → verify download allowed
- [ ] Hindi UI: switch to हिंदी → verify all labels rendered correctly
- [ ] Search for Hindi text in Hindi UI → verify results returned with highlighted terms

---

### Phase 4 — Compliance, Hardening & Production Readiness
**Duration: Week 7–8 | Output: Production-deployable system, security-hardened, fully observable**

#### Step 4.1 — Legal Compliance Features
- [ ] **§65B BSA Certificate Generator**: render certificate PDF with system ID, log hash, Ed25519 signature, RFC 3161 timestamp; attach to audit log exports
- [ ] **RFC 3161 Timestamp Authority**: integrate NIC-approved TSA (or Sectigo fallback); timestamp every document on upload; store TSA token in `documents.custom_metadata`
- [ ] **DPDP Act Erasure Handler**: pseudonymize user PII in audit logs (replace name with `[REDACTED-{hash}]`) while preserving hash chain integrity; block if `legal_hold = TRUE`
- [ ] **Retention Scheduler**: Celery beat job — archive documents past case retention date (configurable per case); generate retention action audit entry
- [ ] **Compliance Report Export**: LEAD_IO can export all case access events as JSON/CSV for submission to courts or regulatory bodies

#### Step 4.2 — Security Hardening
- [ ] Run `pip-audit` + `npm audit`; resolve all HIGH/CRITICAL CVEs before deployment
- [ ] Run OWASP ZAP scan against staging API; remediate all HIGH/CRITICAL findings
- [ ] Implement CSP headers on all Next.js pages (nonce-based script policy)
- [ ] Implement Subresource Integrity (SRI) on all external assets
- [ ] Implement account lockout: 5 failed attempts → lock for 30 minutes → log `ACCOUNT_LOCKED`; admin unlock endpoint
- [ ] Add `Referrer-Policy: no-referrer` and `Permissions-Policy` headers
- [ ] Enforce `secure`, `httpOnly`, `sameSite=Strict` on all cookies
- [ ] Database: enforce SSL-only connections; disable `trust` auth in `pg_hba.conf`

#### Step 4.3 — Observability
- [ ] OpenTelemetry SDK in FastAPI: traces per request with `user_id`, `case_id`, `action` as span attributes
- [ ] Prometheus metrics: request latency (p50/p99), error rate by endpoint, document pipeline queue depth, Vault decrypt latency, ClamAV scan latency
- [ ] Grafana dashboards:
  - **API Health**: request rate, latency, error rate
  - **Security**: failed logins per minute, forbidden access attempts, rate limit hits
  - **Document Pipeline**: queue depth, scan status breakdown, processing latency
- [ ] Alertmanager rules:
  - `>10 forbidden access attempts in 5 min` → page SOC
  - `audit log write failure` → critical alert
  - `ClamAV service down > 60s` → block all uploads
  - `Vault unreachable > 30s` → critical alert

#### Step 4.4 — Kubernetes & NIC Deployment
- [ ] Write Kubernetes manifests: `Deployment`, `Service`, `ConfigMap`, `Secret` (SealedSecrets), `HPA`, `NetworkPolicy` (deny-all default)
- [ ] Write Helm chart with values: `dev`, `staging`, `prod-nic`
- [ ] Implement automated backup: `pg_dump` + `mc mirror` (MinIO) → GPG-sign → ship to NIC cold storage
- [ ] Write and test backup restoration runbook
- [ ] Configure PostgreSQL Patroni for automatic failover
- [ ] RTO target: < 4 hours | RPO target: < 1 hour

#### Step 4.5 — Test Suite
- [ ] Integration tests: all 5 roles × all API endpoints (should return correct 200/403/401)
- [ ] Audit chain integrity test: generate 10,000 entries, tamper entry #5000, verify detection
- [ ] Evidence pipeline E2E: upload → AV scan → encrypt → index → search → download → hash verify → CoC PDF
- [ ] Load test: 100 concurrent uploads → verify 0 data corruption or cross-user data leak
- [ ] Hindi search test: upload Hindi document → search with Hindi query → verify correct result

**✅ Phase 4 Checkpoint:**
- [ ] §65B certificate PDF generated with valid signature and RFC 3161 timestamp
- [ ] OWASP ZAP scan: zero HIGH/CRITICAL findings
- [ ] `pip-audit` + `npm audit`: zero HIGH/CRITICAL CVEs
- [ ] Full RBAC integration test suite: 100% pass rate
- [ ] Audit chain tamper test: detection confirmed
- [ ] Load test: 100 concurrent uploads with 0 data integrity failures
- [ ] Kubernetes deployment on NIC staging: all pods healthy, mTLS verified between services

---

## Appendix A — Critical Security Invariants (Gemini Must Never Violate)

1. **No plaintext document ever touches disk on the application server.** Stream encrypted directly to/from MinIO — memory only.
2. **Audit logs are write-once, period.** The DB role for `audit_logs` has INSERT only. No UPDATE, no DELETE — enforced at DB role level, not application level.
3. **Every API error returns a generic message to the client.** Detailed errors go to structured logs only. Zero stack traces to client.
4. **Every DEK is unique per document.** Never reuse DEKs across documents, versions, or cases.
5. **SYSADMIN cannot read case document content.** Enforced at PostgreSQL RLS — not bypassable by application code.
6. **Privileged document access by non-LEAD_IO always generates `PRIVILEGE_OVERRIDE_ALERT`**, even if granted via dual-approval.
7. **Evidence documents are WORM-locked immediately.** No application code path to unlock — requires manual Vault + MinIO console quorum.
8. **Session tokens are invalidated on logout** by Redis blocklist check — not just left to JWT TTL expiry.
9. **JWT claims are re-validated on every request.** No caching of authorization decisions beyond the request lifetime.
10. **All inter-service communication uses mTLS.** No plain HTTP on internal network, even inside Kubernetes.
11. **Hash chain must never be paused.** Even during maintenance or partition creation, audit entries continue to chain correctly.
12. **Aadhaar numbers are never stored in plaintext** anywhere in the system — encrypted at rest and masked in all log outputs.

---

## Appendix B — Project File Structure

```
sih26190-legal-dms/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   │   ├── config.py          # Pydantic settings from env
│   │   │   │   ├── database.py        # SQLAlchemy async engine + RLS session
│   │   │   │   ├── vault.py           # Vault Transit/KV client
│   │   │   │   ├── minio.py           # MinIO client + pre-signed URL
│   │   │   │   ├── opensearch.py      # OpenSearch client
│   │   │   │   └── security.py        # JWT validation, RBAC, signing
│   │   │   ├── models/                # SQLAlchemy ORM models
│   │   │   ├── schemas/               # Pydantic request/response schemas
│   │   │   ├── api/
│   │   │   │   ├── auth.py
│   │   │   │   ├── cases.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── search.py
│   │   │   │   ├── approvals.py
│   │   │   │   └── admin.py
│   │   │   ├── services/
│   │   │   │   ├── audit_service.py   # Hash-chain + Ed25519 audit logging
│   │   │   │   ├── document_service.py
│   │   │   │   ├── case_service.py
│   │   │   │   ├── encryption_service.py
│   │   │   │   └── coc_service.py     # Chain-of-Custody PDF
│   │   │   ├── workers/               # Celery tasks
│   │   │   │   ├── av_scan.py
│   │   │   │   ├── tika_extract.py
│   │   │   │   ├── pii_detect.py      # spaCy Indian PII NER
│   │   │   │   ├── encrypt_store.py
│   │   │   │   ├── index_document.py
│   │   │   │   └── access_expiry.py   # Celery beat job
│   │   │   └── middleware/
│   │   │       ├── jwt_auth.py
│   │   │       ├── rbac.py
│   │   │       ├── rate_limit.py
│   │   │       └── audit_hook.py
│   │   ├── tests/
│   │   │   ├── integration/           # Per-endpoint RBAC tests
│   │   │   ├── security/              # RLS tests, tamper tests
│   │   │   └── e2e/                   # Full pipeline tests
│   │   ├── alembic/                   # DB migrations
│   │   └── pyproject.toml
│   └── frontend/
│       ├── app/                       # Next.js App Router
│       │   ├── [locale]/              # i18n routing (en / hi)
│       │   │   ├── dashboard/
│       │   │   ├── cases/
│       │   │   └── admin/
│       ├── components/
│       │   ├── documents/
│       │   ├── cases/
│       │   └── admin/
│       ├── lib/
│       │   ├── auth.ts               # next-auth Keycloak provider
│       │   ├── api-client.ts
│       │   └── i18n.ts
│       ├── messages/
│       │   ├── en.json
│       │   └── hi.json               # Hindi translations
│       └── package.json
├── infra/
│   ├── docker-compose.yml
│   ├── vault/
│   │   └── config.hcl
│   ├── keycloak/
│   │   └── mha-realm-export.json
│   ├── postgres/
│   │   └── 01-init.sql
│   ├── opensearch/
│   │   └── legal_documents_mapping.json
│   └── k8s/
│       ├── namespaces/
│       ├── deployments/
│       ├── services/
│       ├── network-policies/
│       └── helm/
│           └── legal-dms/
├── scripts/
│   ├── seed_dev_data.py
│   ├── verify_audit_chain.py
│   ├── rotate_case_kek.py
│   └── backup.sh
└── docs/
    ├── blueprint.md                  ← this document
    ├── runbook.md
    ├── security-controls.md
    └── compliance-matrix.md
```

---

*Blueprint prepared for SIH26190 — Ministry of Home Affairs, Government of India*
*Smart India Hackathon 2026 | Submission Deadline: 30 September 2026*
