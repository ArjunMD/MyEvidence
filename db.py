# db.py

import os
import re
import sqlite3
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

DB_PATH = "data/papers.db"
GUIDELINES_DIR = "data/guidelines"
GUIDELINES_MD_DIR = "data/guidelines_md"

# ---------------- Local DB paths / connection ----------------

def _db_path() -> str:
    return DB_PATH


def _guidelines_dir() -> str:
    return GUIDELINES_DIR


def _guidelines_md_dir() -> str:
    return GUIDELINES_MD_DIR

def _connect_db() -> sqlite3.Connection:
    path = _db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# ---------------- Abstracts schema + CRUD ----------------

def ensure_schema() -> None:
    with _connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS abstracts (
                pmid TEXT PRIMARY KEY,
                title TEXT,
                abstract TEXT NOT NULL,
                year TEXT,
                journal TEXT,
                patient_n INTEGER,
                study_design TEXT,
                patient_details TEXT,
                intervention_comparison TEXT,
                authors_conclusions TEXT,
                results TEXT,
                specialty TEXT
            );
            """
        )


def save_record(
    pmid: str,
    title: str,
    abstract: str,
    year: str,
    journal: str,
    patient_n: Optional[int],
    study_design: Optional[str],
    patient_details: Optional[str],
    intervention_comparison: Optional[str],
    authors_conclusions: Optional[str],
    results: Optional[str],
    specialty: Optional[str],
) -> None:
    with _connect_db() as conn:
        conn.execute(
            """
            INSERT INTO abstracts (
                pmid, title, abstract, year, journal, patient_n, study_design,
                patient_details, intervention_comparison, authors_conclusions, results,
                specialty
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                pmid,
                title,
                abstract,
                year,
                journal,
                patient_n,
                study_design,
                patient_details,
                intervention_comparison,
                authors_conclusions,
                results,
                specialty,
            ),
        )


def is_saved(pmid: str) -> bool:
    with _connect_db() as conn:
        row = conn.execute("SELECT 1 FROM abstracts WHERE pmid=? LIMIT 1;", (pmid,)).fetchone()
        return row is not None


def db_count() -> int:
    with _connect_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM abstracts;").fetchone()
        return int(row["c"]) if row else 0


def guidelines_count() -> int:
    # Safe even if the guidelines table doesn't exist yet.
    with _connect_db() as conn:
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM guidelines;").fetchone()
        except sqlite3.OperationalError:
            return 0
        return int(row["c"]) if row else 0


def db_count_all() -> int:
    # Count papers + guidelines in one connection.
    with _connect_db() as conn:
        row_p = conn.execute("SELECT COUNT(*) AS c FROM abstracts;").fetchone()
        papers = int(row_p["c"]) if row_p else 0

        try:
            row_g = conn.execute("SELECT COUNT(*) AS c FROM guidelines;").fetchone()
            guidelines = int(row_g["c"]) if row_g else 0
        except sqlite3.OperationalError:
            guidelines = 0

    return papers + guidelines

def search_records(limit: int, q: str) -> List[Dict[str, str]]:
    raw = (q or "").strip()
    if not raw:
        return []

    tokens = re.findall(r"[A-Za-z0-9]+", raw)
    if not tokens:
        return []

    cols = [
        "COALESCE(pmid,'')",
        "COALESCE(title,'')",
        "COALESCE(abstract,'')",
        "COALESCE(year,'')",
        "COALESCE(journal,'')",
        "COALESCE(study_design,'')",
        "COALESCE(patient_details,'')",
        "COALESCE(intervention_comparison,'')",
        "COALESCE(authors_conclusions,'')",
        "COALESCE(results,'')",
        "COALESCE(specialty,'')",
        "COALESCE(CAST(patient_n AS TEXT),'')",
    ]

    where_parts: List[str] = []
    params: List[str] = []
    for tok in tokens:
        like = f"%{tok}%"
        ors = " OR ".join([f"{c} LIKE ?" for c in cols])
        where_parts.append(f"({ors})")
        params.extend([like] * len(cols))

    where_sql = " AND ".join(where_parts)

    with _connect_db() as conn:
        rows = conn.execute(
            f"""
            SELECT pmid, title, year, journal, patient_n, study_design, specialty
            FROM abstracts
            WHERE {where_sql}
            ORDER BY
                CASE WHEN year GLOB '[0-9][0-9][0-9][0-9]' THEN year END DESC,
                title COLLATE NOCASE ASC
            LIMIT ?;
            """,
            (*params, int(limit)),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "pmid": (r["pmid"] or "").strip(),
                "title": (r["title"] or "").strip(),
                "year": (r["year"] or "").strip(),
                "journal": (r["journal"] or "").strip(),
                "patient_n": "" if r["patient_n"] is None else str(int(r["patient_n"])),
                "study_design": (r["study_design"] or "").strip(),
                "specialty": (r["specialty"] or "").strip(),
            }
        )
    return out


