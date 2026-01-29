# extract.py
import os
import re
import time
import random
import json
import io
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import requests
import streamlit as st
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import DocumentContentFormat
except Exception:
    AzureKeyCredential = None
    DocumentIntelligenceClient = None
    DocumentContentFormat = None

if TYPE_CHECKING:
    from azure.ai.documentintelligence import DocumentIntelligenceClient as DocumentIntelligenceClientType

# ---- imports from db layer (must exist in db.py) ----
from db import (
    read_guideline_pdf_bytes,
    get_guideline_meta,
    get_cached_layout_markdown,
    save_layout_markdown,
    update_guideline_metadata,
    get_record,
)

# ---------------- Constants ----------------

NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
NCBI_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

GUIDELINE_ELEMENT_MAX_CHARS = 4500
GUIDELINE_CANDIDATE_MAX = 250

GUIDELINE_OPENAI_BATCH_SIZE = 20  # OpenAI decides which candidates are true recommendations
GUIDELINE_OPENAI_MAX_CHARS_PER_ITEM = 1800

GUIDELINE_OPENAI_STRICTNESS = os.getenv("GUIDELINE_OPENAI_STRICTNESS", "medium").strip().lower()

_RECO_HINT_RE = re.compile(
    r"(?i)\b(recommend|recommended|should|we suggest|we recommend|is indicated|are indicated|is not recommended|do not|avoid|consider)\b"
)
_LOE_HINT_RE = re.compile(
    r"(?i)\b(level of evidence|loe|class\b|grade\b|grading\b|certainty|strong recommendation|conditional recommendation)\b"
)

META_MAX_STUDIES_HARD_CAP = 25
META_MAX_CHARS_PER_STUDY = 10000

_GUIDELINE_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

# ---------------- Section-based recommendation pipeline ----------------

SECTION_TRIAGE_BATCH = int(os.getenv("SECTION_TRIAGE_BATCH", "10"))
SECTION_PREVIEW_HEAD_CHARS = int(os.getenv("SECTION_PREVIEW_HEAD_CHARS", "1200"))
SECTION_PREVIEW_TAIL_CHARS = int(os.getenv("SECTION_PREVIEW_TAIL_CHARS", "700"))
SECTION_PREVIEW_MAX_HINT_LINES = int(os.getenv("SECTION_PREVIEW_MAX_HINT_LINES", "28"))

# How much of a full section to send per extraction call.
# If a section is larger, it will be split into parts (still under the same heading path).
SECTION_MAX_CHARS_SEND = int(os.getenv("SECTION_MAX_CHARS_SEND", "14000"))
SECTION_PART_OVERLAP_CHARS = int(os.getenv("SECTION_PART_OVERLAP_CHARS", "600"))

def _heading_level(line: str) -> int:
    ln = (line or "").lstrip()
    if not ln.startswith("#"):
        return 0
    return len(ln) - len(ln.lstrip("#"))

def _heading_text(line: str) -> str:
    return (line or "").lstrip("#").strip()

def _path_from_stack(stack: List[str]) -> str:
    parts = [p.strip() for p in (stack or []) if p and p.strip()]
    return " > ".join(parts).strip()

