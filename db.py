# db.py

import os
import re
import sqlite3
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

DB_PATH = "data/papers.db"

# ---------------- Local DB paths / connection ----------------

def _db_path() -> str:
    return DB_PATH

def _connect_db() -> sqlite3.Connection:
    path = _db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _dedupe_nonempty(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in (values or []):
        v = str(raw or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


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
                pub_month TEXT,
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
        # Migration: add uploaded_at for History page (existing rows get NULL)
        try:
            conn.execute("ALTER TABLE abstracts ADD COLUMN uploaded_at TEXT;")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE abstracts ADD COLUMN pub_month TEXT;")
        except sqlite3.OperationalError:
            pass

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hidden_pubmed_pmids (
                pmid TEXT PRIMARY KEY,
                hidden_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS search_pubmed_ledger (
                year_month TEXT NOT NULL,
                specialty_label TEXT NOT NULL DEFAULT '',
                journal_label TEXT NOT NULL,
                study_type_label TEXT NOT NULL,
                total_matches INTEGER NOT NULL,
                visible_matches INTEGER NOT NULL,
                hidden_matches INTEGER NOT NULL,
                is_cleared INTEGER NOT NULL,
                is_verified INTEGER NOT NULL,
                last_checked_at TEXT NOT NULL,
                PRIMARY KEY (year_month, journal_label, study_type_label)
            );
            """
        )
        try:
            conn.execute("ALTER TABLE search_pubmed_ledger ADD COLUMN specialty_label TEXT NOT NULL DEFAULT '';")
        except sqlite3.OperationalError:
            pass
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_search_pubmed_ledger_checked
            ON search_pubmed_ledger(last_checked_at DESC);
            """
        )
    ensure_folders_schema()
    ensure_evidence_cart_schema()


def save_record(
    pmid: str,
    title: str,
    abstract: str,
    year: str,
    pub_month: str,
    journal: str,
    patient_n: Optional[int],
    study_design: Optional[str],
    patient_details: Optional[str],
    intervention_comparison: Optional[str],
    authors_conclusions: Optional[str],
    results: Optional[str],
    specialty: Optional[str],
) -> None:
    uploaded_at = _utc_iso_z()
    with _connect_db() as conn:
        conn.execute(
            """
            INSERT INTO abstracts (
                pmid, title, abstract, year, pub_month, journal, patient_n, study_design,
                patient_details, intervention_comparison, authors_conclusions, results,
                specialty, uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                pmid,
                title,
                abstract,
                year,
                pub_month,
                journal,
                patient_n,
                study_design,
                patient_details,
                intervention_comparison,
                authors_conclusions,
                results,
                specialty,
                uploaded_at,
            ),
        )


def is_saved(pmid: str) -> bool:
    with _connect_db() as conn:
        row = conn.execute("SELECT 1 FROM abstracts WHERE pmid=? LIMIT 1;", (pmid,)).fetchone()
        return row is not None


def get_saved_pmids(pmids: List[str]) -> Set[str]:
    vals: List[str] = []
    seen = set()
    for raw in (pmids or []):
        p = str(raw or "").strip()
        if not p or p in seen:
            continue
        seen.add(p)
        vals.append(p)
    if not vals:
        return set()

    placeholders = ",".join(["?"] * len(vals))
    with _connect_db() as conn:
        rows = conn.execute(
            f"SELECT pmid FROM abstracts WHERE pmid IN ({placeholders});",
            tuple(vals),
        ).fetchall()
    return {(r["pmid"] or "").strip() for r in rows if (r["pmid"] or "").strip()}


def hide_pubmed_pmid(pmid: str) -> None:
    p = (pmid or "").strip()
    if not p:
        return
    with _connect_db() as conn:
        conn.execute(
            """
            INSERT INTO hidden_pubmed_pmids (pmid, hidden_at)
            VALUES (?, ?)
            ON CONFLICT(pmid) DO NOTHING;
            """,
            (p, _utc_iso_z()),
        )


def get_hidden_pubmed_pmids(pmids: List[str]) -> Set[str]:
    vals: List[str] = []
    seen = set()
    for raw in (pmids or []):
        p = str(raw or "").strip()
        if not p or p in seen:
            continue
        seen.add(p)
        vals.append(p)
    if not vals:
        return set()

    placeholders = ",".join(["?"] * len(vals))
    with _connect_db() as conn:
        rows = conn.execute(
            f"SELECT pmid FROM hidden_pubmed_pmids WHERE pmid IN ({placeholders});",
            tuple(vals),
        ).fetchall()
    return {(r["pmid"] or "").strip() for r in rows if (r["pmid"] or "").strip()}


def upsert_search_pubmed_ledger(
    year_month: str,
    specialty_label: str,
    journal_label: str,
    study_type_label: str,
    total_matches: int,
    visible_matches: int,
    hidden_matches: int,
    is_cleared: bool,
    is_verified: bool,
) -> None:
    ym = (year_month or "").strip()
    spec = (specialty_label or "").strip()
    jl = (journal_label or "").strip()
    stype = (study_type_label or "").strip()
    if not ym or not jl or not stype:
        return

    total_i = max(0, int(total_matches or 0))
    visible_i = max(0, int(visible_matches or 0))
    hidden_i = max(0, int(hidden_matches or 0))
    now = _utc_iso_z()

    with _connect_db() as conn:
        conn.execute(
            """
            INSERT INTO search_pubmed_ledger (
                year_month, specialty_label, journal_label, study_type_label,
                total_matches, visible_matches, hidden_matches,
                is_cleared, is_verified, last_checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(year_month, journal_label, study_type_label) DO UPDATE SET
                specialty_label=excluded.specialty_label,
                total_matches=excluded.total_matches,
                visible_matches=excluded.visible_matches,
                hidden_matches=excluded.hidden_matches,
                is_cleared=excluded.is_cleared,
                is_verified=excluded.is_verified,
                last_checked_at=excluded.last_checked_at;
            """,
            (
                ym,
                spec,
                jl,
                stype,
                total_i,
                visible_i,
                hidden_i,
                1 if bool(is_cleared) else 0,
                1 if bool(is_verified) else 0,
                now,
            ),
        )


def list_search_pubmed_ledger(limit: Optional[int] = None) -> List[Dict[str, str]]:
    with _connect_db() as conn:
        query = """
            SELECT
                year_month,
                specialty_label,
                journal_label,
                study_type_label,
                total_matches,
                visible_matches,
                hidden_matches,
                is_cleared,
                is_verified,
                last_checked_at
            FROM search_pubmed_ledger
            ORDER BY
                specialty_label COLLATE NOCASE ASC,
                journal_label COLLATE NOCASE ASC,
                study_type_label COLLATE NOCASE ASC,
                CAST(SUBSTR(year_month, 1, 4) AS INTEGER) DESC,
                CAST(SUBSTR(year_month, 6, 2) AS INTEGER) ASC
        """
        params: Tuple[object, ...] = ()
        try:
            lim = int(limit) if limit is not None else 0
        except Exception:
            lim = 0
        if lim > 0:
            query += "\n            LIMIT ?"
            params = (lim,)
        query += ";"
        rows = conn.execute(query, params).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "year_month": (r["year_month"] or "").strip(),
                "specialty_label": (r["specialty_label"] or "").strip(),
                "journal_label": (r["journal_label"] or "").strip(),
                "study_type_label": (r["study_type_label"] or "").strip(),
                "total_matches": str(int(r["total_matches"] or 0)),
                "visible_matches": str(int(r["visible_matches"] or 0)),
                "hidden_matches": str(int(r["hidden_matches"] or 0)),
                "is_cleared": "1" if int(r["is_cleared"] or 0) == 1 else "0",
                "is_verified": "1" if int(r["is_verified"] or 0) == 1 else "0",
                "last_checked_at": (r["last_checked_at"] or "").strip(),
            }
        )
    return out


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


def _parse_search_query_groups(raw: str) -> List[List[str]]:
    """
    Parse a free-text query into OR-groups of AND-terms.
    Supported syntax:
    - AND / OR operators (case-insensitive)
    - quoted phrases for exact substring terms
    - implicit AND between adjacent terms
    """
    s = (raw or "").strip()
    if not s:
        return []

    lex: List[Tuple[str, str]] = []
    for m in re.finditer(r'"([^"]+)"|(\S+)', s):
        phrase = m.group(1)
        token = m.group(2)

        if phrase is not None:
            t = re.sub(r"\s+", " ", phrase).strip()
            if t:
                lex.append(("TERM", t))
            continue

        w = (token or "").strip()
        if not w:
            continue
        if re.fullmatch(r"(?i)and|or", w):
            lex.append(("OP", w.upper()))
            continue

        # Keep legacy behavior for unquoted text: split punctuation into terms.
        parts = re.findall(r"[A-Za-z0-9]+", w)
        for p in parts:
            t = (p or "").strip()
            if t:
                lex.append(("TERM", t))

    if not lex:
        return []

    groups: List[List[str]] = []
    current: List[str] = []
    pending_op = "AND"
    for kind, val in lex:
        if kind == "OP":
            pending_op = val
            continue

        if not current:
            current = [val]
        elif pending_op == "OR":
            groups.append(current)
            current = [val]
        else:
            current.append(val)
        pending_op = "AND"

    if current:
        groups.append(current)

    cleaned: List[List[str]] = []
    for g in groups:
        seen = set()
        out: List[str] = []
        for raw_t in g:
            t = (raw_t or "").strip()
            if not t:
                continue
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
        if out:
            cleaned.append(out)
    return cleaned


def _build_search_where_sql(groups: List[List[str]], cols: List[str]) -> Tuple[str, List[str]]:
    where_parts: List[str] = []
    params: List[str] = []

    for group in (groups or []):
        and_parts: List[str] = []
        for term in (group or []):
            like = f"%{term}%"
            ors = " OR ".join([f"{c} LIKE ?" for c in cols])
            and_parts.append(f"({ors})")
            params.extend([like] * len(cols))
        if and_parts:
            where_parts.append("(" + " AND ".join(and_parts) + ")")

    return " OR ".join(where_parts), params

def search_records(limit: int, q: str) -> List[Dict[str, str]]:
    raw = (q or "").strip()
    if not raw:
        return []

    groups = _parse_search_query_groups(raw)
    if not groups:
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

    where_sql, params = _build_search_where_sql(groups, cols)
    if not where_sql:
        return []

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
            SELECT pmid, title, year, pub_month, journal, patient_n, specialty, authors_conclusions
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
                "pub_month": (r["pub_month"] or "").strip(),
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
            SELECT pmid, title, abstract, year, pub_month, journal, patient_n, study_design,
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
            "pub_month": (row["pub_month"] or "").strip(),
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
        try:
            conn.execute("DELETE FROM folder_papers WHERE pmid=?;", (pmid,))
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("DELETE FROM evidence_cart_items WHERE item_type='paper' AND item_id=?;", (pmid,))
        except sqlite3.OperationalError:
            pass


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


def list_abstracts_for_history(limit: int) -> List[Dict[str, str]]:
    """Return abstracts with uploaded_at, newest first (NULL uploaded_at last)."""
    with _connect_db() as conn:
        try:
            rows = conn.execute(
                """
                SELECT pmid, title, year, uploaded_at
                FROM abstracts
                ORDER BY uploaded_at DESC, pmid DESC
                LIMIT ?;
                """,
                (int(limit),),
            ).fetchall()
        except sqlite3.OperationalError:
            # uploaded_at column might not exist on very old DBs
            rows = conn.execute(
                """
                SELECT pmid, title, year, NULL AS uploaded_at
                FROM abstracts
                ORDER BY pmid DESC
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
                "uploaded_at": (r["uploaded_at"] or "").strip() if r["uploaded_at"] else "",
            }
        )
    return out


# ---------------- Folders ----------------

def ensure_folders_schema() -> None:
    with _connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS folders (
                folder_id TEXT PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS folder_papers (
                folder_id TEXT NOT NULL,
                pmid TEXT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (folder_id, pmid)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS folder_guidelines (
                folder_id TEXT NOT NULL,
                guideline_id TEXT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (folder_id, guideline_id)
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_folder_papers_folder
            ON folder_papers(folder_id);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_folder_guidelines_folder
            ON folder_guidelines(folder_id);
            """
        )


def list_folders(limit: int = 500) -> List[Dict[str, str]]:
    ensure_folders_schema()
    with _connect_db() as conn:
        rows = conn.execute(
            """
            SELECT
                f.folder_id,
                f.name,
                f.created_at,
                f.updated_at,
                COALESCE(fp.paper_count, 0) AS paper_count,
                COALESCE(fg.guideline_count, 0) AS guideline_count
            FROM folders f
            LEFT JOIN (
                SELECT folder_id, COUNT(*) AS paper_count
                FROM folder_papers
                GROUP BY folder_id
            ) fp
                ON fp.folder_id = f.folder_id
            LEFT JOIN (
                SELECT folder_id, COUNT(*) AS guideline_count
                FROM folder_guidelines
                GROUP BY folder_id
            ) fg
                ON fg.folder_id = f.folder_id
            ORDER BY f.name COLLATE NOCASE ASC
            LIMIT ?;
            """,
            (max(1, int(limit or 500)),),
        ).fetchall()

    out: List[Dict[str, str]] = []
    for r in rows:
        paper_count = int(r["paper_count"] or 0)
        guideline_count = int(r["guideline_count"] or 0)
        out.append(
            {
                "folder_id": (r["folder_id"] or "").strip(),
                "name": (r["name"] or "").strip(),
                "created_at": (r["created_at"] or "").strip(),
                "updated_at": (r["updated_at"] or "").strip(),
                "paper_count": str(paper_count),
                "guideline_count": str(guideline_count),
                "total_count": str(paper_count + guideline_count),
            }
        )
    return out


def create_or_get_folder(name: str) -> Dict[str, str]:
    ensure_folders_schema()
    clean_name = re.sub(r"\s+", " ", (name or "").strip())
    if not clean_name:
        return {}

    with _connect_db() as conn:
        row = conn.execute(
            "SELECT folder_id, name FROM folders WHERE name = ? COLLATE NOCASE LIMIT 1;",
            (clean_name,),
        ).fetchone()
        if row:
            return {
                "folder_id": (row["folder_id"] or "").strip(),
                "name": (row["name"] or "").strip(),
                "created": "0",
            }

        now = _utc_iso_z()
        folder_id = uuid.uuid4().hex
        try:
            conn.execute(
                """
                INSERT INTO folders (folder_id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?);
                """,
                (folder_id, clean_name, now, now),
            )
            return {"folder_id": folder_id, "name": clean_name, "created": "1"}
        except sqlite3.IntegrityError:
            row = conn.execute(
                "SELECT folder_id, name FROM folders WHERE name = ? COLLATE NOCASE LIMIT 1;",
                (clean_name,),
            ).fetchone()
            if row:
                return {
                    "folder_id": (row["folder_id"] or "").strip(),
                    "name": (row["name"] or "").strip(),
                    "created": "0",
                }
    return {}


def add_items_to_folder(folder_id: str, pmids: List[str], guideline_ids: List[str]) -> Dict[str, str]:
    ensure_folders_schema()
    fid = (folder_id or "").strip()
    if not fid:
        return {"papers_added": "0", "guidelines_added": "0", "total_added": "0"}

    clean_pmids = _dedupe_nonempty(pmids)
    clean_gids = _dedupe_nonempty(guideline_ids)
    if not clean_pmids and not clean_gids:
        return {"papers_added": "0", "guidelines_added": "0", "total_added": "0"}

    now = _utc_iso_z()
    papers_added = 0
    guidelines_added = 0

    with _connect_db() as conn:
        row = conn.execute("SELECT 1 FROM folders WHERE folder_id=? LIMIT 1;", (fid,)).fetchone()
        if not row:
            return {"papers_added": "0", "guidelines_added": "0", "total_added": "0"}

        for pmid in clean_pmids:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO folder_papers (folder_id, pmid, added_at)
                VALUES (?, ?, ?);
                """,
                (fid, pmid, now),
            )
            papers_added += int(cur.rowcount or 0)

        for gid in clean_gids:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO folder_guidelines (folder_id, guideline_id, added_at)
                VALUES (?, ?, ?);
                """,
                (fid, gid, now),
            )
            guidelines_added += int(cur.rowcount or 0)

        if papers_added > 0 or guidelines_added > 0:
            conn.execute("UPDATE folders SET updated_at=? WHERE folder_id=?;", (now, fid))

    return {
        "papers_added": str(papers_added),
        "guidelines_added": str(guidelines_added),
        "total_added": str(papers_added + guidelines_added),
    }


def get_folder_item_ids(folder_id: str) -> Dict[str, List[str]]:
    ensure_folders_schema()
    fid = (folder_id or "").strip()
    if not fid:
        return {"pmids": [], "guideline_ids": []}

    with _connect_db() as conn:
        paper_rows = conn.execute(
            """
            SELECT pmid
            FROM folder_papers
            WHERE folder_id=?
            ORDER BY added_at DESC, pmid ASC;
            """,
            (fid,),
        ).fetchall()
        guideline_rows = conn.execute(
            """
            SELECT guideline_id
            FROM folder_guidelines
            WHERE folder_id=?
            ORDER BY added_at DESC, guideline_id ASC;
            """,
            (fid,),
        ).fetchall()

    pmids = _dedupe_nonempty([(r["pmid"] or "").strip() for r in paper_rows])
    gids = _dedupe_nonempty([(r["guideline_id"] or "").strip() for r in guideline_rows])
    return {"pmids": pmids, "guideline_ids": gids}


def remove_items_from_folder(folder_id: str, pmids: List[str], guideline_ids: List[str]) -> Dict[str, str]:
    ensure_folders_schema()
    fid = (folder_id or "").strip()
    if not fid:
        return {"papers_removed": "0", "guidelines_removed": "0", "total_removed": "0"}

    clean_pmids = _dedupe_nonempty(pmids)
    clean_gids = _dedupe_nonempty(guideline_ids)
    if not clean_pmids and not clean_gids:
        return {"papers_removed": "0", "guidelines_removed": "0", "total_removed": "0"}

    papers_removed = 0
    guidelines_removed = 0

    with _connect_db() as conn:
        row = conn.execute("SELECT 1 FROM folders WHERE folder_id=? LIMIT 1;", (fid,)).fetchone()
        if not row:
            return {"papers_removed": "0", "guidelines_removed": "0", "total_removed": "0"}

        for pmid in clean_pmids:
            cur = conn.execute(
                "DELETE FROM folder_papers WHERE folder_id=? AND pmid=?;",
                (fid, pmid),
            )
            papers_removed += int(cur.rowcount or 0)

        for gid in clean_gids:
            cur = conn.execute(
                "DELETE FROM folder_guidelines WHERE folder_id=? AND guideline_id=?;",
                (fid, gid),
            )
            guidelines_removed += int(cur.rowcount or 0)

        if papers_removed > 0 or guidelines_removed > 0:
            conn.execute("UPDATE folders SET updated_at=? WHERE folder_id=?;", (_utc_iso_z(), fid))

    return {
        "papers_removed": str(papers_removed),
        "guidelines_removed": str(guidelines_removed),
        "total_removed": str(papers_removed + guidelines_removed),
    }


def delete_folder(folder_id: str) -> Dict[str, str]:
    ensure_folders_schema()
    fid = (folder_id or "").strip()
    if not fid:
        return {"deleted": "0", "name": "", "papers_removed": "0", "guidelines_removed": "0"}

    with _connect_db() as conn:
        folder_row = conn.execute(
            "SELECT name FROM folders WHERE folder_id=? LIMIT 1;",
            (fid,),
        ).fetchone()
        if not folder_row:
            return {"deleted": "0", "name": "", "papers_removed": "0", "guidelines_removed": "0"}

        name = (folder_row["name"] or "").strip()
        paper_row = conn.execute(
            "SELECT COUNT(*) AS n FROM folder_papers WHERE folder_id=?;",
            (fid,),
        ).fetchone()
        guideline_row = conn.execute(
            "SELECT COUNT(*) AS n FROM folder_guidelines WHERE folder_id=?;",
            (fid,),
        ).fetchone()
        papers_removed = int((paper_row["n"] if paper_row else 0) or 0)
        guidelines_removed = int((guideline_row["n"] if guideline_row else 0) or 0)

        conn.execute("DELETE FROM folder_papers WHERE folder_id=?;", (fid,))
        conn.execute("DELETE FROM folder_guidelines WHERE folder_id=?;", (fid,))
        cur = conn.execute("DELETE FROM folders WHERE folder_id=?;", (fid,))
        deleted = "1" if int(cur.rowcount or 0) > 0 else "0"

    return {
        "deleted": deleted,
        "name": name,
        "papers_removed": str(papers_removed),
        "guidelines_removed": str(guidelines_removed),
    }


# ---------------- Evidence cart ----------------

def ensure_evidence_cart_schema() -> None:
    with _connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_cart_items (
                item_type TEXT NOT NULL CHECK(item_type IN ('paper','guideline')),
                item_id TEXT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (item_type, item_id)
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evidence_cart_added_at
            ON evidence_cart_items(added_at DESC);
            """
        )


def get_evidence_cart_item_ids() -> Dict[str, List[str]]:
    ensure_evidence_cart_schema()
    with _connect_db() as conn:
        rows = conn.execute(
            """
            SELECT item_type, item_id
            FROM evidence_cart_items
            ORDER BY added_at DESC, item_id ASC;
            """
        ).fetchall()

    pmids: List[str] = []
    gids: List[str] = []
    for r in rows:
        item_type = (r["item_type"] or "").strip().lower()
        item_id = (r["item_id"] or "").strip()
        if not item_id:
            continue
        if item_type == "paper":
            pmids.append(item_id)
        elif item_type == "guideline":
            gids.append(item_id)

    return {"pmids": pmids, "guideline_ids": gids}


def add_evidence_cart_items(pmids: List[str], guideline_ids: List[str]) -> Dict[str, str]:
    ensure_evidence_cart_schema()
    clean_pmids = _dedupe_nonempty(pmids)
    clean_gids = _dedupe_nonempty(guideline_ids)
    now = _utc_iso_z()

    papers_added = 0
    guidelines_added = 0

    with _connect_db() as conn:
        for pmid in clean_pmids:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO evidence_cart_items (item_type, item_id, added_at)
                VALUES ('paper', ?, ?);
                """,
                (pmid, now),
            )
            if int(cur.rowcount or 0) > 0:
                papers_added += 1

        for gid in clean_gids:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO evidence_cart_items (item_type, item_id, added_at)
                VALUES ('guideline', ?, ?);
                """,
                (gid, now),
            )
            if int(cur.rowcount or 0) > 0:
                guidelines_added += 1

    return {
        "papers_added": str(papers_added),
        "guidelines_added": str(guidelines_added),
        "total_added": str(papers_added + guidelines_added),
    }


def remove_evidence_cart_items(pmids: List[str], guideline_ids: List[str]) -> Dict[str, str]:
    ensure_evidence_cart_schema()
    clean_pmids = _dedupe_nonempty(pmids)
    clean_gids = _dedupe_nonempty(guideline_ids)

    papers_removed = 0
    guidelines_removed = 0

    with _connect_db() as conn:
        for pmid in clean_pmids:
            cur = conn.execute(
                "DELETE FROM evidence_cart_items WHERE item_type='paper' AND item_id=?;",
                (pmid,),
            )
            papers_removed += int(cur.rowcount or 0)

        for gid in clean_gids:
            cur = conn.execute(
                "DELETE FROM evidence_cart_items WHERE item_type='guideline' AND item_id=?;",
                (gid,),
            )
            guidelines_removed += int(cur.rowcount or 0)

    return {
        "papers_removed": str(papers_removed),
        "guidelines_removed": str(guidelines_removed),
        "total_removed": str(papers_removed + guidelines_removed),
    }


def clear_evidence_cart() -> Dict[str, str]:
    ensure_evidence_cart_schema()
    with _connect_db() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM evidence_cart_items;").fetchone()
        total = int(row["n"] or 0) if row else 0
        conn.execute("DELETE FROM evidence_cart_items;")

    return {"total_removed": str(total)}


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

def delete_guideline(guideline_id: str) -> None:
    gid = (guideline_id or "").strip()
    if not gid:
        return
    with _connect_db() as conn:
        conn.execute("DELETE FROM guidelines WHERE guideline_id=?;", (gid,))
        try:
            conn.execute("DELETE FROM folder_guidelines WHERE guideline_id=?;", (gid,))
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("DELETE FROM evidence_cart_items WHERE item_type='guideline' AND item_id=?;", (gid,))
        except sqlite3.OperationalError:
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

# ---------------- Guideline recommendations + review state ----------------

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

    groups = _parse_search_query_groups(raw)
    if not groups:
        return []

    gcols = [
        "COALESCE(g.guideline_name,'')",
        "COALESCE(g.filename,'')",
        "COALESCE(g.pub_year,'')",
        "COALESCE(g.specialty,'')",
        "COALESCE(g.recommendations_display_md,'')",
    ]

    where_sql, params = _build_search_where_sql(groups, gcols)
    if not where_sql:
        return []

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
