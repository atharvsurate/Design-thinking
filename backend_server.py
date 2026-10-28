"""
SIH26190 - Secure Legal DMS Backend
Pure stdlib backend: http.server + sqlite3 + scikit-learn (already installed)
No pip installs needed. Runs on Python 3.12 standard.
"""
import sqlite3
import json
import hashlib
import os
import re
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "dms.db")

# ──────────────────────────────────────────
# DATABASE SETUP
# ──────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id          TEXT    NOT NULL,
            filename         TEXT    NOT NULL,
            file_size        TEXT    NOT NULL,
            doc_type         TEXT    NOT NULL,
            is_evidence      INTEGER NOT NULL DEFAULT 0,
            seizure_date     TEXT,
            seizure_location TEXT,
            sha256_hash      TEXT    NOT NULL,
            classification   TEXT    NOT NULL DEFAULT 'Other',
            class_confidence REAL    NOT NULL DEFAULT 0.0,
            class_status     TEXT    NOT NULL DEFAULT 'auto',
            uploaded_at      TEXT    NOT NULL,
            uploader_id      TEXT    NOT NULL DEFAULT 'NIC-994321'
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            seq          INTEGER PRIMARY KEY AUTOINCREMENT,
            prev_hash    TEXT NOT NULL,
            entry_hash   TEXT NOT NULL,
            actor_id     TEXT NOT NULL,
            action       TEXT NOT NULL,
            resource_id  TEXT,
            outcome      TEXT NOT NULL,
            logged_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cases (
            case_id     TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id         TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            role            TEXT NOT NULL,
            role_label      TEXT NOT NULL,
            agency          TEXT NOT NULL,
            initials        TEXT NOT NULL,
            can_upload      INTEGER NOT NULL DEFAULT 1,
            can_reclassify  INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS case_assignments (
            case_id         TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            role_in_case    TEXT NOT NULL,
            assigned_at     TEXT NOT NULL,
            PRIMARY KEY (case_id, user_id)
        );

        INSERT OR IGNORE INTO cases VALUES
            ('CBI-2026-0042', 'Operation Silken Thread - Financial Fraud', '2026-01-15T09:00:00'),
            ('DP-2026-8991',  'FIR 49/2026 - Cyber Espionage Incident',   '2026-02-20T11:30:00'),
            ('NIA-2026-1105', 'Operation Black Horizon - Counter-Terrorism', '2026-03-05T14:00:00');

        INSERT OR IGNORE INTO users VALUES
            ('NIC-994321', 'Insp. R. Kumar',    'LEAD_IO',          'Lead Investigating Officer', 'CBI - Anti-Corruption',  'RK', 1, 1),
            ('NIC-882104', 'Dr. A. Verma',      'FORENSIC_EXPERT',  'Chief Forensic Analyst',     'CFSL Cyber Forensics',   'AV', 1, 0),
            ('NIC-773219', 'Adv. S. Iyer',      'PROSECUTOR',       'Special Public Prosecutor',  'Ministry of Law',        'SI', 0, 0),
            ('NIC-110022', 'K. Swaminathan',    'AUDITOR',          'Director of Vigilance',      'MHA Audit Directorate',  'KS', 0, 0);

        INSERT OR IGNORE INTO case_assignments VALUES
            -- Insp. R. Kumar: CBI-0042 & DP-8991
            ('CBI-2026-0042', 'NIC-994321', 'Lead Investigator', '2026-01-15T09:00:00'),
            ('DP-2026-8991',  'NIC-994321', 'Co-Investigator',   '2026-02-20T11:30:00'),

            -- Dr. A. Verma: DP-8991 & NIA-1105 (Forensics)
            ('DP-2026-8991',  'NIC-882104', 'Forensic Examiner', '2026-02-21T10:00:00'),
            ('NIA-2026-1105', 'NIC-882104', 'Cyber Forensics',   '2026-03-05T14:00:00'),

            -- Adv. S. Iyer: CBI-0042 (Legal Prosecution)
            ('CBI-2026-0042', 'NIC-773219', 'Prosecutor',        '2026-01-18T16:00:00'),

            -- K. Swaminathan: All cases (Oversight / Compliance)
            ('CBI-2026-0042', 'NIC-110022', 'Compliance Auditor','2026-01-16T12:00:00'),
            ('DP-2026-8991',  'NIC-110022', 'Compliance Auditor','2026-02-22T09:00:00'),
            ('NIA-2026-1105', 'NIC-110022', 'Compliance Auditor','2026-03-06T11:00:00');
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ──────────────────────────────────────────
# DOCUMENT CLASSIFIER (keyword-based using sklearn TF-IDF if file text
# is available; falls back to filename rules for binary files)
# ──────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "Legal": [
        "fir", "chargesheet", "court", "affidavit", "warrant", "bail", "judgment",
        "petition", "advocate", "legal", "section", "ipc", "crpc", "law", "act",
        "evidence", "witness", "statement", "plaint", "complaint", "police",
        "seizure", "custody", "arrest", "accused", "prosecution"
    ],
    "Financial": [
        "bank", "account", "transaction", "invoice", "balance", "credit", "debit",
        "statement", "financial", "payment", "amount", "rupee", "inr", "usd",
        "transfer", "fund", "income", "tax", "gst", "audit", "fraud", "loan",
        "interest", "cheque", "ledger", "profit", "loss", "asset", "liability"
    ],
    "Identity": [
        "aadhaar", "aadhar", "passport", "pan", "voter", "identity", "id proof",
        "driving license", "birth certificate", "dob", "date of birth", "name",
        "address", "photograph", "biometric", "national id", "residence proof",
        "ration card", "uid", "kyc"
    ],
    "Educational": [
        "degree", "certificate", "university", "college", "school", "marksheet",
        "transcript", "education", "qualification", "exam", "result", "grade",
        "academic", "course", "diploma", "graduation", "student", "roll number"
    ],
    "Business": [
        "company", "corporate", "incorporation", "moa", "aoa", "director",
        "shareholder", "equity", "business", "firm", "partnership", "contract",
        "agreement", "mou", "tender", "procurement", "vendor", "gst number",
        "cin", "roc", "trademark", "patent", "license"
    ],
    "Confidential": [
        "secret", "classified", "confidential", "sensitive", "restricted",
        "top secret", "internal", "surveillance", "intelligence", "nsa",
        "encrypted", "cbi", "ib", "raw", "operation", "undercover", "covert",
        "espionage", "cyber", "threat", "investigation", "suspect"
    ],
}