def list_browse_items(limit: int) -> List[Dict[str, str]]:
    with _connect_db() as conn:
        rows = conn.execute(
            """
            SELECT pmid, title, year, journal, patient_n, specialty, authors_conclusions
            FROM abstracts
            ORDER BY
                specialty COLLATE NOCASE ASC,
                CASE WHEN year GLOB '[0-9][0-9][0-9][0-9]' THEN year END DESC,
                title COLLATE NOCASE ASC
            LIMIT ?;
            """,
            (int(limit),),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "pmid": (r["pmid"] or "").strip(),
                "title": (r["title"] or "").strip(),
                "year": (r["year"] or "").strip(),
                "journal": (r["journal"] or "").strip(),
                "patient_n": str(r["patient_n"] or "").strip(),
                "specialty": (r["specialty"] or "").strip(),
                "authors_conclusions": (r["authors_conclusions"] or "").strip(),
            }
        )
    return out


def get_record(pmid: str) -> Dict[str, str]:
    with _connect_db() as conn:
        row = conn.execute(
            """
            SELECT pmid, title, abstract, year, journal, patient_n, study_design,
                   patient_details, intervention_comparison, authors_conclusions, results,
                   specialty
            FROM abstracts
            WHERE pmid=? LIMIT 1;
            """,
            (pmid,),
        ).fetchone()
        if not row:
            return {}
        return {
            "pmid": (row["pmid"] or "").strip(),
            "title": (row["title"] or "").strip(),
            "abstract": (row["abstract"] or "").strip(),
            "year": (row["year"] or "").strip(),
            "journal": (row["journal"] or "").strip(),
            "patient_n": "" if row["patient_n"] is None else str(int(row["patient_n"])),
            "study_design": (row["study_design"] or "").strip(),
            "patient_details": (row["patient_details"] or "").strip(),
            "intervention_comparison": (row["intervention_comparison"] or "").strip(),
            "authors_conclusions": (row["authors_conclusions"] or "").strip(),
            "results": (row["results"] or "").strip(),
            "specialty": (row["specialty"] or "").strip(),
        }


def delete_record(pmid: str) -> None:
    with _connect_db() as conn:
        conn.execute("DELETE FROM abstracts WHERE pmid=?;", (pmid,))


def list_recent_records(limit: int) -> List[Dict[str, str]]:
    with _connect_db() as conn:
        rows = conn.execute(
            """
            SELECT pmid, title, year, journal, patient_n, study_design, specialty
            FROM abstracts
            ORDER BY
                CASE WHEN year GLOB '[0-9][0-9][0-9][0-9]' THEN year END DESC,
                title COLLATE NOCASE ASC
            LIMIT ?;
            """,
            (int(limit),),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "pmid": (r["pmid"] or "").strip(),
                "title": (r["title"] or "").strip(),
                "year": (r["year"] or "").strip(),
                "journal": (r["journal"] or "").strip(),
                "patient_n": "" if r["patient_n"] is None else str(int(r["patient_n"])),
                "study_design": (r["study_design"] or "").strip(),
                "specialty": (r["specialty"] or "").strip(),
            }
        )
    return out