def _split_markdown_into_sections(md: str) -> List[Dict[str, str]]:
    """
    Turn markdown into sections keyed by a full heading-path.
    A new section begins at each heading and continues until the next heading.
    """
    text = (md or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    sections: List[Dict[str, str]] = []
    heading_stack: List[str] = []

    current_path = ""
    current_level = 0
    buf: List[str] = []

    def flush():
        nonlocal buf, current_path, current_level
        content = "\n".join(buf).strip()
        buf = []
        if content:
            sections.append(
                {
                    "path": current_path or "(no heading)",
                    "level": str(int(current_level or 0)),
                    "content": content,
                }
            )

    for ln in lines:
        lvl = _heading_level(ln)
        if lvl > 0:
            # New heading -> flush previous section content
            flush()

            title = _heading_text(ln)
            # Maintain a stack where index = level-1
            if lvl <= 0:
                heading_stack = []
            else:
                heading_stack = heading_stack[: max(0, lvl - 1)]
            heading_stack.append(title or "(untitled)")
            current_path = _path_from_stack(heading_stack)
            current_level = lvl

            # Keep the heading line as part of section content (helps GPT)
            buf.append(ln.strip())
            continue

        # normal line
        buf.append(ln)

    flush()

    # If no headings exist, treat whole doc as one section
    if not sections:
        whole = (md or "").strip()
        if whole:
            sections = [{"path": "(no heading)", "level": "0", "content": whole}]

    # assign stable sec_idx in traversal order
    out: List[Dict[str, str]] = []
    for i, s in enumerate(sections, start=1):
        out.append(
            {
                "sec_idx": str(i),
                "path": (s.get("path") or "").strip() or "(no heading)",
                "level": (s.get("level") or "0").strip(),
                "content": (s.get("content") or "").strip(),
            }
        )
    return out

def _section_preview(section_text: str) -> str:
    """
    Preview = head + tail + a few "high-signal" lines that contain recommendation hints.
    Helps triage without missing recs that appear late in a section.
    """
    s = (section_text or "").strip()
    if not s:
        return ""

    head = s[: max(0, SECTION_PREVIEW_HEAD_CHARS)]
    tail = s[-max(0, SECTION_PREVIEW_TAIL_CHARS) :] if len(s) > SECTION_PREVIEW_TAIL_CHARS else ""

    # Hint lines: any line matching recommendation or grading regex
    hint_lines: List[str] = []
    for ln in s.splitlines():
        t = (ln or "").strip()
        if not t:
            continue
        if _RECO_HINT_RE.search(t) or _LOE_HINT_RE.search(t) or re.match(r"(?i)^\s*(recommendation|statement|practice point)\b", t):
            hint_lines.append(t[:240])
        if len(hint_lines) >= SECTION_PREVIEW_MAX_HINT_LINES:
            break

    parts = []
    parts.append("HEAD:\n" + head)
    if hint_lines:
        parts.append("HINT_LINES:\n" + "\n".join(hint_lines))
    if tail and tail != head:
        parts.append("TAIL:\n" + tail)
    return "\n\n".join(parts).strip()

def _split_large_section(text: str, max_chars: int, overlap: int) -> List[str]:
    """
    Split oversized sections into overlapping parts (best-effort, keeps context).
    """
    s = (text or "").strip()
    if not s:
        return []
    if len(s) <= max_chars:
        return [s]

    out: List[str] = []
    start = 0
    while start < len(s):
        end = min(len(s), start + max_chars)
        chunk = s[start:end].strip()
        if chunk:
            out.append(chunk)
        if end >= len(s):
            break
        start = max(0, end - max(0, overlap))
    return out

# ---------------- Core helpers ----------------

def _itertext(el: Optional[ET.Element]) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _ncbi_params_base() -> Dict[str, str]:
    params = {
        "tool": os.getenv("NCBI_TOOL", "streamlit-pmid-abstract"),
        "email": os.getenv("NCBI_EMAIL", "").strip(),
    }
    api_key = os.getenv("NCBI_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key
    return params


@st.cache_resource
def _requests_session() -> requests.Session:
    s = requests.Session()
    email = os.getenv("NCBI_EMAIL", "").strip()
    ua = "streamlit-pmid-abstract/1.0"
    if email:
        ua += f" ({email})"
    s.headers.update({"User-Agent": ua})
    return s


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------- NCBI fetch + parse ----------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pubmed_xml(pmid: str) -> str:
    sess = _requests_session()
    params = {"db": "pubmed", "id": pmid, "retmode": "xml", **_ncbi_params_base()}
    r = sess.get(NCBI_EFETCH_URL, params=params, timeout=25)
    r.raise_for_status()
    return r.text


def parse_abstract(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    abstract_elems = root.findall(".//Abstract/AbstractText")
    parts: List[str] = []
    for el in abstract_elems:
        label = el.attrib.get("Label") or el.attrib.get("NlmCategory") or ""
        txt = _itertext(el)
        if not txt:
            continue
        parts.append(f"{label}: {txt}" if label else txt)
    return "\n\n".join(parts).strip()


def parse_year(xml_text: str) -> str:
    root = ET.fromstring(xml_text)

    year = _itertext(root.find(".//JournalIssue/PubDate/Year"))
    if year:
        return year

    year = _itertext(root.find(".//ArticleDate/Year"))
    if year:
        return year

    medline = _itertext(root.find(".//JournalIssue/PubDate/MedlineDate"))
    if medline:
        m = re.search(r"(\d{4})", medline)
        if m:
            return m.group(1)

    for path in [".//DateCreated/Year", ".//DateCompleted/Year"]:
        year = _itertext(root.find(path))
        if year:
            return year

    return ""


def parse_journal(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    journal = _itertext(root.find(".//Journal/Title"))
    if journal:
        return journal
    return _itertext(root.find(".//Journal/ISOAbbreviation"))


def parse_title(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    return _itertext(root.find(".//ArticleTitle"))


# ---------------- Neighbors (ELink) ----------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_neighbors_elink_xml(pmid: str, retmax: int = 50) -> str:
    sess = _requests_session()
    params = {
        "dbfrom": "pubmed",
        "db": "pubmed",
        "id": pmid,
        "cmd": "neighbor_score",
        "linkname": "pubmed_pubmed",
        "retmode": "xml",
        "retmax": str(int(retmax)),
        **_ncbi_params_base(),
    }
    r = sess.get(NCBI_ELINK_URL, params=params, timeout=25)
    r.raise_for_status()
    return r.text


def parse_neighbor_pmids(elink_xml: str, exclude_pmid: str = "") -> List[str]:
    root = ET.fromstring(elink_xml)

    def _parse_score_any(s: str) -> Optional[float]:
        m = re.search(r"[-+]?\d*\.?\d+", (s or "").strip())
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None

    best: List[Tuple[str, Optional[float]]] = []
    best_rank: Tuple[int, int, int] = (-1, -1, -1)

    for lsdb in root.findall(".//LinkSetDb"):
        linkname = (_itertext(lsdb.find("LinkName")) or "").strip().lower()
        links = lsdb.findall("Link")
        if not links:
            continue

        extracted: List[Tuple[str, Optional[float]]] = []
        has_scores = 0

        for link in links:
            pid = _itertext(link.find("Id")).strip()
            if not pid:
                continue

            score: Optional[float] = None
            for child in list(link):
                if (child.tag or "").strip().lower() in ("score", "linkscore"):
                    score = _parse_score_any(_itertext(child))
                    break

            if score is not None:
                has_scores = 1

            extracted.append((pid, score))

        if not extracted:
            continue

        pref_pubmed = 1 if "pubmed_pubmed" in linkname else 0
        rank = (pref_pubmed, has_scores, len(extracted))
        if rank > best_rank:
            best_rank = rank
            best = extracted

    if not best:
        return []

    if any(s is not None for _, s in best):
        best.sort(key=lambda t: (t[1] is None, -(t[1] or 0.0), t[0]))

    out: List[str] = []
    seen = set()
    ex = (exclude_pmid or "").strip()
    for pid, _ in best:
        if ex and pid == ex:
            continue
        if pid in seen:
            continue
        seen.add(pid)
        out.append(pid)

    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pubmed_esummary_xml(pmids_csv: str) -> str:
    sess = _requests_session()
    params = {"db": "pubmed", "id": pmids_csv, "retmode": "xml", **_ncbi_params_base()}
    r = sess.get(NCBI_ESUMMARY_URL, params=params, timeout=25)
    r.raise_for_status()
    return r.text


def parse_esummary_titles(esummary_xml: str) -> Dict[str, str]:
    root = ET.fromstring(esummary_xml)
    out: Dict[str, str] = {}
    for docsum in root.findall(".//DocSum"):
        pid = _itertext(docsum.find("Id"))
        if not pid:
            continue
        title = ""
        for item in docsum.findall("Item"):
            if item.attrib.get("Name") == "Title":
                title = _itertext(item)
                break
        out[pid] = (title or "").strip()
    return out


def get_top_neighbors(pmid: str, top_n: int = 5) -> List[Dict[str, str]]:
    elink_xml = fetch_neighbors_elink_xml(pmid, retmax=max(50, int(top_n) * 10))
    pmids = parse_neighbor_pmids(elink_xml, exclude_pmid=pmid)[: int(top_n)]
    if not pmids:
        return []
    esum_xml = fetch_pubmed_esummary_xml(",".join(pmids))
    titles = parse_esummary_titles(esum_xml)
    return [{"pmid": p, "title": titles.get(p, "").strip()} for p in pmids]


# ---------------- OpenAI helpers ----------------

def _openai_api_key() -> str:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return str(st.secrets["OPENAI_API_KEY"]).strip()
    except Exception:
        pass
    try:
        if "openai" in st.secrets and "api_key" in st.secrets["openai"]:
            return str(st.secrets["openai"]["api_key"]).strip()
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "").strip()


def _openai_model() -> str:
    try:
        if "OPENAI_MODEL" in st.secrets:
            return str(st.secrets["OPENAI_MODEL"]).strip() or "gpt-5.2"
    except Exception:
        pass
    return (os.getenv("OPENAI_MODEL", "").strip() or "gpt-5.2")



# ---------------- Semantic Scholar helpers ----------------

SEMANTIC_SCHOLAR_RECOMMEND_FORPAPER_URL = "https://api.semanticscholar.org/recommendations/v1/papers/forpaper/"

def _semantic_scholar_api_key() -> str:
    """Return Semantic Scholar API key (supports multiple secrets.toml layouts)."""
    try:
        if "SEMANTIC_SCHOLAR_API_KEY" in st.secrets:
            return str(st.secrets["SEMANTIC_SCHOLAR_API_KEY"]).strip()
    except Exception:
        pass
    try:
        if "semantic_scholar" in st.secrets and "api_key" in st.secrets["semantic_scholar"]:
            return str(st.secrets["semantic_scholar"]["api_key"]).strip()
    except Exception:
        pass
    return os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()

@st.cache_data(show_spinner=False, ttl=60 * 60)
def get_s2_similar_papers(pmid: str, top_n: int = 5) -> List[Dict[str, str]]:
    """Return top Semantic Scholar recommendations for a PubMed PMID."""
    pmid = (pmid or "").strip()
    if not pmid:
        return []

    api_key = _semantic_scholar_api_key()
    if not api_key:
        raise ValueError(
            "Semantic Scholar API key not found. Add SEMANTIC_SCHOLAR_API_KEY to .streamlit/secrets.toml "
            "or set the SEMANTIC_SCHOLAR_API_KEY environment variable."
        )

    # Recommendations API accepts paper ids including PMID/PMCID/DOI formats.
    # Use explicit 'PMID:' prefix to avoid ambiguity.
    paper_id = f"PMID:{pmid}"
    url = SEMANTIC_SCHOLAR_RECOMMEND_FORPAPER_URL + quote(paper_id, safe="")
    params = {
        "limit": str(int(top_n)),
        "fields": "title,url,year,externalIds",
    }
    headers = {"x-api-key": api_key}

    sess = _requests_session()
    r = sess.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()

    payload = r.json() or {}
    recs = payload.get("recommendedPapers") or []

    out: List[Dict[str, str]] = []
    for p in recs[: int(top_n)]:
        ext = p.get("externalIds") or {}
        out.append(
            {
                "title": (p.get("title") or "").strip(),
                "url": (p.get("url") or "").strip(),
                "paperId": (p.get("paperId") or "").strip(),
                "year": str(p.get("year") or "").strip(),
                "pmid": str(ext.get("PubMed") or "").strip(),
                "doi": str(ext.get("DOI") or "").strip(),
            }
        )
    return out


def _post_with_retries(
    url: str,
    headers: Dict[str, str],
    json: Dict,
    timeout: int = 30,
) -> requests.Response:
    sess = _requests_session()
    last_exc: Optional[Exception] = None

    for attempt in range(5):
        try:
            r = sess.post(url, headers=headers, json=json, timeout=timeout)

            if r.status_code in (429, 500, 502, 503, 504):
                retry_after = r.headers.get("Retry-After", "").strip()
                ra = int(retry_after) if retry_after.isdigit() else None

                backoff = (2 ** attempt) + random.random()
                sleep_s = ra if ra is not None else min(backoff, 10)
                time.sleep(max(0.5, float(sleep_s)))
                continue

            r.raise_for_status()
            return r

        except Exception as e:
            last_exc = e
            backoff = (2 ** attempt) + random.random()
            time.sleep(min(backoff, 10))

    if last_exc:
        raise last_exc
    raise RuntimeError("POST failed after retries")


def _extract_output_text(resp_json: Dict) -> str:
    if isinstance(resp_json.get("output_text"), str) and resp_json["output_text"].strip():
        return resp_json["output_text"].strip()

    parts: List[str] = []
    for item in (resp_json.get("output") or []):
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for c in (item.get("content") or []):
            if isinstance(c, dict) and c.get("type") == "output_text" and isinstance(c.get("text"), str):
                parts.append(c["text"])
    return "\n".join(parts).strip()


def _parse_nonneg_int(raw: str) -> Optional[int]:
    s = (raw or "").strip()
    if not s:
        return None
    s = s.replace(",", "")
    m = re.search(r"(\d+)", s)
    if not m:
        return None
    try:
        n = int(m.group(1))
        return n if n >= 0 else None
    except Exception:
        return None


def _parse_tag_list(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if re.fullmatch(r"(?i)\s*(none|n/a|na|null|0|unknown)\s*", s):
        return ""

    toks = re.split(r"[,\n;|]+", s)
    out: List[str] = []
    seen = set()
    for t in toks:
        t = (t or "").strip().strip("-•").strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return ", ".join(out).strip()


def _normalize_bullets(raw: str) -> str:
    out_text = (raw or "").strip()
    if not out_text:
        return ""
    lines = [ln.strip() for ln in out_text.splitlines() if ln.strip()]
    bullets: List[str] = []
    for ln in lines:
        if ln.startswith("- "):
            bullets.append(ln)
        else:
            bullets.append("- " + ln.lstrip("-• ").strip())

    seen = set()
    final: List[str] = []
    for b in bullets:
        key = b.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        final.append(b)
    return "\n".join(final).strip()


def _strip_digits(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    s = re.sub(r"\d", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    return s.strip()


# ---------------- OpenAI extractors ----------------

@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_specialty(title: str, abstract: str) -> str:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not abstract:
        return ""

    instructions = (
        "You extract medical specialty labels from a PubMed title+abstract.\n"
        "Return a comma-separated list of specialty names (or an empty string if unclear).\n"
        "Rules:\n"
        "- Output MUST be ONLY the comma-separated specialties on one line (no extra text).\n"
        "- You must restrict your choice to the following specialties: Cardiology, Endocrinology, Gastroenterology, Hematology, Infectious Disease, Nephrology, Neurology, Oncology, Pulmonology, Rheumatology, Critical Care, Emergency Medicine, Surgery, Obstetrics and Gynecology, Psychiatry, Dermatology, Ophthalmology, Otolaryngology, Urology, Orthopedics.\n"
        "- You may return multiple specialties if truly relevant.\n"
        "- Do not invent specialties; use only what is explicitly stated or strongly implied.\n"
        "- Keep it concise (max 2)."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": f"TITLE:\n{title}\n\nABSTRACT:\n{abstract}\n\nReturn the specialty list.",
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": 48,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()

    return _parse_tag_list(_extract_output_text(r.json()))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_study_design(title: str, abstract: str) -> str:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not abstract:
        return ""

    instructions = (
        "You extract study design descriptors from a PubMed abstract.\n"
        "Return a comma-separated list of short tags (no extra text).\n"
        "Only include tags that are explicitly stated or very strongly implied by the abstract.\n"
        "If unclear, return an empty string.\n"
        "\n"
        "Include BOTH:\n"
        "1) study design tags (trial/observational/review etc)\n"
        "2) setting/geography tags when stated (country/region, community hospital vs academic center, ICU/ED/inpatient/outpatient, multicenter, multinational)\n"
        "\n"
        "Output rules:\n"
        "- Output MUST be ONLY the comma-separated tags, on one line.\n"
        "- Do NOT explain.\n"
        "- Do NOT invent tags not supported by the abstract."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": f"TITLE:\n{title}\n\nABSTRACT:\n{abstract}\n\nReturn the study design + setting/geography tags.",
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": 72,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()

    return _parse_tag_list(_extract_output_text(r.json()))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_patient_details(title: str, abstract: str, patient_n: int, study_design: str) -> str:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not abstract:
        return ""

    instructions = (
        "You extract patient population details from a PubMed abstract.\n"
        "Return ONLY bullet lines, each starting with '- ' (or return an empty string).\n"
        "Hard rules:\n"
        "- Use ONLY information explicitly stated in the abstract. Do not invent or infer beyond what's stated.\n"
        "- Do NOT include any headers, labels, or subheadings.\n"
        "- Do NOT repeat the total patient count or any study design descriptors/tags.\n"
        "- Prioritize eligibility criteria and baseline characteristics.\n"
        "- Keep it concise and high-yield. Prefer 3–10 bullets when possible.\n"
        "- If the abstract does not state meaningful eligibility/baseline details, return an empty string."
    )

    user_input = (
        f"TITLE:\n{title}\n\n"
        f"ALREADY EXTRACTED (do not repeat):\n"
        f"- Patient count: {int(patient_n) if patient_n is not None else 0}\n"
        f"- Study design tags: {study_design or ''}\n\n"
        f"ABSTRACT:\n{abstract}\n\nReturn the bullet list."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": user_input,
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": 350,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()

    return _normalize_bullets(_extract_output_text(r.json()))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_intervention_comparison(
    title: str,
    abstract: str,
    patient_n: int,
    study_design: str,
    patient_details: str,
) -> str:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not abstract:
        return ""

    instructions = (
        "You extract the intervention and the comparison from a PubMed abstract.\n"
        "Return ONLY bullet lines, each starting with '- ' (or return an empty string).\n"
        "Hard rules:\n"
        "- Use ONLY information explicitly stated in the abstract. Do not invent or infer beyond what's stated.\n"
        "- Do NOT include any headers, labels, or subheadings.\n"
        "- Do NOT repeat patient count, study design tags, or patient population details.\n"
        "- Capture: intervention/exposure, comparator/control/reference, dosing/intensity, timing, duration, co-interventions if stated.\n"
        "- If no clear intervention/comparator is described, return an empty string.\n"
        "- Keep it concise (prefer 2–8 bullets)."
    )

    user_input = (
        f"TITLE:\n{title}\n\n"
        f"ALREADY EXTRACTED (do not repeat):\n"
        f"- Patient count: {int(patient_n) if patient_n is not None else 0}\n"
        f"- Study design tags: {study_design or ''}\n"
        f"- Patient details:\n{patient_details or ''}\n\n"
        f"ABSTRACT:\n{abstract}\n\nReturn the bullet list."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": user_input,
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": 320,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()

    return _normalize_bullets(_extract_output_text(r.json()))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_authors_conclusions(
    title: str,
    abstract: str,
    patient_n: int,
    study_design: str,
    patient_details: str,
    intervention_comparison: str,
) -> str:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not abstract:
        return ""

    instructions = (
        "Extract the authors' conclusion statement from a PubMed abstract.\n"
        "Output MUST be plain text only (no bullets, no labels, no quotes), ideally 1–2 sentences.\n"
        "Be as close to verbatim as possible from the abstract text (prefer the Conclusions sentence if present).\n"
        "Do NOT include any numbers (no digits), and avoid statistics.\n"
        "Do NOT repeat patient count, study design tags, patient details, or intervention/comparison specifics.\n"
        "If no clear conclusion statement exists, return an empty string."
    )

    user_input = (
        f"TITLE:\n{title}\n\n"
        f"ALREADY EXTRACTED (do not repeat):\n"
        f"- Patient count: {int(patient_n) if patient_n is not None else 0}\n"
        f"- Study design tags: {study_design or ''}\n"
        f"- Patient details:\n{patient_details or ''}\n"
        f"- Intervention/comparison:\n{intervention_comparison or ''}\n\n"
        f"ABSTRACT:\n{abstract}\n\nReturn the authors' conclusion statement."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": user_input,
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": 160,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()

    return _strip_digits((_extract_output_text(r.json()) or "").strip())


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_results(
    title: str,
    abstract: str,
    patient_n: int,
    study_design: str,
    patient_details: str,
    intervention_comparison: str,
) -> str:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not abstract:
        return ""

    instructions = (
        "Extract the RESULTS from a PubMed abstract.\n"
        "Return ONLY bullet lines, each starting with '- '. No headers, no labels.\n"
        "Make ONE bullet per distinct reported result.\n"
        "Rules:\n"
        "- Use ONLY information explicitly stated in the abstract. Do not invent.\n"
        "- Avoid repeating patient count, study design tags, patient details, and intervention/comparison descriptions.\n"
        "- If a confidence interval (CI) is provided for a result, do NOT include a p-value for that same result.\n"
        "- Prefer including: outcome name, time horizon (if stated), effect estimate (RR/OR/HR/MD/etc), and CI when stated.\n"
        "- If results are not clearly stated, return an empty string.\n"
        "- Keep it concise; prefer 2–12 bullets."
    )

    user_input = (
        f"TITLE:\n{title}\n\n"
        f"ALREADY EXTRACTED (do not repeat):\n"
        f"- Patient count: {int(patient_n) if patient_n is not None else 0}\n"
        f"- Study design tags: {study_design or ''}\n"
        f"- Patient details:\n{patient_details or ''}\n"
        f"- Intervention/comparison:\n{intervention_comparison or ''}\n\n"
        f"ABSTRACT:\n{abstract}\n\nReturn the results bullet list."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": user_input,
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": 520,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()

    return _normalize_bullets(_extract_output_text(r.json()))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_patient_n(title: str, abstract: str) -> int:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not abstract:
        return 0

    instructions = (
        "You extract the total integer number of human patients/participants studied from a PubMed abstract.\n"
        "Rules:\n"
        "- Output MUST be a single integer on one line, with no other text.\n"
        "- If multiple groups are reported (e.g., randomized arms), output the total enrolled/analyzed participants across all groups.\n"
        "- If multiple cohorts or phases are described, sum the unique participant counts when clearly stated; otherwise use the best single total.\n"
        "- If the abstract is not a human patient/participant study, or the total is not stated/derivable, output 0.\n"
        "- Do not output words, units, punctuation, or explanations."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": f"TITLE:\n{title}\n\nABSTRACT:\n{abstract}\n\nReturn the total number of patients studied.",
        "reasoning": {"effort": "none"},
        "text": {"verbosity": "low"},
        "max_output_tokens": 16,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()

    n = _parse_nonneg_int(_extract_output_text(r.json()))
    return int(n) if n is not None else 0


# ---------------- Azure Document Intelligence (Layout -> Markdown) ----------------

def _azure_di_endpoint() -> str:
    try:
        if "AZURE_DI_ENDPOINT" in st.secrets:
            return str(st.secrets["AZURE_DI_ENDPOINT"]).strip()
    except Exception:
        pass
    return os.getenv("AZURE_DI_ENDPOINT", "").strip()


def _azure_di_key() -> str:
    try:
        if "AZURE_DI_KEY" in st.secrets:
            return str(st.secrets["AZURE_DI_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("AZURE_DI_KEY", "").strip()


def _require_azure_di() -> None:
    if DocumentIntelligenceClient is None or AzureKeyCredential is None:
        raise RuntimeError("azure-ai-documentintelligence is not installed. Run: pip install azure-ai-documentintelligence")
    ep = _azure_di_endpoint()
    key = _azure_di_key()
    if not ep or not key:
        raise RuntimeError("Missing AZURE_DI_ENDPOINT / AZURE_DI_KEY in secrets.toml (or env vars).")


def _azure_di_client() -> "DocumentIntelligenceClientType":
    _require_azure_di()
    return DocumentIntelligenceClient(endpoint=_azure_di_endpoint(), credential=AzureKeyCredential(_azure_di_key()))


def analyze_pdf_to_markdown_azure(pdf_bytes: bytes) -> str:
    client = _azure_di_client()
    body = io.BytesIO(pdf_bytes)

    try:
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=body,
            output_content_format=DocumentContentFormat.MARKDOWN,
        )
    except Exception:
        body.seek(0)
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=body,
            output_content_format="markdown",
        )

    result = poller.result()
    return (getattr(result, "content", "") or "").strip()


def get_or_create_markdown(guideline_id: str) -> str:
    meta = get_guideline_meta(guideline_id)
    if not meta:
        return ""
    sha = meta.get("sha256", "")
    cached = get_cached_layout_markdown(guideline_id, sha)
    if (cached or "").strip():
        return cached.strip()

    pdf_bytes = read_guideline_pdf_bytes(guideline_id)
    if not pdf_bytes:
        return ""

    md = analyze_pdf_to_markdown_azure(pdf_bytes)
    if md.strip():
        save_layout_markdown(guideline_id, sha, md)
    return md.strip()


# ---------------- Guideline markdown -> elements ----------------

def _split_markdown_into_elements(md: str) -> List[Dict[str, str]]:
    text = (md or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    lines = text.split("\n")
    out: List[Dict[str, str]] = []
    buf: List[str] = []

    def flush_paragraph():
        nonlocal buf
        s = " ".join([b.strip() for b in buf if b.strip()]).strip()
        buf = []
        if s:
            out.append({"kind": "text", "content": s})

    list_re = re.compile(r"^\s*(?:[-*+]|(?:\d+[\.\)]))\s+")
    table_sep_re = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")

    i = 0
    while i < len(lines):
        ln = lines[i]

        if not ln.strip():
            flush_paragraph()
            i += 1
            continue

        if ln.lstrip().startswith("#"):
            flush_paragraph()
            out.append({"kind": "heading", "content": ln.strip()})
            i += 1
            continue

        # Boxed / callout text often shows up as blockquotes in Azure DI markdown
        if ln.lstrip().startswith(">"):
            flush_paragraph()
            q: List[str] = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                q.append(re.sub(r"^\s*>\s?", "", lines[i]).rstrip())
                i += 1
            content = " ".join([x for x in q if x.strip()]).strip()
            if content:
                out.append({"kind": "callout", "content": content})
            continue

        # Table: header line + separator line
        if ("|" in ln) and (i + 1 < len(lines)) and table_sep_re.match(lines[i + 1] or ""):
            flush_paragraph()
            header = ln.strip()
            i += 2

            rows = []
            while i < len(lines) and lines[i].strip() and ("|" in lines[i]):
                rows.append(lines[i].strip())
                i += 1

            for r in rows:
                out.append({"kind": "table_row", "content": f"TABLE HEADER: {header}\nTABLE ROW: {r}"})
            continue

        # List item (+ continuation lines)
        if list_re.match(ln):
            flush_paragraph()
            base = list_re.sub("", ln).strip()
            cont: List[str] = []
            i += 1

            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    break
                if nxt.lstrip().startswith("#"):
                    break
                if ("|" in nxt) and (i + 1 < len(lines)) and table_sep_re.match(lines[i + 1] or ""):
                    break
                if list_re.match(nxt):
                    break

                # continuation heuristic: only accept indented lines
                if nxt.startswith("  ") or nxt.startswith("\t"):
                    cont.append(nxt.strip())
                    i += 1
                    continue

                # stop if not clearly a continuation
                break

            full = " ".join([base] + cont).strip()
            if full:
                out.append({"kind": "list_item", "content": full})
            continue

        buf.append(ln)
        i += 1

    flush_paragraph()

    # bound element size
    bounded: List[Dict[str, str]] = []
    for el in out:
        c = (el.get("content") or "").strip()
        if not c:
            continue
        if len(c) <= GUIDELINE_ELEMENT_MAX_CHARS:
            bounded.append(el)
        else:
            start = 0
            while start < len(c):
                chunk = c[start : start + GUIDELINE_ELEMENT_MAX_CHARS]
                bounded.append({"kind": el.get("kind") or "text", "content": chunk})
                start += GUIDELINE_ELEMENT_MAX_CHARS
    return bounded


def _is_candidate_reco(el_text: str) -> bool:
    s = (el_text or "").strip()
    if len(s) < 25:
        return False
    if _RECO_HINT_RE.search(s):
        return True
    if _LOE_HINT_RE.search(s):
        return True
    if re.match(r"(?i)^\s*(recommendation|statement|key recommendation)\b", s):
        return True
    return False


def _hash_text(s: str) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update((s or "").encode("utf-8", errors="ignore"))
    return h.hexdigest()


# ---------------- Guideline extraction: OpenAI recos from elements ----------------

def _openai_extract_recos_from_element(element_text: str) -> List[Dict[str, str]]:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    el = (element_text or "").strip()
    if not el:
        return []

    instructions = (
        "You extract clinical guideline RECOMMENDATIONS from the provided text (which may be markdown or a table row).\n"
        "Return ONLY valid JSON (no markdown) with this exact top-level shape:\n"
        "{ \"items\": [ {\"recommendation_text\":\"...\",\"strength_raw\":\"...\",\"evidence_raw\":\"...\",\"source_snippet\":\"...\"}, ... ] }\n"
        "Rules:\n"
        "- Use ONLY what is explicitly in the text. Do NOT infer or guess.\n"
        "- If no recommendation is present, return {\"items\":[]}.\n"
        "- recommendation_text: include the FULL actionable recommendation sentence(s); do not truncate clauses.\n"
        "- strength_raw: e.g., 'Class I', 'Strong recommendation' if explicitly stated; else empty string.\n"
        "- evidence_raw: e.g., 'Level A', 'LOE B', 'moderate certainty' if explicitly stated; else empty string.\n"
        "- source_snippet: short verbatim excerpt (<= 240 chars) supporting the recommendation + any grading.\n"
        "- Strings only; never null.\n"
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": f"TEXT:\n{el}\n\nReturn JSON now.",
        "text": {"verbosity": "low"},
        "max_output_tokens": 650,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=75,
    )
    r.raise_for_status()

    raw = (_extract_output_text(r.json()) or "").strip()
    if not raw:
        return []

    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
        if not m:
            return []
        try:
            obj = json.loads(m.group(1))
        except Exception:
            return []

    items = obj.get("items")
    if not isinstance(items, list):
        return []

    out: List[Dict[str, str]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rec = (it.get("recommendation_text") or "").strip()
        if not rec:
            continue
        out.append(
            {
                "recommendation_text": rec,
                "strength_raw": (it.get("strength_raw") or "").strip(),
                "evidence_raw": (it.get("evidence_raw") or "").strip(),
                "source_snippet": (it.get("source_snippet") or "").strip(),
            }
        )
    return out


def _openai_extract_recos_from_elements_batch(batch: List[Dict]) -> List[Dict[str, str]]:
    """Batch extractor: OpenAI decides which items are *formal* guideline recommendations."""
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    if not batch:
        return []

    cand = []
    for it in batch:
        try:
            idx = int(it.get("idx"))
        except Exception:
            continue
        kind = (it.get("kind") or "text").strip()
        section = (it.get("section") or "").strip()
        text = (it.get("content") or "").strip()
        if not text:
            continue
        cand.append(
            {
                "idx": idx,
                "kind": kind,
                "section": section[:120],
                "text": text[:GUIDELINE_OPENAI_MAX_CHARS_PER_ITEM],
            }
        )

    if not cand:
        return []

    strictness = (GUIDELINE_OPENAI_STRICTNESS or "medium").strip().lower()

    if strictness == "strict":
        instructions = """You are a STRICT extractor of *formal* clinical guideline recommendations.
Input is a JSON array of candidate snippets from a guideline PDF.
Each candidate has: idx (identifier), kind (list_item/table_row/callout/text), section (nearest heading), text.

Only output items when you are confident the text is intended as an actual guideline recommendation/statement:
- Typically appears as a list item, table row, or boxed/callout text.
- Or explicitly labeled (e.g., 'Recommendation', 'Statement', 'Practice Point', 'Key recommendation').
- Or contains explicit strength/grade markers (Class/Level/LOE/GRADE/etc.).

Do NOT extract:
- Background, rationale, narrative discussion, evidence summaries, methods.
- 'Recommended daily allowance' / nutrition RDAs, reporting checklists, or 'recommended for future research'.
- Anything that is not an actionable clinical directive.

For kind='text' (plain paragraph): be EXTRA strict — only extract if it is clearly labeled as a recommendation or includes explicit grading/strength. If unsure, omit.

Return ONLY valid JSON with this exact shape:
{ "items": [ {"idx":123, "recommendation_text":"...", "strength_raw":"...", "evidence_raw":"...", "source_snippet":"..."}, ... ] }

Rules:
- Use ONLY what is explicitly present in the provided text; never infer.
- idx MUST be one of the provided idx values.
- recommendation_text: include the full actionable recommendation sentence(s).
- strength_raw / evidence_raw: include only if explicitly stated; else empty string.
- source_snippet: verbatim excerpt <= 240 chars from the candidate text.
- Strings only (no nulls). If none qualify, return {"items":[]}"""
    elif strictness == "loose":
        instructions = """You extract clinical guideline recommendations with good recall (still avoid obvious false positives).
Input is a JSON array of candidate snippets from a guideline PDF.
Each candidate has: idx (identifier), kind (list_item/table_row/callout/text), section (nearest heading), text.

Extract items that read like actionable guidance (directive language) even if not graded, especially when:
- kind is list_item/table_row/callout, OR
- section heading suggests recommendations/guidance/statements/algorithm/summary, OR
- the snippet is short and directive.

When a snippet includes rationale + recommendation, extract ONLY the directive sentence(s).

Do NOT extract:
- Recommended daily allowance / nutrition RDAs, reporting checklists, or future research recommendations.
- Methods, literature review, background.

Return ONLY valid JSON with this exact shape:
{ "items": [ {"idx":123, "recommendation_text":"...", "strength_raw":"...", "evidence_raw":"...", "source_snippet":"..."}, ... ] }

Rules:
- Use ONLY what is explicitly present in the provided text; never infer.
- idx MUST be one of the provided idx values.
- strength_raw/evidence_raw only if explicitly stated, else empty string.
- source_snippet <= 240 chars.
- If none qualify, return {"items":[]}"""
    else:
        instructions = """You extract clinical guideline recommendations with HIGH precision and balanced recall.
Input is a JSON array of candidate snippets from a guideline PDF.
Each candidate has: idx (identifier), kind (list_item/table_row/callout/text), section (nearest heading), text.

A recommendation is an *actionable clinical directive* intended as guidance (for clinicians/patients).
Prefer TRUE recommendations; skip narrative evidence summaries.

Strong signals (any one can be sufficient):
- kind is list_item, table_row, or callout (boxed text).
- The section heading suggests recommendations/guidance/statements/algorithm/summary.
- The text contains directive language (e.g., should, must, we recommend, do not, avoid, consider, offer, use, initiate, administer, discontinue).
- Explicit labels (Recommendation/Statement/Practice Point/Key recommendation) or grading (Class/Level/LOE/GRADE/etc.).

For kind='text' (plain paragraph): extract if BOTH are true:
1) It contains clear directive language; AND
2) It is either (a) under a recommendation-like section heading OR (b) explicitly labeled/graded OR (c) short and directive (roughly <= 450 characters of main directive text).
If a paragraph mixes rationale + recommendation, extract ONLY the recommendation sentence(s) and omit rationale.

Do NOT extract:
- Background, rationale-only discussion, evidence summaries, methods.
- 'Recommended daily allowance' / nutrition RDAs, reporting checklists, or 'recommended for future research'.
- Vague non-directive statements ("may be beneficial") unless clearly framed as guidance.

Return ONLY valid JSON with this exact shape:
{ "items": [ {"idx":123, "recommendation_text":"...", "strength_raw":"...", "evidence_raw":"...", "source_snippet":"..."}, ... ] }

Rules:
- Use ONLY what is explicitly present in the provided text; never infer.
- idx MUST be one of the provided idx values.
- recommendation_text: include the full actionable recommendation sentence(s).
- strength_raw / evidence_raw: include only if explicitly stated; else empty string.
- source_snippet: verbatim excerpt <= 240 chars from the candidate text.
- Strings only (no nulls). If none qualify, return {"items":[]}"""

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": "CANDIDATES_JSON:\n" + json.dumps(cand, ensure_ascii=False) + "\n\nReturn JSON now.",
        "text": {"verbosity": "low"},
        "max_output_tokens": 1400,
        "temperature": 0,
        "store": False,
    }

    r = requests.post(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    r.raise_for_status()

    raw = (_extract_output_text(r.json()) or "").strip()
    if not raw:
        return []

    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
        if not m:
            return []
        try:
            obj = json.loads(m.group(1))
        except Exception:
            return []

    items = obj.get("items")
    if not isinstance(items, list):
        return []

    out: List[Dict[str, str]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            idx = int(it.get("idx"))
        except Exception:
            continue
        rec = (it.get("recommendation_text") or "").strip()
        if not rec:
            continue
        out.append(
            {
                "idx": str(idx),
                "recommendation_text": rec,
                "strength_raw": (it.get("strength_raw") or "").strip(),
                "evidence_raw": (it.get("evidence_raw") or "").strip(),
                "source_snippet": (it.get("source_snippet") or "").strip(),
            }
        )

    return out


def _openai_triage_sections(sections: List[Dict[str, str]]) -> List[int]:
    """
    First pass: decide which sections likely contain formal recommendations.
    Returns a list of sec_idx (ints) to pursue.
    """
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    items = []
    for s in sections:
        try:
            sec_idx = int(s.get("sec_idx") or 0)
        except Exception:
            continue
        path = (s.get("path") or "").strip()
        content = (s.get("content") or "").strip()
        if not content:
            continue
        items.append(
            {
                "sec_idx": sec_idx,
                "path": path[:220],
                "preview": _section_preview(content)[:5000],
            }
        )

    if not items:
        return []

    strictness = (GUIDELINE_OPENAI_STRICTNESS or "medium").strip().lower()

    instructions = f"""You are triaging sections of a clinical guideline to find where *formal clinical recommendations* likely appear.
Input is JSON with items: sec_idx, path (heading path), preview (head/tail + hint lines).

Return ONLY valid JSON with this exact shape:
{{ "keep": [<sec_idx integers>], "maybe": [<sec_idx integers>] }}

Guidance:
- "keep": sections very likely to contain formal recommendations/statements/practice points/graded directives.
- "maybe": sections that might contain recommendations but you are less confident.
- Prefer precision but don't miss obvious recommendation sections (e.g., 'Recommendations', 'Practice points', 'Summary of recommendations', 'Algorithm', 'Key statements').

Do NOT include methods/background/evidence review unless there is clear directive language intended as guidance.

Strictness mode is '{strictness}'. In 'strict', be more conservative.
"""

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": "SECTIONS_JSON:\n" + json.dumps({"items": items}, ensure_ascii=False) + "\n\nReturn JSON now.",
        "text": {"verbosity": "low"},
        "max_output_tokens": 900,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()

    raw = (_extract_output_text(r.json()) or "").strip()
    if not raw:
        return []

    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
        if not m:
            return []
        try:
            obj = json.loads(m.group(1))
        except Exception:
            return []

    keep = obj.get("keep") or []
    maybe = obj.get("maybe") or []

    out: List[int] = []
    for arr in (keep, maybe):
        if not isinstance(arr, list):
            continue
        for v in arr:
            try:
                out.append(int(v))
            except Exception:
                continue

    # dedupe while preserving order
    seen = set()
    final = []
    for x in out:
        if x in seen:
            continue
        seen.add(x)
        final.append(x)
    return final

def _openai_extract_recos_from_section(section_text: str, heading_path: str) -> List[Dict[str, str]]:
    """
    Second pass: extract recommendations from the full section text.
    """
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    sec = (section_text or "").strip()
    if not sec:
        return []

    strictness = (GUIDELINE_OPENAI_STRICTNESS or "medium").strip().lower()

    instructions = f"""You extract *formal clinical guideline recommendations* from a single guideline section.
You must be faithful to the text.

Return ONLY valid JSON with this exact shape:
{{ "items": [ {{"recommendation_text":"...","strength_raw":"...","evidence_raw":"...","source_snippet":"..."}}, ... ] }}

Rules:
- Use ONLY what is explicitly present in the section. Never infer.
- If no formal recommendation is present, return {{ "items": [] }}.
- recommendation_text: include the full actionable directive sentence(s). Do not truncate clauses.
- strength_raw / evidence_raw: include only if explicitly stated; else empty string.
- source_snippet: verbatim excerpt <= 240 chars that supports the recommendation (include grade markers if present).
- Strings only; never null. No extra keys.

Strictness mode: '{strictness}'
- In 'strict': extract only clearly labeled/graded or clearly directive guidance intended as recommendations.
- In 'loose': allow ungraded but clearly directive practice guidance.
"""

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": f"HEADING_PATH:\n{(heading_path or '').strip()}\n\nSECTION_TEXT:\n{sec}\n\nReturn JSON now.",
        "text": {"verbosity": "low"},
        "max_output_tokens": 1400,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    r.raise_for_status()

    raw = (_extract_output_text(r.json()) or "").strip()
    if not raw:
        return []

    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
        if not m:
            return []
        try:
            obj = json.loads(m.group(1))
        except Exception:
            return []

    items = obj.get("items")
    if not isinstance(items, list):
        return []

    out: List[Dict[str, str]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rec = (it.get("recommendation_text") or "").strip()
        if not rec:
            continue
        out.append(
            {
                "recommendation_text": rec,
                "strength_raw": (it.get("strength_raw") or "").strip(),
                "evidence_raw": (it.get("evidence_raw") or "").strip(),
                "source_snippet": (it.get("source_snippet") or "").strip(),
            }
        )
    return out

def extract_and_store_guideline_recommendations_azure(guideline_id: str, progress_cb=None) -> int:
    """
    Azure DI markdown -> elements -> candidates -> OpenAI -> store via db.py
    NOTE: storage function lives in db.py; we import it lazily to avoid circular imports.
    """
    from db import insert_guideline_element, insert_guideline_recommendation  # must exist in db.py

    gid = (guideline_id or "").strip()
    if not gid:
        return 0

    md = get_or_create_markdown(gid)
    if not md:
        return 0

    # 1) Build full sections with heading paths
    sections = _split_markdown_into_sections(md)
    if not sections:
        return 0

    # Optional safety cap for pathological docs
    if len(sections) > 3000:
        sections = sections[:3000]

    # 2) TRIAGE pass: decide which sections to pursue
    # Batch triage to keep prompts bounded
    keep_sec_idxs: List[int] = []
    for b0 in range(0, len(sections), SECTION_TRIAGE_BATCH):
        batch = sections[b0 : b0 + SECTION_TRIAGE_BATCH]
        try:
            keep = _openai_triage_sections(batch)
        except Exception:
            keep = []
        keep_sec_idxs.extend(keep)
        if progress_cb:
            progress_cb(min(b0 + len(batch), len(sections)), len(sections))

    keep_set = set(int(x) for x in keep_sec_idxs if isinstance(x, int) or str(x).isdigit())
    if not keep_set:
        return 0

    created_at = _utc_iso_z()
    stored = 0
    seen = set()

    # 3) For each kept section: store as an element + extract recommendations from full section
    # NOTE: storage function lives in db.py; imported lazily to avoid circular imports.
    from db import insert_guideline_element, insert_guideline_recommendation

    for s in sections:
        try:
            sec_idx = int(s.get("sec_idx") or 0)
        except Exception:
            continue
        if sec_idx not in keep_set:
            continue

        path = (s.get("path") or "").strip() or "(no heading)"
        content = (s.get("content") or "").strip()
        if not content:
            continue

        # store section as a guideline_element (best-effort) for audit/debug
        sec_blob = f"PATH: {path}\n\n{content}".strip()
        sec_hash = _hash_text(sec_blob)
        try:
            insert_guideline_element(gid, sec_idx, "section", sec_blob[:GUIDELINE_ELEMENT_MAX_CHARS], sec_hash)
        except Exception:
            pass

        # 4) EXTRACT pass: send the whole section (or split into parts if huge)
        parts = _split_large_section(content, max_chars=SECTION_MAX_CHARS_SEND, overlap=SECTION_PART_OVERLAP_CHARS)
        for pi, part in enumerate(parts, start=1):
            part_path = path if len(parts) == 1 else f"{path} (part {pi}/{len(parts)})"
            try:
                recos = _openai_extract_recos_from_section(part, part_path)
            except Exception:
                recos = []

            if not recos:
                continue

            for rco in recos:
                rec_text = (rco.get("recommendation_text") or "").strip()
                if not rec_text:
                    continue

                strength = (rco.get("strength_raw") or "").strip()
                evidence = (rco.get("evidence_raw") or "").strip()
                snippet = (rco.get("source_snippet") or "").strip()

                # Light dedupe
                dedupe_key = (rec_text.lower(), strength.lower(), evidence.lower())
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                # Persist; put heading path into snippet for downstream visibility
                snip_final = f"[{path}] {snippet}".strip() if snippet else f"[{path}]".strip()

                try:
                    insert_guideline_recommendation(
                        guideline_id=gid,
                        idx=int(sec_idx),
                        recommendation_text=rec_text,
                        strength_raw=strength or None,
                        evidence_raw=evidence or None,
                        source_snippet=snip_final or None,
                        element_hash=sec_hash,
                        created_at=created_at,
                    )
                    stored += 1
                except Exception:
                    pass

    return stored



# ---------------- Guideline metadata extraction ----------------

def _parse_year4(raw: str) -> str:
    s = (raw or "").strip()
    m = _GUIDELINE_YEAR_RE.search(s)
    if not m:
        return ""
    y = int(m.group(1))
    if 1900 <= y <= (datetime.now().year + 1):
        return str(y)
    return ""


def _best_year_guess_from_text(text: str) -> str:
    t = (text or "")
    if not t:
        return ""
    hits = []
    for m in _GUIDELINE_YEAR_RE.finditer(t):
        y = int(m.group(1))
        pos = m.start()
        window = t[max(0, pos - 50) : min(len(t), pos + 50)].lower()
        score = 0
        if "publish" in window or "publication" in window or "issued" in window or "release" in window:
            score += 3
        if "update" in window or "updated" in window or "revision" in window:
            score += 2
        if "copyright" in window or "©" in window:
            score += 1
        hits.append((score, y))
    if not hits:
        return ""
    hits.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = hits[0][1]
    return str(best) if 1900 <= best <= (datetime.now().year + 1) else ""


def _guideline_meta_snippet(md: str, max_chars: int = 9000) -> str:
    text = (md or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    head = "\n".join(lines[:140])

    kw_re = re.compile(
        r"(?i)\b(published|publication|issued|released|updated|update|revision|copyright|©|guideline|statement|"
        r"recommendation|consensus|society|association|college)\b"
    )

    picked = []
    seen = set()
    for ln in lines[:600]:
        if _GUIDELINE_YEAR_RE.search(ln) or kw_re.search(ln) or ln.startswith("#"):
            key = ln.lower()
            if key in seen:
                continue
            seen.add(key)
            picked.append(ln)
        if len(picked) >= 220:
            break

    blob = head + "\n\n" + "\n".join(picked)
    return blob[:max_chars].strip()


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def gpt_extract_guideline_title_year(filename: str, snippet: str) -> Dict[str, str]:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    fn = (filename or "").strip()
    sn = (snippet or "").strip()
    if not sn:
        return {"guideline_name": "", "pub_year": ""}

    instructions = (
        "You extract metadata from a clinical guideline document excerpt.\n"
        "Return ONLY valid JSON (no markdown) with this exact shape:\n"
        "{\"guideline_name\":\"...\",\"pub_year\":\"...\"}\n"
        "Rules:\n"
        "- Use ONLY what is explicitly present in the text.\n"
        "- guideline_name: the most official/primary guideline title as shown.\n"
        "- pub_year: a 4-digit year ONLY if explicitly stated as the publication year; else empty string.\n"
        "- If multiple years appear, choose the one most clearly tied to publication.\n"
        "- Strings only; never null; no extra keys."
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": f"FILENAME:\n{fn}\n\nTEXT EXCERPT:\n{sn}\n\nReturn JSON now.",
        "text": {"verbosity": "low"},
        "max_output_tokens": 220,
        "temperature": 0,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()

    raw = (_extract_output_text(r.json()) or "").strip()
    if not raw:
        return {"guideline_name": "", "pub_year": ""}

    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"(\{.*\})", raw, flags=re.DOTALL)
        if not m:
            return {"guideline_name": "", "pub_year": ""}
        try:
            obj = json.loads(m.group(1))
        except Exception:
            return {"guideline_name": "", "pub_year": ""}

    return {
        "guideline_name": (obj.get("guideline_name") or "").strip(),
        "pub_year": (obj.get("pub_year") or "").strip(),
    }


def extract_and_store_guideline_metadata_azure(guideline_id: str) -> Dict[str, str]:
    gid = (guideline_id or "").strip()
    if not gid:
        return {}

    meta = get_guideline_meta(gid)
    if not meta:
        return {}

    md = get_or_create_markdown(gid)
    if not md:
        return {}

    snippet = _guideline_meta_snippet(md)
    fn = meta.get("filename", "")

    gname = ""
    year = ""
    try:
        out = gpt_extract_guideline_title_year(fn, snippet)
        gname = (out.get("guideline_name") or "").strip()
        year = _parse_year4(out.get("pub_year") or "")
    except Exception:
        gname = ""
        year = ""

    try:
        spec = gpt_extract_specialty(gname or fn, snippet)
    except Exception:
        spec = ""

    # don't wipe manual values if extraction yields blanks
    existing = get_guideline_meta(gid) or {}
    final_name = (gname or "").strip() or (existing.get("guideline_name") or "").strip()
    final_year = (year or "").strip() or (existing.get("pub_year") or "").strip()
    final_spec = (spec or "").strip() or (existing.get("specialty") or "").strip()

    update_guideline_metadata(
        guideline_id=gid,
        guideline_name=final_name or None,
        pub_year=final_year or None,
        specialty=final_spec or None,
    )

    return {"guideline_name": final_name, "pub_year": final_year, "specialty": final_spec}


# ---------------- Meta synthesis ----------------
def _pack_study_for_meta(rec: Dict[str, str], idx: int, include_abstract: bool) -> str:
    title = (rec.get("title") or "").strip()
    journal = (rec.get("journal") or "").strip()
    year = (rec.get("year") or "").strip()
    pmid = (rec.get("pmid") or "").strip()

    header_bits = [b for b in [journal, year] if b]
    header = f"STUDY {idx}: {title or '(no title)'}" + (f" ({' • '.join(header_bits)})" if header_bits else "")
    header += f" | PMID {pmid}" if pmid else ""

    lines: List[str] = [header]

    # Mutually exclusive: either send raw abstract OR send extracted structured fields.
    if include_abstract:
        ab = (rec.get("abstract") or "").strip()
        if ab:
            ab = ab[: max(0, META_MAX_CHARS_PER_STUDY)]
            lines.append("- Abstract (truncated):")
            lines.append(ab)
        else:
            # Fall back to extracted fields if the abstract is missing.
            include_abstract = False

    if not include_abstract:
        n = (rec.get("patient_n") or "").strip()
        if n:
            lines.append(f"- N: {n}")

        design = (rec.get("study_design") or "").strip()
        if design:
            lines.append(f"- Design/setting tags: {design}")

        p = (rec.get("patient_details") or "").strip()
        if p:
            lines.append("- Population:")
            for ln in p.splitlines():
                ln = ln.strip()
                if ln:
                    lines.append(f"  {ln if ln.startswith('- ') else ('- ' + ln)}")

        ic = (rec.get("intervention_comparison") or "").strip()
        if ic:
            lines.append("- Intervention/comparator:")
            for ln in ic.splitlines():
                ln = ln.strip()
                if ln:
                    lines.append(f"  {ln if ln.startswith('- ') else ('- ' + ln)}")

        res = (rec.get("results") or "").strip()
        if res:
            lines.append("- Results:")
            for ln in res.splitlines():
                ln = ln.strip()
                if ln:
                    lines.append(f"  {ln if ln.startswith('- ') else ('- ' + ln)}")

        concl = (rec.get("authors_conclusions") or "").strip()
        if concl:
            lines.append(f"- Authors’ conclusion (from abstract): {concl}")

    packed = "\n".join(lines).strip()
    return packed[: max(0, META_MAX_CHARS_PER_STUDY)]

@st.cache_data(ttl=6 * 3600, show_spinner=False)
def gpt_generate_meta_paragraph(
    pmids_csv: str,
    focus_question: str,
    include_abstract: bool,
    tone: str,
) -> str:
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")

    pmids = [p.strip() for p in (pmids_csv or "").split(",") if p.strip()]
    if not pmids:
        return ""

    records: List[Dict[str, str]] = []
    for p in pmids:
        r = get_record(p)
        if r:
            records.append(r)

    if not records:
        return ""

    blocks = [_pack_study_for_meta(r, i, include_abstract=include_abstract) for i, r in enumerate(records, start=1)]
    studies_text = "\n\n".join(blocks).strip()

    fq = (focus_question or "").strip()
    fq_line = f"Focus question: {fq}" if fq else "Focus question: (none provided)"

    instructions = (
        "You are helping a clinician synthesize multiple studies that were saved from PubMed.\n"
        "Write ONE paragraph of high-yield interpretive thoughts across the set.\n"
        "Hard rules:\n"
        "- Use ONLY information in the provided study blocks. Do not invent details.\n"
        "- Do NOT claim a formal meta-analysis; this is a qualitative synthesis.\n"
        "- If studies conflict or are too heterogeneous/unclear, say so plainly.\n"
        "- Mention key limitations that are explicitly apparent without overreaching.\n"
        "- If a focus question is provided, orient the synthesis around it.\n"
        "- Output must be a single paragraph (no bullets, no headings).\n"
        f"- Tone: {tone}.\n"
    )

    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": f"{fq_line}\n\nSTUDIES:\n{studies_text}\n\nNow write the single-paragraph synthesis.",
        "reasoning": {"effort": "medium"},
        "text": {"verbosity": "medium"},
        "max_output_tokens": 10000,
        "store": False,
    }

    r = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()

    return (_extract_output_text(r.json()) or "").strip()