FILENAME_RULES = {
    r"(fir|chargesheet|warrant|seizure|affidavit|witness|statement)": "Legal",
    r"(bank|statement|invoice|transaction|financial|fraud|ledger|tax|gst)": "Financial",
    r"(aadhaar|aadhar|passport|pan|voter|kyc|id_proof|identity)": "Identity",
    r"(degree|marksheet|certificate|transcript|university|college)": "Educational",
    r"(moa|aoa|company|corporate|contract|agreement|mou|tender)": "Business",
    r"(secret|confidential|classified|intelligence|operation|covert|espionage|cyber)": "Confidential",
}


def classify_text(text: str, filename: str) -> tuple[str, float, str]:
    """Returns (category, confidence 0-1, method_used)"""
    text_lower = text.lower() if text else ""
    filename_lower = filename.lower()

    scores = {}
    if text_lower.strip():
        # Score each category by keyword hits
        words = re.findall(r"\b\w+\b", text_lower)
        word_set = set(words)
        for category, keywords in CATEGORY_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text_lower or kw in word_set)
            scores[category] = hits

        if scores:
            best_cat = max(scores, key=scores.get)
            best_score = scores[best_cat]
            total = sum(scores.values()) or 1
            confidence = min(best_score / total, 1.0) if best_score > 0 else 0.0

            if best_score >= 2:
                return best_cat, round(confidence, 2), "content-analysis"

    # Fallback: filename pattern match
    for pattern, category in FILENAME_RULES.items():
        if re.search(pattern, filename_lower):
            return category, 0.70, "filename-match"

    return "Other", 0.50, "default"


def read_file_text(file_bytes: bytes, filename: str) -> str:
    """Try to extract readable text from file bytes."""
    fname = filename.lower()
    # Plain text files
    if any(fname.endswith(ext) for ext in [".txt", ".csv", ".log", ".md", ".json", ".xml"]):
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    # PDF: look for readable strings (simple heuristic, no pdfminer)
    if fname.endswith(".pdf"):
        try:
            raw = file_bytes.decode("latin-1", errors="ignore")
            # Extract printable ASCII runs of 4+ chars
            chunks = re.findall(r"[A-Za-z0-9 ,.\-:;/\(\)]{4,}", raw)
            return " ".join(chunks[:200])
        except Exception:
            return ""
    # Fallback for .doc/.docx/.odt etc: extract printable chars
    try:
        raw = file_bytes.decode("latin-1", errors="ignore")
        chunks = re.findall(r"[A-Za-z0-9 ,.\-:;/]{4,}", raw)
        return " ".join(chunks[:200])
    except Exception:
        return ""