# ---------------- Guidelines storage + schema ----------------

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b or b"")
    return h.hexdigest()


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def ensure_guidelines_schema() -> None:
    with _connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guidelines (
                guideline_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,          -- kept for compatibility; always '' in ultra-minimal
                sha256 TEXT NOT NULL,
                bytes INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                guideline_name TEXT,
                pub_year TEXT,
                specialty TEXT,
                meta_extracted_at TEXT,
                recommendations_display_md TEXT,
                recommendations_display_updated_at TEXT
            );
            """
        )
        # Dedupe + browse/search helpers
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_guidelines_sha256_uq ON guidelines(sha256);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_guidelines_uploaded_at ON guidelines(uploaded_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_guidelines_pub_year ON guidelines(pub_year);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_guidelines_specialty ON guidelines(specialty);")


def find_guideline_by_hash(sha256: str) -> Optional[Dict[str, str]]:
    s = (sha256 or "").strip()
    if not s:
        return None
    with _connect_db() as conn:
        row = conn.execute(
            """
            SELECT guideline_id, filename, stored_path, sha256, bytes, uploaded_at,
                   guideline_name, pub_year, specialty, meta_extracted_at,
                   recommendations_display_md, recommendations_display_updated_at
            FROM guidelines
            WHERE sha256=?
            LIMIT 1;
            """,
            (s,),
        ).fetchone()
        if not row:
            return None
        return {
            "guideline_id": (row["guideline_id"] or "").strip(),
            "filename": (row["filename"] or "").strip(),
            "stored_path": (row["stored_path"] or "").strip(),
            "sha256": (row["sha256"] or "").strip(),
            "bytes": str(int(row["bytes"])) if row["bytes"] is not None else "0",
            "uploaded_at": (row["uploaded_at"] or "").strip(),
            "guideline_name": (row["guideline_name"] or "").strip(),
            "pub_year": (row["pub_year"] or "").strip(),
            "specialty": (row["specialty"] or "").strip(),
            "meta_extracted_at": (row["meta_extracted_at"] or "").strip(),
            "recommendations_display_md": (row["recommendations_display_md"] or "").strip(),
            "recommendations_display_updated_at": (row["recommendations_display_updated_at"] or "").strip(),
        }

def save_guideline_pdf(filename: str, pdf_bytes: bytes) -> Dict[str, str]:
    if not pdf_bytes:
        raise ValueError("Empty PDF bytes.")
    fn = (filename or "").strip() or "guideline.pdf"

    sha = _sha256_bytes(pdf_bytes)
    existing = find_guideline_by_hash(sha)
    if existing:
        return existing

    gid = uuid.uuid4().hex
    uploaded_at = _utc_iso_z()
    nbytes = int(len(pdf_bytes))

    # Ultra-minimal: never store PDF; keep stored_path as ''.
    with _connect_db() as conn:
        conn.execute(
            """
            INSERT INTO guidelines (guideline_id, filename, stored_path, sha256, bytes, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (gid, fn, "", sha, nbytes, uploaded_at),
        )

    return {
        "guideline_id": gid,
        "filename": fn,
        "stored_path": "",
        "sha256": sha,
        "bytes": str(nbytes),
        "uploaded_at": uploaded_at,
        "guideline_name": "",
        "pub_year": "",
        "specialty": "",
        "meta_extracted_at": "",
        "recommendations_display_md": "",
        "recommendations_display_updated_at": "",
    }


def list_guidelines(limit: int) -> List[Dict[str, str]]:
    with _connect_db() as conn:
        rows = conn.execute(
            """
            SELECT guideline_id, filename, stored_path, sha256, bytes, uploaded_at,
                   guideline_name, pub_year, specialty, meta_extracted_at
            FROM guidelines
            ORDER BY uploaded_at DESC
            LIMIT ?;
            """,
            (int(limit),),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "guideline_id": (r["guideline_id"] or "").strip(),
                "filename": (r["filename"] or "").strip(),
                "stored_path": (r["stored_path"] or "").strip(),
                "sha256": (r["sha256"] or "").strip(),
                "bytes": str(int(r["bytes"])) if r["bytes"] is not None else "0",
                "uploaded_at": (r["uploaded_at"] or "").strip(),
                "guideline_name": (r["guideline_name"] or "").strip(),
                "pub_year": (r["pub_year"] or "").strip(),
                "specialty": (r["specialty"] or "").strip(),
                "meta_extracted_at": (r["meta_extracted_at"] or "").strip(),
            }
        )
    return out


