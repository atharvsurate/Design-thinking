-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create roles for security isolation
-- In a real scenario, password should be injected securely, not hardcoded
DO \$\$
BEGIN
  CREATE ROLE app_writer WITH LOGIN PASSWORD 'app_secure_pass';
  EXCEPTION WHEN DUPLICATE_OBJECT THEN
  RAISE NOTICE 'not creating role app_writer -- it already exists';
END
\$\$;

DO \$\$
BEGIN
  CREATE ROLE audit_writer WITH LOGIN PASSWORD 'audit_secure_pass';
  EXCEPTION WHEN DUPLICATE_OBJECT THEN
  RAISE NOTICE 'not creating role audit_writer -- it already exists';
END
\$\$;

-- Set current app user parameter for RLS context
-- e.g., SET app.current_user_id = 'uuid';

-------------------------------------------------------------------------------
-- 1. USERS TABLE
-------------------------------------------------------------------------------
CREATE TABLE users (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keycloak_id           VARCHAR(255) UNIQUE NOT NULL,
    nic_employee_id       VARCHAR(100),
    email                 BYTEA NOT NULL,
    email_hash            VARCHAR(64) UNIQUE NOT NULL,
    full_name             BYTEA NOT NULL,
    full_name_hindi       BYTEA,
    designation           VARCHAR(255),
    department            VARCHAR(255),
    global_role           VARCHAR(50) NOT NULL DEFAULT 'OFFICER'
                          CHECK (global_role IN ('SYSADMIN', 'OFFICER')),
    mfa_enforced          BOOLEAN NOT NULL DEFAULT TRUE,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until          TIMESTAMPTZ,
    last_login_at         TIMESTAMPTZ,
    password_changed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by            UUID REFERENCES users(id)
);

CREATE INDEX idx_users_email_hash   ON users(email_hash);
CREATE INDEX idx_users_keycloak_id  ON users(keycloak_id);
CREATE INDEX idx_users_nic_emp_id   ON users(nic_employee_id);