# ──────────────────────────────────────────
# AUDIT CHAIN
# ──────────────────────────────────────────
_audit_lock = threading.Lock()

def append_audit(actor_id: str, action: str, resource_id: str, outcome: str):
    with _audit_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        row = c.execute("SELECT entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
        prev_hash = row[0] if row else "0" * 64
        logged_at = datetime.utcnow().isoformat()
        payload = json.dumps({
            "prev": prev_hash, "actor": actor_id, "action": action,
            "resource": resource_id, "outcome": outcome, "ts": logged_at
        }, sort_keys=True)
        entry_hash = hashlib.sha256(payload.encode()).hexdigest()
        c.execute("""INSERT INTO audit_log
                     (prev_hash, entry_hash, actor_id, action, resource_id, outcome, logged_at)
                     VALUES (?,?,?,?,?,?,?)""",
                  (prev_hash, entry_hash, actor_id, action, resource_id, outcome, logged_at))
        conn.commit()
        conn.close()


# ──────────────────────────────────────────
# HTTP SERVER
# ──────────────────────────────────────────
def parse_multipart(body: bytes, boundary: bytes):
    """Simple multipart/form-data parser."""
    parts = {}
    delimiter = b"--" + boundary
    segments = body.split(delimiter)
    for seg in segments:
        if b"Content-Disposition" not in seg:
            continue
        header_end = seg.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        header_raw = seg[:header_end].decode("utf-8", errors="ignore")
        value_raw = seg[header_end + 4:].rstrip(b"\r\n--")

        name_match = re.search(r'name="([^"]+)"', header_raw)
        filename_match = re.search(r'filename="([^"]+)"', header_raw)
        if name_match:
            field_name = name_match.group(1)
            if filename_match:
                parts[field_name] = {"filename": filename_match.group(1), "data": value_raw}
            else:
                parts[field_name] = value_raw.decode("utf-8", errors="ignore").strip()
    return parts


class DMSHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[HTTP] {self.address_string()} - {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Serve frontend web UI
        if path in ("/", "/index.html", "/app.html"):
            index_path = os.path.join(os.path.dirname(__file__), "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
                return

        # Serve Firebase configuration module
        if path == "/firebase-config.js":
            cfg_path = os.path.join(os.path.dirname(__file__), "firebase-config.js")
            if os.path.exists(cfg_path):
                with open(cfg_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
                return

        # Health check
        if path == "/api/health":
            return self.send_json({"status": "healthy", "db": DB_PATH})

        # List users
        if path == "/api/users":
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("""
                SELECT user_id, name, role, role_label, agency, initials, can_upload, can_reclassify
                FROM users ORDER BY rowid ASC
            """).fetchall()
            conn.close()
            return self.send_json([
                {
                    "user_id": r[0], "name": r[1], "role": r[2], "role_label": r[3],
                    "agency": r[4], "initials": r[5], "can_upload": bool(r[6]),
                    "can_reclassify": bool(r[7])
                } for r in rows
            ])

        # List cases (filtered by user if user_id param provided)
        if path == "/api/cases":
            user_id = qs.get("user_id", [None])[0]
            conn = sqlite3.connect(DB_PATH)
            if user_id:
                rows = conn.execute("""
                    SELECT c.case_id, c.title, c.created_at, ca.role_in_case
                    FROM cases c
                    INNER JOIN case_assignments ca ON c.case_id = ca.case_id
                    WHERE ca.user_id = ?
                    ORDER BY c.created_at DESC
                """, (user_id,)).fetchall()
            else:
                rows = conn.execute("SELECT case_id, title, created_at, 'Public' FROM cases ORDER BY created_at DESC").fetchall()
            conn.close()
            return self.send_json([
                {"case_id": r[0], "title": r[1], "created_at": r[2], "role_in_case": r[3]}
                for r in rows
            ])

        # List documents for a case
        if path == "/api/documents":
            case_id = qs.get("case_id", [None])[0]
            user_id = qs.get("user_id", ["NIC-994321"])[0]
            if not case_id:
                return self.send_json({"error": "case_id required"}, 400)
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("""
                SELECT id, filename, file_size, doc_type, is_evidence,
                       sha256_hash, classification, class_confidence, class_status, uploaded_at, uploader_id
                FROM documents WHERE case_id=? ORDER BY id DESC
            """, (case_id,)).fetchall()
            conn.close()
            docs = []
            for r in rows:
                docs.append({
                    "id": r[0], "name": r[1], "size": r[2], "type": r[3],
                    "evidence": bool(r[4]), "hash": r[5],
                    "classification": r[6], "confidence": r[7],
                    "class_status": r[8], "date": r[9], "uploader": r[10]
                })
            append_audit(user_id, "LIST_DOCUMENTS", case_id, "OK")
            return self.send_json(docs)

        # Audit log
        if path == "/api/audit":
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute("""
                SELECT seq, actor_id, action, resource_id, outcome, logged_at, entry_hash
                FROM audit_log ORDER BY seq DESC LIMIT 50
            """).fetchall()
            conn.close()
            return self.send_json([
                {"seq": r[0], "actor": r[1], "action": r[2],
                 "resource": r[3], "outcome": r[4], "ts": r[5], "hash": r[6]}
                for r in rows
            ])

        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Upload document
        if path == "/api/documents/upload":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            content_type = self.headers.get("Content-Type", "")

            if "multipart/form-data" not in content_type:
                return self.send_json({"error": "multipart expected"}, 400)

            boundary_match = re.search(r"boundary=(.+)", content_type)
            if not boundary_match:
                return self.send_json({"error": "no boundary"}, 400)

            boundary = boundary_match.group(1).strip().encode()
            parts = parse_multipart(body, boundary)

            file_part = parts.get("file")
            if not file_part or not isinstance(file_part, dict):
                return self.send_json({"error": "no file uploaded"}, 400)

            file_bytes = file_part["data"]
            filename = file_part["filename"]
            case_id = parts.get("case_id", "CBI-2026-0042")
            uploader_id = parts.get("uploader_id", "NIC-994321")
            doc_type = parts.get("doc_type", "OTHER")
            is_evidence = parts.get("is_evidence", "false").lower() in ("true", "1", "on")
            seizure_date = parts.get("seizure_date", "")
            seizure_location = parts.get("seizure_location", "")

            # Security: compute hash of raw bytes
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            file_size_kb = len(file_bytes) / 1024
            file_size_str = f"{file_size_kb:.1f} KB" if file_size_kb < 1024 else f"{file_size_kb/1024:.1f} MB"

            # Classify based on content
            extracted_text = read_file_text(file_bytes, filename)
            category, confidence, method = classify_text(extracted_text, filename)

            # Persist to DB
            uploaded_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO documents
                (case_id, filename, file_size, doc_type, is_evidence,
                 seizure_date, seizure_location, sha256_hash,
                 classification, class_confidence, class_status, uploaded_at, uploader_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (case_id, filename, file_size_str, doc_type, int(is_evidence),
                  seizure_date, seizure_location, sha256_hash,
                  category, confidence, "auto", uploaded_at, uploader_id))
            doc_id = c.lastrowid
            conn.commit()
            conn.close()

            append_audit(uploader_id, "UPLOAD_DOCUMENT", f"{case_id}/{filename}", "OK")

            return self.send_json({
                "success": True,
                "id": doc_id,
                "filename": filename,
                "sha256": sha256_hash,
                "size": file_size_str,
                "classification": category,
                "confidence": confidence,
                "method": method,
                "uploaded_at": uploaded_at
            })

        self.send_json({"error": "not found"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        # PUT /api/documents/{id}/classification
        m = re.match(r"/api/documents/(\d+)/classification", parsed.path)
        if m:
            doc_id = int(m.group(1))
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except Exception:
                return self.send_json({"error": "invalid JSON"}, 400)

            new_cat = data.get("classification", "Other")
            valid_cats = {"Legal", "Financial", "Identity", "Educational", "Business", "Confidential", "Other"}
            if new_cat not in valid_cats:
                return self.send_json({"error": "invalid category"}, 400)

            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                UPDATE documents SET classification=?, class_status='manual', class_confidence=1.0
                WHERE id=?
            """, (new_cat, doc_id))
            conn.commit()
            conn.close()

            actor_id = data.get("actor_id", "NIC-994321")
            append_audit(actor_id, "RECLASSIFY_DOCUMENT", str(doc_id), new_cat)
            return self.send_json({"success": True, "id": doc_id, "classification": new_cat, "class_status": "manual"})

        self.send_json({"error": "not found"}, 404)


def run_server(port=8765):
    init_db()
    server = HTTPServer(("0.0.0.0", port), DMSHandler)
    print(f"[SERVER] DMS Backend running at http://localhost:{port}")
    print(f"[SERVER] API endpoints:")
    print(f"         GET  /api/health")
    print(f"         GET  /api/cases")
    print(f"         GET  /api/documents?case_id=CBI-2026-0042")
    print(f"         POST /api/documents/upload  (multipart/form-data)")
    print(f"         PUT  /api/documents/{{id}}/classification")
    print(f"         GET  /api/audit")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