def read_guideline_pdf_bytes(guideline_id: str) -> bytes:
    gid = (guideline_id or "").strip()
    if not gid:
        return b""
    with _connect_db() as conn:
        row = conn.execute(
            "SELECT stored_path FROM guidelines WHERE guideline_id=? LIMIT 1;",
            (gid,),
        ).fetchone()
        if not row:
            return b""
        path = (row["stored_path"] or "").strip()
    if not path or not os.path.exists(path):
        return b""
    with open(path, "rb") as f:
        return f.read()


def delete_guideline(guideline_id: str) -> None:
    gid = (guideline_id or "").strip()
    if not gid:
        return
    with _connect_db() as conn:
        conn.execute("DELETE FROM guidelines WHERE guideline_id=?;", (gid,))


def purge_guideline_pdf(guideline_id: str) -> None:
    """
    Delete the stored PDF from disk (best-effort) and clear stored_path.
    Keeps extracted content + cached markdown in SQLite.
    """
    gid = (guideline_id or "").strip()
    if not gid:
        return

    stored_path = ""
    with _connect_db() as conn:
        row = conn.execute(
            "SELECT stored_path FROM guidelines WHERE guideline_id=? LIMIT 1;",
            (gid,),
        ).fetchone()
        if not row:
            return
        stored_path = (row["stored_path"] or "").strip()

        # Keep row, just clear the path (stored_path is NOT NULL, so use empty string)
        conn.execute(
            "UPDATE guidelines SET stored_path='' WHERE guideline_id=?;",
            (gid,),
        )

    # Best-effort remove stored PDF from disk (guarded to guidelines dir)
    try:
        if stored_path:
            gdir = os.path.abspath(_guidelines_dir())
            pabs = os.path.abspath(stored_path)
            if pabs.startswith(gdir + os.sep) and os.path.exists(pabs):
                os.remove(pabs)
    except Exception:
        pass


# ---------------- Guideline layout markdown cache ----------------

def get_guideline_meta(guideline_id: str) -> Dict[str, str]:
    gid = (guideline_id or "").strip()
    if not gid:
        return {}
    with _connect_db() as conn:
        row = conn.execute(
            """
            SELECT guideline_id, filename, sha256, stored_path, uploaded_at, bytes,
                   guideline_name, pub_year, specialty, meta_extracted_at
            FROM guidelines
            WHERE guideline_id=? LIMIT 1;
            """,
            (gid,),
        ).fetchone()
        if not row:
            return {}
        return {
            "guideline_id": (row["guideline_id"] or "").strip(),
            "filename": (row["filename"] or "").strip(),
            "sha256": (row["sha256"] or "").strip(),
            "stored_path": (row["stored_path"] or "").strip(),
            "uploaded_at": (row["uploaded_at"] or "").strip(),
            "bytes": str(int(row["bytes"])) if row["bytes"] is not None else "0",
            "guideline_name": (row["guideline_name"] or "").strip(),
            "pub_year": (row["pub_year"] or "").strip(),
            "specialty": (row["specialty"] or "").strip(),
            "meta_extracted_at": (row["meta_extracted_at"] or "").strip(),
        }


def get_guideline_recommendations_display(guideline_id: str) -> str:
    gid = (guideline_id or "").strip()
    if not gid:
        return ""
    with _connect_db() as conn:
        row = conn.execute(
            "SELECT recommendations_display_md FROM guidelines WHERE guideline_id=? LIMIT 1;",
            (gid,),
        ).fetchone()
        if not row:
            return ""
        return (row["recommendations_display_md"] or "").strip()


def update_guideline_recommendations_display(guideline_id: str, markdown: str) -> None:
    gid = (guideline_id or "").strip()
    if not gid:
        return
    md = (markdown or "").strip()
    now = _utc_iso_z()
    with _connect_db() as conn:
        conn.execute(
            """
            UPDATE guidelines
            SET recommendations_display_md=?, recommendations_display_updated_at=?
            WHERE guideline_id=?;
            """,
            (md, now, gid),
        )