-------------------------------------------------------------------------------
-- 2. CASES TABLE
-------------------------------------------------------------------------------
CREATE TABLE cases (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_number           VARCHAR(200) UNIQUE NOT NULL,
    title                 VARCHAR(500) NOT NULL,
    title_hindi           VARCHAR(500),
    description           TEXT,
    department            VARCHAR(255) NOT NULL,
    status                VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
                          CHECK (status IN ('ACTIVE','CLOSED','ARCHIVED','LEGAL_HOLD')),
    classification        VARCHAR(50) NOT NULL DEFAULT 'CONFIDENTIAL'
                          CHECK (classification IN (
                              'UNCLASSIFIED','RESTRICTED','CONFIDENTIAL',
                              'SECRET','TOP_SECRET')),
    data_purpose          TEXT NOT NULL,
    data_residency_zone   VARCHAR(50) DEFAULT 'IN-NIC',
    kek_id                VARCHAR(255) NOT NULL,
    legal_hold            BOOLEAN NOT NULL DEFAULT FALSE,
    legal_hold_reason     TEXT,
    legal_hold_order_ref  VARCHAR(255),
    legal_hold_set_by     UUID REFERENCES users(id),
    legal_hold_set_at     TIMESTAMPTZ,
    lead_io_id            UUID NOT NULL REFERENCES users(id),
    fir_number            VARCHAR(200),
    fir_police_station    VARCHAR(255),
    court_case_number     VARCHAR(200),
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

-------------------------------------------------------------------------------
-- 3. CASE PERMISSIONS TABLE
-------------------------------------------------------------------------------
CREATE TABLE case_permissions (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role              VARCHAR(50) NOT NULL
                      CHECK (role IN (
                          'LEAD_IO','INVESTIGATOR','PARALEGAL','EXT_EXPERT')),
    document_set_id   UUID,
    access_reason     TEXT NOT NULL,
    access_expires_at TIMESTAMPTZ,
    granted_by        UUID NOT NULL REFERENCES users(id),
    granted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at        TIMESTAMPTZ,
    revoked_by        UUID REFERENCES users(id),
    revoke_reason     TEXT,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (case_id, user_id)
);

CREATE INDEX idx_cp_case_user ON case_permissions(case_id, user_id, is_active);

-------------------------------------------------------------------------------
-- 4. DOCUMENT SETS
-------------------------------------------------------------------------------
CREATE TABLE document_sets (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id      UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    created_by   UUID NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-------------------------------------------------------------------------------
-- 5. DOCUMENTS TABLE
-------------------------------------------------------------------------------
CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id             UUID NOT NULL REFERENCES cases(id),
    document_set_id     UUID REFERENCES document_sets(id),
    title               VARCHAR(1000) NOT NULL,
    title_hindi         VARCHAR(1000),
    original_filename   VARCHAR(1000) NOT NULL,
    mime_type           VARCHAR(255) NOT NULL,
    size_bytes          BIGINT NOT NULL,
    language            VARCHAR(10) DEFAULT 'en',
    storage_bucket      VARCHAR(255) NOT NULL,
    storage_key         VARCHAR(1000) NOT NULL,
    encrypted_dek       BYTEA NOT NULL,
    iv                  BYTEA NOT NULL,
    sha256_hash         VARCHAR(64) NOT NULL,
    blake3_hash         VARCHAR(64) NOT NULL,
    manifest_sig        BYTEA NOT NULL,
    provided_hash       VARCHAR(64),
    hash_verified       BOOLEAN,
    doc_type            VARCHAR(100),
    classification      VARCHAR(50) NOT NULL DEFAULT 'CONFIDENTIAL',
    is_privileged       BOOLEAN NOT NULL DEFAULT FALSE,
    is_evidence         BOOLEAN NOT NULL DEFAULT FALSE,
    is_worm_locked      BOOLEAN NOT NULL DEFAULT FALSE,
    pii_detected        BOOLEAN NOT NULL DEFAULT FALSE,
    pii_types           TEXT[],
    seizure_date        DATE,
    seizure_location    VARCHAR(500),
    seizing_officer_id  UUID REFERENCES users(id),
    evidence_ref_no     VARCHAR(200),
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
    version             INTEGER NOT NULL DEFAULT 1,
    parent_doc_id       UUID REFERENCES documents(id),
    tags                TEXT[],
    custom_metadata     JSONB,
    uploaded_by         UUID NOT NULL REFERENCES users(id),
    uploaded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at    TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ,
    deleted_by          UUID REFERENCES users(id),
    delete_reason       TEXT
);

-- RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY doc_sysadmin_block ON documents
    AS RESTRICTIVE
    USING (
        current_setting('app.current_global_role', true) != 'SYSADMIN'
    );

CREATE INDEX idx_docs_case         ON documents(case_id);
CREATE INDEX idx_docs_status       ON documents(status);

-------------------------------------------------------------------------------
-- 6. AUDIT LOGS (Append-Only, Hash-Chained, Partitioned)
-------------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id              UUID NOT NULL DEFAULT uuid_generate_v4(),
    seq             BIGSERIAL NOT NULL,
    prev_hash       VARCHAR(64),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id        UUID REFERENCES users(id),
    actor_ip_hash   VARCHAR(64),
    actor_role      VARCHAR(50),
    actor_dept      VARCHAR(255),
    session_id      VARCHAR(255),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     UUID,
    case_id         UUID,
    document_hash   VARCHAR(64),
    outcome         VARCHAR(50) NOT NULL DEFAULT 'SUCCESS'
                    CHECK (outcome IN ('SUCCESS','FAILURE','DENIED')),
    metadata        JSONB,
    entry_hash      VARCHAR(64) NOT NULL,
    entry_sig       BYTEA NOT NULL,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Default partition for current month (will need pg_partman to auto-manage moving forward)
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;

-- Ensure true immutability at the database level
CREATE RULE audit_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

-- Revoke all, grant insert only to audit_writer
REVOKE ALL ON audit_logs FROM PUBLIC;
GRANT INSERT ON audit_logs TO audit_writer;
GRANT SELECT ON audit_logs TO app_writer;

CREATE INDEX idx_audit_actor    ON audit_logs(actor_id, timestamp DESC);
CREATE INDEX idx_audit_case     ON audit_logs(case_id, timestamp DESC);
CREATE INDEX idx_audit_seq      ON audit_logs(seq);