def get_cached_layout_markdown(guideline_id: str, sha256: str) -> str:
    gid = (guideline_id or "").strip()
    sha = (sha256 or "").strip()
    if not gid or not sha:
        return ""
    with _connect_db() as conn:
        row = conn.execute(
            "SELECT markdown FROM guideline_layout WHERE guideline_id=? AND sha256=? LIMIT 1;",
            (gid, sha),
        ).fetchone()
        return (row["markdown"] or "") if row else ""


def save_layout_markdown(guideline_id: str, sha256: str, markdown: str) -> None:
    gid = (guideline_id or "").strip()
    sha = (sha256 or "").strip()
    md = (markdown or "").strip()
    if not gid or not sha or not md:
        return
    analyzed_at = _utc_iso_z()
    with _connect_db() as conn:
        conn.execute(
            """
            INSERT INTO guideline_layout (guideline_id, sha256, markdown, analyzed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guideline_id) DO UPDATE SET
                sha256=excluded.sha256,
                markdown=excluded.markdown,
                analyzed_at=excluded.analyzed_at;
            """,
            (gid, sha, md, analyzed_at),
        )

# ---------------- Guideline element + recommendation inserts (used by extract.py) ----------------

def _stable_guideline_element_id(guideline_id: str, idx: int, content_hash: str) -> str:
    """
    Deterministic ID so re-running extraction doesn't duplicate the same element.
    """
    gid = (guideline_id or "").strip()
    ch = (content_hash or "").strip()
    key = f"{gid}|{int(idx)}|{ch}".encode("utf-8", errors="ignore")
    return hashlib.sha256(key).hexdigest()


def insert_guideline_element(
    guideline_id: str,
    idx: int,
    kind: str,
    content: str,
    content_hash: str,
) -> None:
    """
    Best-effort store of parsed markdown elements for debugging/auditing extraction.
    Safe to call repeatedly; duplicates are ignored.
    """
    gid = (guideline_id or "").strip()
    if not gid:
        return

    k = (kind or "").strip() or "text"
    c = (content or "").strip()
    ch = (content_hash or "").strip()
    if not c or not ch:
        return

    element_id = _stable_guideline_element_id(gid, int(idx), ch)

    with _connect_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO guideline_elements (
                element_id, guideline_id, idx, kind, content, content_hash
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (element_id, gid, int(idx), k, c, ch),
        )


def _stable_guideline_rec_id(guideline_id: str, element_hash: str, recommendation_text: str) -> str:
    """
    Deterministic ID so re-running extraction doesn't duplicate the same recommendation.
    """
    gid = (guideline_id or "").strip()
    eh = (element_hash or "").strip()
    rt = (recommendation_text or "").strip().lower()
    key = f"{gid}|{eh}|{rt}".encode("utf-8", errors="ignore")
    return hashlib.sha256(key).hexdigest()


def insert_guideline_recommendation(
    guideline_id: str,
    idx: int,
    recommendation_text: str,
    strength_raw: Optional[str],
    evidence_raw: Optional[str],
    source_snippet: Optional[str],
    element_hash: str,
    created_at: str,
) -> None:
    """
    Insert a recommendation extracted from a candidate element.
    Safe to call repeatedly; duplicates are ignored.
    """
    gid = (guideline_id or "").strip()
    if not gid:
        return

    rec_text = (recommendation_text or "").strip()
    if not rec_text:
        return

    eh = (element_hash or "").strip()
    if not eh:
        return

    rid = _stable_guideline_rec_id(gid, eh, rec_text)

    with _connect_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO guideline_recommendations (
                rec_id,
                guideline_id,
                idx,
                recommendation_text,
                strength_raw,
                evidence_raw,
                source_snippet,
                element_hash,
                relevance_status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unreviewed', ?, NULL);
            """,
            (
                rid,
                gid,
                int(idx),
                rec_text,
                (strength_raw or "").strip() or None,
                (evidence_raw or "").strip() or None,
                (source_snippet or "").strip() or None,
                eh,
                (created_at or "").strip() or _utc_iso_z(),
            ),
        )


# ---------------- Guideline recommendations + review state ----------------

def list_guideline_recommendations(guideline_id: str, limit: int = 2000) -> List[Dict[str, str]]:
    gid = (guideline_id or "").strip()
    if not gid:
        return []
    with _connect_db() as conn:
        rows = conn.execute(
            """
            SELECT rec_id, idx, recommendation_text, strength_raw, evidence_raw,
                   source_snippet, relevance_status, created_at, updated_at
            FROM guideline_recommendations
            WHERE guideline_id=?
            ORDER BY idx ASC
            LIMIT ?;
            """,
            (gid, int(limit)),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "rec_id": (r["rec_id"] or "").strip(),
                "idx": str(int(r["idx"])) if r["idx"] is not None else "0",
                "recommendation_text": (r["recommendation_text"] or "").strip(),
                "strength_raw": (r["strength_raw"] or "").strip(),
                "evidence_raw": (r["evidence_raw"] or "").strip(),
                "source_snippet": (r["source_snippet"] or "").strip(),
                "relevance_status": (r["relevance_status"] or "").strip(),
                "created_at": (r["created_at"] or "").strip(),
                "updated_at": (r["updated_at"] or "").strip(),
            }
        )
    return out


def update_guideline_metadata(
    guideline_id: str,
    guideline_name: Optional[str],
    pub_year: Optional[str],
    specialty: Optional[str],
) -> None:
    gid = (guideline_id or "").strip()
    if not gid:
        return
    now = _utc_iso_z()

    name = (guideline_name or "").strip() or None
    year = (pub_year or "").strip() or None
    spec = (specialty or "").strip() or None

    with _connect_db() as conn:
        conn.execute(
            """
            UPDATE guidelines
            SET guideline_name=?, pub_year=?, specialty=?, meta_extracted_at=?
            WHERE guideline_id=?;
            """,
            (name, year, spec, now, gid),
        )


# ---------------- Guideline browse/search ----------------

def list_browse_guideline_items(limit: int) -> List[Dict[str, str]]:
    with _connect_db() as conn:
        rows = conn.execute(
            """
            SELECT
                guideline_id,
                COALESCE(NULLIF(guideline_name,''), filename) AS title,
                COALESCE(pub_year,'') AS year,
                COALESCE(specialty,'') AS specialty
            FROM guidelines
            ORDER BY
                specialty COLLATE NOCASE ASC,
                CASE WHEN pub_year GLOB '[0-9][0-9][0-9][0-9]' THEN pub_year END DESC,
                title COLLATE NOCASE ASC
            LIMIT ?;
            """,
            (int(limit),),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "type": "guideline",
                "guideline_id": (r["guideline_id"] or "").strip(),
                "title": (r["title"] or "").strip(),
                "year": (r["year"] or "").strip(),
                "specialty": (r["specialty"] or "").strip(),
            }
        )
    return out

def search_guidelines(limit: int, q: str) -> List[Dict[str, str]]:
    raw = (q or "").strip()
    if not raw:
        return []

    tokens = re.findall(r"[A-Za-z0-9]+", raw)
    if not tokens:
        return []

    gcols = [
        "COALESCE(g.guideline_name,'')",
        "COALESCE(g.filename,'')",
        "COALESCE(g.pub_year,'')",
        "COALESCE(g.specialty,'')",
        "COALESCE(g.recommendations_display_md,'')",
    ]

    where_parts: List[str] = []
    params: List[str] = []
    for tok in tokens:
        like = f"%{tok}%"
        ors = " OR ".join([f"{c} LIKE ?" for c in gcols])
        where_parts.append(f"({ors})")
        params.extend([like] * len(gcols))

    where_sql = " AND ".join(where_parts)

    with _connect_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
                g.guideline_id,
                COALESCE(NULLIF(g.guideline_name,''), g.filename) AS title,
                COALESCE(g.pub_year,'') AS year,
                COALESCE(g.specialty,'') AS specialty
            FROM guidelines g
            WHERE {where_sql}
            ORDER BY
                CASE WHEN g.pub_year GLOB '[0-9][0-9][0-9][0-9]' THEN g.pub_year END DESC,
                title COLLATE NOCASE ASC
            LIMIT ?;
            """,
            (*params, int(limit)),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "type": "guideline",
                "guideline_id": (r["guideline_id"] or "").strip(),
                "title": (r["title"] or "").strip(),
                "year": (r["year"] or "").strip(),
                "specialty": (r["specialty"] or "").strip(),
            }
        )
    return out
