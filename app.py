# app.py

import re
import html
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional

import pandas as pd
import requests
import streamlit as st

from pathlib import Path
from urllib.parse import quote_plus  # ✅ added

from db import (
    _db_path,
    ensure_schema,
    ensure_guidelines_schema,
    ensure_folders_schema,
    db_count,
    guidelines_count,
    db_count_all,
    is_saved,
    save_record,
    search_records,
    search_guidelines,
    list_browse_items,
    list_browse_guideline_items,
    get_record,
    delete_record,
    delete_guideline,
    save_guideline_pdf,
    list_guidelines,
    get_guideline_meta,
    update_guideline_metadata,
    list_recent_records,
    list_abstracts_for_history,
    get_guideline_recommendations_display,
    update_guideline_recommendations_display,
    get_saved_pmids,
    hide_pubmed_pmid,
    get_hidden_pubmed_pmids,
    list_folders,
    create_or_get_folder,
    add_items_to_folder,
    get_folder_item_ids,
)
from extract import (
    fetch_pubmed_xml,
    parse_abstract,
    parse_year,
    parse_journal,
    parse_title,
    get_top_neighbors,
    get_s2_similar_papers,
    search_pubmed_by_date_filters,
    gpt_extract_patient_n,
    gpt_extract_study_design,
    gpt_extract_patient_details,
    gpt_extract_intervention_comparison,
    gpt_extract_authors_conclusions,
    gpt_extract_results,
    gpt_extract_specialty,
    _parse_nonneg_int,
    _parse_tag_list,
    extract_and_store_guideline_recommendations_azure,
    extract_and_store_guideline_metadata_azure,
    _parse_year4,
    _pack_study_for_meta,
    _openai_api_key,
    _openai_model,
    _post_with_retries,
    _extract_output_text,
    OPENAI_RESPONSES_URL,
)

# silent safety caps (avoid loading/rendering huge DBs by accident)
SEARCH_MAX_DEFAULT = 1500
BROWSE_MAX_ROWS = 30000

GUIDELINES_MAX_LIST = 30000  # UI list cap
FOLDERS_MAX_LIST = 5000
META_MAX_STUDIES_HARD_CAP = 30000


# ---------------- Core helpers (UI-facing) ----------------

def _clean_pmid(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    m = re.search(r"(\d{1,10})", s)  # allows "PMID: 12345678"
    return m.group(1) if m else ""


def _split_specialties(raw: str) -> List[str]:
    """
    Split a specialty CSV/string into a de-duped list of specialties.
    Empty -> ["Unspecified"].
    """
    s = (raw or "").strip()
    if not s:
        return ["Unspecified"]
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
    return out or ["Unspecified"]


def _fmt_article(r: Dict[str, str]) -> str:
    title = (r.get("title") or "").strip() or "(no title)"
    journal = (r.get("journal") or "").strip()
    year = (r.get("year") or "").strip()

    bits: List[str] = []
    if journal:
        bits.append(journal)
    if year:
        bits.append(year)

    meta = " • ".join(bits)
    return f"{title}{f' — {meta}' if meta else ''}"


def _fmt_search_item(it: Dict[str, str]) -> str:
    if (it.get("type") or "") == "guideline":
        title = (it.get("title") or "").strip() or "(no name)"
        year = (it.get("year") or "").strip()
        meta = year  # no specialty in dropdown
        return f"{title}{f' — {meta}' if meta else ''}"
    return _fmt_article(it)


def _tags_to_md(tags_csv: str) -> str:
    s = (tags_csv or "").strip()
    if not s:
        return ""
    toks = [t.strip() for t in s.split(",") if t.strip()]
    if not toks:
        return ""
    return " ".join([f"`{t}`" for t in toks])


def _render_bullets(text: str, empty_hint: str = "—") -> None:
    s = (text or "").strip()
    if not s:
        st.markdown(empty_hint)
        return
    if not s.startswith("- "):
        s = "\n".join([("- " + ln.strip()) for ln in s.splitlines() if ln.strip()])
    st.markdown(s)


def _render_plain_text(text: str, empty_hint: str = "—") -> None:
    """
    Render plain, non-editable text in Streamlit's normal font (not a textbox),
    preserving newlines and avoiding markdown/HTML injection.
    """
    s = (text or "").strip()
    if not s:
        st.markdown(empty_hint)
        return

    safe = html.escape(s).replace("\n", "<br>")
    st.markdown(f"<div style='white-space: pre-wrap;'>{safe}</div>", unsafe_allow_html=True)


def _filter_search_pubmed_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    valid_rows: List[Dict[str, str]] = []
    pmids: List[str] = []
    for r in (rows or []):
        if not isinstance(r, dict):
            continue
        pmid = (r.get("pmid") or "").strip()
        if not pmid:
            continue
        valid_rows.append(r)
        pmids.append(pmid)

    if not valid_rows:
        return []

    saved_pmids = get_saved_pmids(pmids)
    hidden_pmids = get_hidden_pubmed_pmids(pmids)
    blocked = saved_pmids.union(hidden_pmids)
    if not blocked:
        return valid_rows

    out: List[Dict[str, str]] = []
    for r in valid_rows:
        pmid = (r.get("pmid") or "").strip()
        if pmid in blocked:
            continue
        out.append(r)
    return out


def _year_sort_key(y: str) -> Tuple[int, str]:
    ys = (y or "").strip()
    if re.fullmatch(r"\d{4}", ys):
        return (0, ys)
    if not ys:
        return (2, "0000")
    return (1, ys)

# ---------------- Guideline display editing helpers ----------------

_REC_LINE_RE = re.compile(r"^\s*-\s+\*\*Rec\s+(\d+)\.\*\*\s*(.*)$")

def _parse_rec_nums(raw: str) -> List[int]:
    """
    Accepts: "7", "7,12, 13", "Rec 7 and 12", etc.
    Returns de-duped positive ints in first-seen order.
    """
    s = (raw or "").strip()
    if not s:
        return []
    nums: List[int] = []
    seen = set()
    for tok in re.findall(r"\d+", s):
        try:
            n = int(tok)
        except Exception:
            continue
        if n <= 0 or n in seen:
            continue
        seen.add(n)
        nums.append(n)
    return nums

def _delete_recs_from_guideline_md(md: str, delete_nums: List[int]) -> Tuple[str, List[int]]:
    """
    Deletes ONLY rec bullet lines matching `- **Rec N.** ...` from the stored markdown.
    Does NOT renumber remaining Rec lines (so gaps remain).
    Also prunes empty `###` sections (when they contain nothing meaningful after deletes).

    Returns: (new_md, removed_nums_in_order)
    """
    text = (md or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    delete_set = set(int(n) for n in (delete_nums or []) if isinstance(n, int) and n > 0)
    if not delete_set:
        return (md or "").strip(), []

    removed: List[int] = []
    filtered: List[str] = []

    # 1) Remove selected rec lines
    for ln in lines:
        m = _REC_LINE_RE.match(ln)
        if m:
            try:
                old_n = int(m.group(1))
            except Exception:
                old_n = -1
            if old_n in delete_set:
                removed.append(old_n)
                continue
        filtered.append(ln)

    if not removed:
        return (md or "").strip(), []

    # 2) Prune empty `###` sections
    out: List[str] = []
    i = 0
    while i < len(filtered):
        line = filtered[i]
        if line.startswith("### "):
            heading = line
            i += 1
            block: List[str] = []
            while i < len(filtered) and not filtered[i].startswith("### "):
                block.append(filtered[i])
                i += 1

            has_rec = any(_REC_LINE_RE.match(b or "") for b in block)
            has_meaningful_nonrec = any(
                (b or "").strip()
                and not _REC_LINE_RE.match(b or "")
                for b in block
            )

            # Keep section if it still has recs OR user-added meaningful content
            if has_rec or has_meaningful_nonrec:
                out.append(heading)
                out.extend(block)
            else:
                # drop section entirely
                if out and out[-1].strip():
                    out.append("")
        else:
            out.append(line)
            i += 1

    new_md = "\n".join(out).strip()

    # Optional: if nothing remains, make it explicit
    still_has_any_rec = any(_REC_LINE_RE.match(ln or "") for ln in out)
    if not still_has_any_rec:
        if new_md:
            new_md += "\n\n_No recommendations remaining._"
        else:
            new_md = "_No recommendations remaining._"

    # de-dupe removed in order
    seen = set()
    removed_ordered: List[int] = []
    for n in removed:
        if n in seen:
            continue
        seen.add(n)
        removed_ordered.append(n)

    return new_md, removed_ordered


def _guideline_md_with_delete_links(md: str, gid: str) -> str:
    """
    Render-only: inject a subtle 🗑️ link next to each Rec N label.
    Clicking triggers ?gid=...&delrec=N (handled by query param router).
    """
    base = (md or "")
    gid_q = quote_plus((gid or "").strip())

    pat = re.compile(r"(?m)^(\s*-\s+\*\*Rec\s+(\d+)\.\*\*)(\s*)")
    def repl(m: re.Match) -> str:
        num = m.group(2)
        icon = (
            f"<a href='?gid={gid_q}&delrec={num}' target='_self' "
            f"title='Delete Rec {num}' "
            f"style='text-decoration:none; opacity:0.35; margin-left:0.25rem;'>🗑️</a>"
        )
        # keep original whitespace after the label
        return f"{m.group(1)} {icon}{m.group(3)}"

    return pat.sub(repl, base)


# --------------- Meta synthesis helpers (papers + guidelines) ---------------

def _pack_guideline_for_meta(gid: str, idx: int, max_chars: int = 12000) -> str:
    gid = (gid or "").strip()
    if not gid:
        return ""

    meta = get_guideline_meta(gid) or {}
    name = (meta.get("guideline_name") or meta.get("filename") or "").strip()
    year = (meta.get("pub_year") or "").strip()
    spec = (meta.get("specialty") or "").strip()

    header_bits: List[str] = [b for b in [name or f"Guideline {gid}", year, spec] if b]
    header = f"{idx}. " + " • ".join(header_bits)

    disp = (get_guideline_recommendations_display(gid) or "").strip()
    if not disp:
        return header + "\n- (No saved recommendations display.)"

    disp = disp[:max_chars] + ("…" if len(disp) > max_chars else "")
    return f"{header}\n\n{disp}"


def gpt_generate_meta_combined(
    pmids: List[str],
    guideline_ids: List[str],
    mode: str,
    prompt_text: str,
    include_abstract: bool,
    tone: str,
) -> str:
    """
    Generate a qualitative synthesis paragraph from a mixture of saved studies (PMIDs)
    and clinical guidelines. The output will depend on the ``mode``:

    - ``synthesize``: write a general synthesis across all sources.
    - ``answer``: answer a focused clinical question provided via ``prompt_text``.

    The function constructs textual blocks for each study (via `_pack_study_for_meta`)
    and each guideline (via `_pack_guideline_for_meta`), then calls the OpenAI
    responses API using the same mechanism as `gpt_generate_meta_paragraph`.
    """
    # Sanitize lists
    pmids = [p.strip() for p in (pmids or []) if p and p.strip()]
    guideline_ids = [g.strip() for g in (guideline_ids or []) if g and g.strip()]
    if not pmids and not guideline_ids:
        return ""
    # Build blocks for studies
    blocks: List[str] = []
    idx = 1
    for p in pmids:
        rec = get_record(p)
        if rec:
            try:
                blocks.append(_pack_study_for_meta(rec, idx, include_abstract=include_abstract))
                idx += 1
            except Exception:
                continue
    # Build blocks for guidelines
    for g in guideline_ids:
        try:
            blk = _pack_guideline_for_meta(g, idx)
            if blk:
                blocks.append(blk)
                idx += 1
        except Exception:
            continue
    if not blocks:
        return ""
    content_text = "\n\n".join(blocks).strip()
    # Mode-specific variables
    mode_clean = (mode or "").strip().lower()
    prompt_text = (prompt_text or "").strip()
    # Compose initial descriptor line depending on mode
    if mode_clean == "answer":
        descriptor_line = f"Question: {prompt_text}" if prompt_text else "Question: (none provided)"
    else:
        descriptor_line = ""
    # Base instructions similar to existing meta synthesis
    instructions_lines: List[str] = []
    if mode_clean == "answer":
        instructions_lines.append(
            "You are helping a clinician answer a focused clinical question using multiple studies and guidelines."
        )
        instructions_lines.append(
            "Write ONE paragraph that directly addresses the question using only information from the provided sources."
        )
    else:
        instructions_lines.append(
            "You are helping a clinician synthesize multiple studies and guidelines that were saved for review."
        )
        instructions_lines.append(
            "Write ONE paragraph of high-yield interpretive thoughts across the set."
        )
    # Shared hard rules
    instructions_lines.extend(
        [
            "Hard rules:",
            "- Use ONLY information in the provided blocks. Do not invent details.",
            "- Do NOT claim a formal meta-analysis; this is a qualitative synthesis.",
            "- If studies or guidelines conflict or are too heterogeneous/unclear, say so plainly.",
            "- Mention key limitations that are explicitly apparent without overreaching.",
            "- Output must be a single paragraph (no bullets, no headings).",
            "- When making a substantive claim, cite the source label(s) in parentheses (e.g., STUDY 2; GUIDELINE 5).",
            "- Tone: Clear and organized",
        ]
    )
    # Add additional orientation instructions
    if mode_clean == "answer":
        instructions_lines.append(
            "- Explicitly answer the question by summarizing the evidence across all sources."
        )
    elif prompt_text:
        # For synthesize mode with a provided prompt, orient around it
        instructions_lines.append(
            "- If a prompt is provided, orient the synthesis around it."
        )
    instructions = "\n".join(instructions_lines) + "\n"
    # Build input field
    if descriptor_line:
        input_field = f"{descriptor_line}\n\nSOURCES:\n{content_text}\n\nNow write the single-paragraph output."
    else:
        input_field = f"SOURCES:\n{content_text}\n\nNow write the single-paragraph output."
    # Prepare payload
    key = _openai_api_key()
    if not key:
        raise RuntimeError("Missing OpenAI API key. Put OPENAI_API_KEY in .streamlit/secrets.toml.")
    payload = {
        "model": _openai_model(),
        "instructions": instructions,
        "input": input_field,
        "text": {"verbosity": "medium"},
        "max_output_tokens": 10000,
        "store": False,
        "reasoning": {"effort": "medium"},
    }
    try:
        response = _post_with_retries(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        out = _extract_output_text(response.json())
        return (out or "").strip()
    except Exception as e:
        # Surface errors to caller
        raise e


# ---------------- UI ----------------

st.set_page_config(page_title="PMID → Abstract", page_icon="📄", layout="wide")
ensure_schema()
ensure_guidelines_schema()
ensure_folders_schema()

# ---------------- DB Browse → DB Search deep-links ----------------  ✅ added

def _qp_first(qp: dict, key: str) -> str:
    v = qp.get(key)
    if isinstance(v, list):
        return v[0] if v else ""
    return str(v) if v is not None else ""


def _get_query_params() -> dict:
    try:
        return dict(st.query_params)  # Streamlit newer API
    except Exception:
        try:
            return st.experimental_get_query_params()  # older API
        except Exception:
            return {}


def _clear_query_params() -> None:
    try:
        st.query_params.clear()
    except Exception:
        try:
            st.experimental_set_query_params()
        except Exception:
            pass


def _browse_search_link(*, pmid: str = "", gid: str = "") -> str:
    """
    Tiny icon link that deep-links to DB Search and opens a specific record.
    """
    if pmid:
        return (
            f"<a href='?pmid={quote_plus(pmid)}' target='_self' title='Open in DB Search' "
            f"style='text-decoration:none; opacity:0.45; margin-left:0.35rem; font-size:0.9em;'>🔎</a>"
        )
    if gid:
        return (
            f"<a href='?gid={quote_plus(gid)}' target='_self' title='Open in DB Search' "
            f"style='text-decoration:none; opacity:0.45; margin-left:0.35rem; font-size:0.9em;'>🔎</a>"
        )
    return ""


# If URL has ?pmid=... or ?gid=..., route into DB Search and open that item once
_qp = _get_query_params()
_open_pmid = _clean_pmid(_qp_first(_qp, "pmid"))
_open_gid = (_qp_first(_qp, "gid") or "").strip()
_open_delrec = (_qp_first(_qp, "delrec") or "").strip()

if _open_pmid or _open_gid:
    st.session_state["nav_page"] = "DB Search"

    # If coming from a deep link, don't let an old typed search override forced selection.
    st.session_state["db_search_any"] = ""

    if _open_pmid:
        st.session_state["db_search_open_pmid"] = _open_pmid
        st.session_state.pop("db_search_open_gid", None)
    if _open_gid:
        st.session_state["db_search_open_gid"] = _open_gid
        st.session_state.pop("db_search_open_pmid", None)

    # Optional delete trigger (used by 🗑️ links in guideline display)
    if _open_delrec:
        st.session_state["db_search_delete_rec"] = _open_delrec

        # Keep Edit mode ON after one-click deletes
        if _open_gid:
            st.session_state[f"dbs_guideline_edit_{_open_gid}"] = True

    _clear_query_params()



page = st.sidebar.radio(
    "Navigate",
    ["PMID → Abstract", "Guidelines (PDF Upload)", "DB Search", "DB Browse", "Generate meta", "Search PubMed", "Delete", "About", "History"],
    index=0,
    key="nav_page",
)


st.sidebar.caption(f"DB: `{_db_path()}`")
st.sidebar.caption(
    f"Saved: **{db_count_all()}**  "
    f"({db_count()} abstracts, {guidelines_count()} guidelines)"
)


def _format_date_added(iso_str: str) -> str:
    """Format stored ISO datetime as date only for display (e.g. 'Feb 3, 2025')."""
    s = (iso_str or "").strip()
    if not s:
        return "—"
    try:
        # Accept both "2025-02-03T14:30:00Z" and "2025-02-03"
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        # Cross-platform: no leading zero on day
        return dt.strftime("%b ") + str(dt.day) + dt.strftime(", %Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s or "—"


def render_history_page() -> None:
    st.title("📅 History")
    limit = 500
    abstracts = list_abstracts_for_history(limit=limit)
    guidelines = list_guidelines(limit=limit)
    # Combined list: (sort_key, date_display, type_label, title)
    rows: List[Tuple[str, str, str, str]] = []
    for it in abstracts:
        raw = (it.get("uploaded_at") or "").strip()
        rows.append((raw or "0000", _format_date_added(raw), "Abstract", (it.get("title") or "").strip() or "(no title)"))
    for it in guidelines:
        raw = (it.get("uploaded_at") or "").strip()
        title = (it.get("guideline_name") or it.get("filename") or "").strip() or "(no name)"
        rows.append((raw or "0000", _format_date_added(raw), "Guideline", title))
    rows.sort(key=lambda r: r[0], reverse=True)
    if not rows:
        st.markdown("Nothing added yet.")
        return
    lines = [f"- **{r[1]}** · {r[2]} · {r[3]}" for r in rows]
    st.markdown("\n".join(lines))


def render_search_pubmed_page() -> None:
    st.title("🔎 Search PubMed")
    st.caption("Search PubMed by publication date, journal, and study type.")

    today = datetime.now(timezone.utc).date()
    default_start = today - timedelta(days=365)

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start date", value=default_start, key="search_pubmed_start")
    with c2:
        end_date = st.date_input("End date", value=today, key="search_pubmed_end")

    journal_query_by_label = {
        "NEJM": '"N Engl J Med"[jour]',
        "JAMA": '"JAMA"[jour]',
        "Lancet": '"Lancet"[jour]',
    }
    study_type_queries = {
        "Clinical Trial": ['"Clinical Trial"[Publication Type]'],
        "Meta analysis": ['"Meta-Analysis"[Publication Type]'],
        "Both": [
            '"Clinical Trial"[Publication Type]',
            '"Meta-Analysis"[Publication Type]',
        ],
    }

    c3, c4 = st.columns(2)
    with c3:
        journal_label = st.selectbox(
            "Select Journal",
            options=list(journal_query_by_label.keys()),
            index=0,
            key="search_pubmed_journal",
        )
    with c4:
        study_type_label = st.selectbox(
            "Study type filter",
            options=list(study_type_queries.keys()),
            index=0,
            key="search_pubmed_study_type",
        )

    if st.button("Search", type="primary", width="stretch", key="search_pubmed_btn"):
        if start_date > end_date:
            st.error("Start date must be on or before end date.")
        else:
            start_s = start_date.strftime("%Y/%m/%d")
            end_s = end_date.strftime("%Y/%m/%d")
            try:
                with st.spinner("Searching PubMed…"):
                    rows = search_pubmed_by_date_filters(
                        start_s,
                        end_s,
                        journal_term=journal_query_by_label.get(journal_label, ""),
                        publication_type_terms=study_type_queries.get(study_type_label, []),
                    )
                st.session_state["search_pubmed_rows"] = rows
                st.session_state["search_pubmed_range"] = {"start": start_s, "end": end_s}
                st.session_state["search_pubmed_filters"] = {
                    "journal": journal_label,
                    "study_type": study_type_label,
                }
            except requests.HTTPError as e:
                st.error(f"PubMed search failed: {e}")
            except Exception as e:
                st.error(f"Unexpected search error: {e}")

    if "search_pubmed_rows" not in st.session_state:
        st.info("Choose a date range and click Search.")
        return

    rows = st.session_state.get("search_pubmed_rows") or []
    rows = _filter_search_pubmed_rows(rows)
    rng = st.session_state.get("search_pubmed_range") or {}
    start_s = (rng.get("start") or "").strip()
    end_s = (rng.get("end") or "").strip()
    filters = st.session_state.get("search_pubmed_filters") or {}
    journal_label = (filters.get("journal") or "").strip()
    study_type_label = (filters.get("study_type") or "").strip()
    if start_s and end_s:
        st.caption(f"Range: {start_s} to {end_s}")
    if journal_label or study_type_label:
        st.caption(f"Filters: {journal_label or '—'} • {study_type_label or '—'}")
    st.caption("Saved articles and items marked `Don't show again` are automatically excluded.")

    if not rows:
        st.info("No matching articles found for this date range and filter selection.")
        return

    st.success(f"Found {len(rows)} result(s).")
    for r in rows:
        title = (r.get("title") or "").strip() or "(no title)"
        pmid = (r.get("pmid") or "").strip() or "—"
        c_left, c_right = st.columns([5, 2])
        with c_left:
            st.markdown(f"- {title} — `{pmid}`")
        with c_right:
            if pmid != "—" and st.button(
                "Don't show again",
                key=f"search_pubmed_hide_{pmid}",
                width="stretch",
            ):
                hide_pubmed_pmid(pmid)
                st.rerun()


def render_help_about_page() -> None:
    st.title("ℹ️ About")

    # Read README.md from the repo root (same folder as app.py)
    readme_path_candidates = [
        Path(__file__).with_name("README.md"),
        Path("README.md"),
    ]

    md = ""
    for p in readme_path_candidates:
        try:
            if p.exists() and p.is_file():
                md = p.read_text(encoding="utf-8", errors="ignore")
                break
        except Exception:
            pass

    if not md.strip():
        st.warning(
            "README.md wasn't found next to app.py. "
            "Make sure README.md is committed to the repo root so it can be shown here."
        )
        return

    st.markdown(md)


# =======================
# Page: PMID --> Abstract
# =======================
if page == "PMID → Abstract":
    st.title("📄 PMID → Abstract")

    if "pmid_input" not in st.session_state:
        st.session_state["pmid_input"] = (st.session_state.get("last_pmid") or "")

    pmid_in = st.text_input("PMID", placeholder="e.g., 37212345", key="pmid_input")
    pmid = _clean_pmid(pmid_in)

    fetch_clicked = st.button("Fetch", type="primary", width="stretch")

    if fetch_clicked:
        if not pmid:
            st.error("Please enter a valid numeric PMID.")
            st.stop()

        if is_saved(pmid):
            for k in ["last_pmid", "last_abstract", "last_year", "last_journal", "last_title"]:
                st.session_state.pop(k, None)
            st.info(f"PMID {pmid} is saved in your database.")
            st.stop()

        with st.spinner("Fetching…"):
            try:
                xml_text = fetch_pubmed_xml(pmid)
                abstract = parse_abstract(xml_text)
                year = parse_year(xml_text)
                journal = parse_journal(xml_text)
                title = parse_title(xml_text)

                st.session_state["last_pmid"] = pmid
                st.session_state["last_abstract"] = abstract
                st.session_state["last_year"] = year
                st.session_state["last_journal"] = journal
                st.session_state["last_title"] = title
            except requests.HTTPError as e:
                st.error(f"PubMed request failed: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.stop()

        st.session_state["gpt_patient_n_error"] = ""
        st.session_state["gpt_design_error"] = ""
        st.session_state["gpt_details_error"] = ""
        st.session_state["gpt_ic_error"] = ""
        st.session_state["gpt_conclusions_error"] = ""
        st.session_state["gpt_results_error"] = ""
        st.session_state["gpt_specialty_error"] = ""

        if (st.session_state.get("last_abstract") or "").strip():
            try:
                with st.spinner("Extracting patient count…"):
                    n = gpt_extract_patient_n(
                        st.session_state.get("last_title") or "",
                        st.session_state.get("last_abstract") or "",
                    )
                    st.session_state["gpt_patient_n"] = int(n)
                    st.session_state["patient_n_input"] = str(int(n))
            except Exception as e:
                st.session_state["gpt_patient_n_error"] = str(e)
                st.session_state["gpt_patient_n"] = 0
                st.session_state["patient_n_input"] = ""

            try:
                with st.spinner("Extracting study design…"):
                    design = gpt_extract_study_design(
                        st.session_state.get("last_title") or "",
                        st.session_state.get("last_abstract") or "",
                    )
                    st.session_state["gpt_study_design"] = design
                    st.session_state["study_design_input"] = design
            except Exception as e:
                st.session_state["gpt_design_error"] = str(e)
                st.session_state["gpt_study_design"] = ""
                st.session_state["study_design_input"] = ""

            try:
                with st.spinner("Extracting patient details…"):
                    details = gpt_extract_patient_details(
                        st.session_state.get("last_title") or "",
                        st.session_state.get("last_abstract") or "",
                        int(st.session_state.get("gpt_patient_n") or 0),
                        st.session_state.get("gpt_study_design") or "",
                    )
                    st.session_state["gpt_patient_details"] = details
                    st.session_state["patient_details_input"] = details
            except Exception as e:
                st.session_state["gpt_details_error"] = str(e)
                st.session_state["gpt_patient_details"] = ""
                st.session_state["patient_details_input"] = ""

            try:
                with st.spinner("Extracting intervention/comparison…"):
                    ic = gpt_extract_intervention_comparison(
                        st.session_state.get("last_title") or "",
                        st.session_state.get("last_abstract") or "",
                        int(st.session_state.get("gpt_patient_n") or 0),
                        st.session_state.get("gpt_study_design") or "",
                        st.session_state.get("gpt_patient_details") or "",
                    )
                    st.session_state["gpt_intervention_comparison"] = ic
                    st.session_state["intervention_comparison_input"] = ic
            except Exception as e:
                st.session_state["gpt_ic_error"] = str(e)
                st.session_state["gpt_intervention_comparison"] = ""
                st.session_state["intervention_comparison_input"] = ""

            try:
                with st.spinner("Extracting authors' conclusions…"):
                    concl = gpt_extract_authors_conclusions(
                        st.session_state.get("last_title") or "",
                        st.session_state.get("last_abstract") or "",
                        int(st.session_state.get("gpt_patient_n") or 0),
                        st.session_state.get("gpt_study_design") or "",
                        st.session_state.get("gpt_patient_details") or "",
                        st.session_state.get("gpt_intervention_comparison") or "",
                    )
                    st.session_state["gpt_authors_conclusions"] = concl
                    st.session_state["authors_conclusions_input"] = concl
            except Exception as e:
                st.session_state["gpt_conclusions_error"] = str(e)
                st.session_state["gpt_authors_conclusions"] = ""
                st.session_state["authors_conclusions_input"] = ""

            try:
                with st.spinner("Extracting results…"):
                    res = gpt_extract_results(
                        st.session_state.get("last_title") or "",
                        st.session_state.get("last_abstract") or "",
                        int(st.session_state.get("gpt_patient_n") or 0),
                        st.session_state.get("gpt_study_design") or "",
                        st.session_state.get("gpt_patient_details") or "",
                        st.session_state.get("gpt_intervention_comparison") or "",
                    )
                    st.session_state["gpt_results"] = res
                    st.session_state["results_input"] = res
            except Exception as e:
                st.session_state["gpt_results_error"] = str(e)
                st.session_state["gpt_results"] = ""
                st.session_state["results_input"] = ""

            try:
                with st.spinner("Extracting specialty…"):
                    spec = gpt_extract_specialty(
                        st.session_state.get("last_title") or "",
                        st.session_state.get("last_abstract") or "",
                    )
                    st.session_state["gpt_specialty"] = spec
                    st.session_state["specialty_input"] = spec
            except Exception as e:
                st.session_state["gpt_specialty_error"] = str(e)
                st.session_state["gpt_specialty"] = ""
                st.session_state["specialty_input"] = ""
        else:
            st.session_state["gpt_patient_n"] = 0
            st.session_state["patient_n_input"] = ""
            st.session_state["gpt_study_design"] = ""
            st.session_state["study_design_input"] = ""
            st.session_state["gpt_patient_details"] = ""
            st.session_state["patient_details_input"] = ""
            st.session_state["gpt_intervention_comparison"] = ""
            st.session_state["intervention_comparison_input"] = ""
            st.session_state["gpt_authors_conclusions"] = ""
            st.session_state["authors_conclusions_input"] = ""
            st.session_state["gpt_results"] = ""
            st.session_state["results_input"] = ""
            st.session_state["gpt_specialty"] = ""
            st.session_state["specialty_input"] = ""

    last_pmid = st.session_state.get("last_pmid")
    last_abstract = (st.session_state.get("last_abstract") or "").strip()
    last_year = (st.session_state.get("last_year") or "").strip()
    last_journal = (st.session_state.get("last_journal") or "").strip()
    last_title = (st.session_state.get("last_title") or "").strip()

    if last_pmid:
        left, right = st.columns([2, 1], gap="large")

        with left:
            st.markdown(f"[Open in PubMed](https://pubmed.ncbi.nlm.nih.gov/{last_pmid}/)")

            if last_title:
                st.subheader(last_title)

            meta_bits = []
            if last_journal:
                meta_bits.append(last_journal)
            if last_year:
                meta_bits.append(last_year)
            if meta_bits:
                st.caption(" • ".join(meta_bits))

            if last_abstract:
                already_saved_now = is_saved(last_pmid)

                if already_saved_now:
                    st.info("This PMID is saved in your database.")
                else:
                    if st.button("Add to database", width="stretch"):
                        raw_n = st.session_state.get("patient_n_input", "")
                        parsed_n = _parse_nonneg_int(raw_n)

                        raw_design = (st.session_state.get("study_design_input", "") or "").strip()
                        parsed_design = raw_design if raw_design else None

                        raw_details = (st.session_state.get("patient_details_input", "") or "").strip()
                        parsed_details = raw_details if raw_details else None

                        raw_ic = (st.session_state.get("intervention_comparison_input", "") or "").strip()
                        parsed_ic = raw_ic if raw_ic else None

                        raw_concl = (st.session_state.get("authors_conclusions_input", "") or "").strip()
                        parsed_concl = raw_concl if raw_concl else None

                        raw_results = (st.session_state.get("results_input", "") or "").strip()
                        parsed_results = raw_results if raw_results else None

                        raw_spec = (st.session_state.get("specialty_input") or "").strip()
                        parsed_spec = _parse_tag_list(raw_spec) or None

                        if raw_n.strip() and parsed_n is None:
                            st.error("Patient count must be a single integer (or leave blank).")
                        else:
                            try:
                                save_record(
                                    last_pmid,
                                    last_title,
                                    last_abstract,
                                    last_year,
                                    last_journal,
                                    parsed_n,
                                    parsed_design,
                                    parsed_details,
                                    parsed_ic,
                                    parsed_concl,
                                    parsed_results,
                                    parsed_spec,
                                )
                                st.success("Saved.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to save: {e}")

                _render_plain_text(last_abstract)
                st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
            else:
                st.warning("No abstract found for this PMID (or PubMed returned no AbstractText).")

            with st.expander("Pubmed Related articles (top 5)"):
                try:
                    neighbors = get_top_neighbors(last_pmid, top_n=5)
                    if not neighbors:
                        st.info("No related articles returned.")
                    else:
                        for n in neighbors:
                            st.markdown(
                                f"- [{n['title'] or n['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{n['pmid']}/) — `{n['pmid']}`"
                            )
                except requests.HTTPError as e:
                    st.error(f"Neighbors lookup failed: {e}")
                except Exception as e:
                    st.error(f"Neighbors lookup error: {e}")

            with st.expander("Semantic Scholar similar papers (top 5)"):
                try:
                    s2_papers = get_s2_similar_papers(last_pmid, top_n=5)
                    if not s2_papers:
                        st.info("No Semantic Scholar recommendations returned.")
                    else:
                        for p in s2_papers:
                            title = (p.get("title") or "").strip() or (p.get("pmid") or p.get("paperId") or "(no title)")
                            url = (p.get("url") or "").strip()
                            tag = ""
                            if (p.get("pmid") or "").strip():
                                tag = f" — `{p['pmid']}`"
                            elif (p.get("paperId") or "").strip():
                                tag = f" — `{p['paperId']}`"
                            if url:
                                st.markdown(f"- [{title}]({url}){tag}")
                            else:
                                st.markdown(f"- {title}{tag}")
                except ValueError as e:
                    st.warning(str(e))
                except requests.HTTPError as e:
                    st.error(f"Semantic Scholar lookup failed: {e}")
                except Exception as e:
                    st.error(f"Semantic Scholar lookup error: {e}")

        with right:
            cerr = (st.session_state.get("gpt_conclusions_error") or "").strip()
            if cerr:
                st.error(cerr)
            st.text_area(
                "Author's conclusions",
                key="authors_conclusions_input",
                placeholder="Near-verbatim conclusion statement (no numbers).",
                height=110,
            )

            st.divider()

            serr = (st.session_state.get("gpt_specialty_error") or "").strip()
            if serr:
                st.error(serr)
            st.text_input("Specialty", key="specialty_input", placeholder="e.g., Infectious Disease, Critical Care")

            st.divider()

            err = (st.session_state.get("gpt_patient_n_error") or "").strip()
            if err:
                st.error(err)
            st.text_input("Total patients", key="patient_n_input", placeholder="e.g., 250")

            st.divider()

            derr = (st.session_state.get("gpt_design_error") or "").strip()
            if derr:
                st.error(derr)
            st.text_area(
                "Study design tags",
                key="study_design_input",
                placeholder="e.g., Randomized controlled trial, Double-blind, Multicenter, USA",
                height=110,
            )

            st.divider()

            perr = (st.session_state.get("gpt_details_error") or "").strip()
            if perr:
                st.error(perr)
            st.text_area(
                "Patient details",
                key="patient_details_input",
                placeholder="- Adults ≥18 years with ...\n- Excluded if ...\n- Mean age ...\n- % male ...",
                height=160,
            )

            st.divider()

            icerr = (st.session_state.get("gpt_ic_error") or "").strip()
            if icerr:
                st.error(icerr)
            st.text_area(
                "Intervention / comparison",
                key="intervention_comparison_input",
                placeholder="- Intervention: ...\n- Comparator: ...\n- Dose/duration: ...",
                height=140,
            )

            st.divider()

            rerr = (st.session_state.get("gpt_results_error") or "").strip()
            if rerr:
                st.error(rerr)
            st.text_area(
                "Results",
                key="results_input",
                placeholder="- Primary outcome: ... (effect estimate, CI)\n- Secondary outcome: ...",
                height=200,
            )

# =======================
# Page: DB Search
# =======================
elif page == "DB Search":
    st.title("📚 Database")

    # ✅ deep-link open support
    forced_selected: Optional[Dict[str, str]] = None
    open_pmid = (st.session_state.get("db_search_open_pmid") or "").strip()
    open_gid = (st.session_state.get("db_search_open_gid") or "").strip()

    if open_pmid:
        forced_selected = {"type": "paper", "pmid": open_pmid}
    elif open_gid:
        forced_selected = {"type": "guideline", "guideline_id": open_gid}

    q = st.text_input(
        "Search",
        placeholder="Search anything (title, abstract text, intervention, journal, etc)…",
        key="db_search_any",
    )

    # If user starts typing, stop forcing the opened item
    if (q or "").strip():
        st.session_state.pop("db_search_open_pmid", None)
        st.session_state.pop("db_search_open_gid", None)
        forced_selected = None

    rows: List[Dict[str, str]] = []
    selected: Optional[Dict[str, str]] = None

    if (q or "").strip():
        paper_rows = search_records(limit=SEARCH_MAX_DEFAULT, q=q)
        guideline_rows = search_guidelines(limit=SEARCH_MAX_DEFAULT, q=q)

        rows.extend(guideline_rows)
        rows.extend(paper_rows)

        if not rows:
            st.warning("No matches.")
            st.stop()

        selected = st.selectbox("Results", options=rows, format_func=_fmt_search_item, index=0)

    elif forced_selected:
        selected = forced_selected

    else:
        st.info("Type to search.")
        st.stop()

    if (selected.get("type") or "") != "guideline":
        selected_pmid = selected["pmid"]
        rec = get_record(selected_pmid)
        if not rec:
            st.error("Could not load that record.")
            st.stop()

        st.markdown(f"[Open in PubMed](https://pubmed.ncbi.nlm.nih.gov/{selected_pmid}/) — `{selected_pmid}`")

        title = (rec.get("title") or "").strip()
        if title:
            st.subheader(title)

        meta_bits = []
        if rec.get("journal"):
            meta_bits.append(rec["journal"])
        if rec.get("year"):
            meta_bits.append(rec["year"])
        if meta_bits:
            st.caption(" • ".join(meta_bits))

        c1, c2, c3 = st.columns([1, 1, 2], gap="large")
        with c1:
            st.metric("Patients (N)", rec.get("patient_n") or "—")
        with c2:
            st.metric("Specialty", rec.get("specialty") or "—")
        with c3:
            tags_md = _tags_to_md(rec.get("study_design") or "")
            st.markdown(tags_md if tags_md else " ")

        st.divider()

        st.markdown("### P — Population")
        _render_bullets(rec.get("patient_details") or "", empty_hint="—")

        st.markdown("### I/C — Intervention / Comparison")
        _render_bullets(rec.get("intervention_comparison") or "", empty_hint="—")

        st.markdown("### O — Outcomes / Results")
        _render_bullets(rec.get("results") or "", empty_hint="—")

        concl = (rec.get("authors_conclusions") or "").strip()
        if concl:
            st.markdown("### Authors’ conclusion")
            st.markdown(concl)

        abstract = (rec.get("abstract") or "").strip()
        if abstract:
            with st.expander("Original abstract"):
                _render_plain_text(abstract)

        with st.expander("PubMed Related articles (top 5)"):
            try:
                neighbors = get_top_neighbors(selected_pmid, top_n=5)
                if not neighbors:
                    st.info("No related articles returned.")
                else:
                    for n in neighbors:
                        st.markdown(
                            f"- [{n['title'] or n['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{n['pmid']}/) — `{n['pmid']}`"
                        )
            except requests.HTTPError as e:
                st.error(f"Neighbors lookup failed: {e}")
            except Exception as e:
                st.error(f"Neighbors lookup error: {e}")

        with st.expander("Semantic Scholar similar papers (top 5)"):
            try:
                s2_papers = get_s2_similar_papers(selected_pmid, top_n=5)
                if not s2_papers:
                    st.info("No Semantic Scholar recommendations returned.")
                else:
                    for p in s2_papers:
                        title = (p.get("title") or "").strip() or (p.get("pmid") or p.get("paperId") or "(no title)")
                        url = (p.get("url") or "").strip()
                        tag = ""
                        if (p.get("pmid") or "").strip():
                            tag = f" — `{p['pmid']}`"
                        elif (p.get("paperId") or "").strip():
                            tag = f" — `{p['paperId']}`"
                        if url:
                            st.markdown(f"- [{title}]({url}){tag}")
                        else:
                            st.markdown(f"- {title}{tag}")
            except ValueError as e:
                st.warning(str(e))
            except requests.HTTPError as e:
                st.error(f"Semantic Scholar lookup failed: {e}")
            except Exception as e:
                st.error(f"Semantic Scholar lookup error: {e}")

    else:
        gid = (selected.get("guideline_id") or "").strip()
        meta = get_guideline_meta(gid) or {}
        title = (meta.get("guideline_name") or "").strip() or (meta.get("filename") or "").strip() or (selected.get("title") or "")
        st.subheader(f"📘 {title}")

        # Show guideline metadata (optional)
        bits = []
        y = (meta.get("pub_year") or "").strip()
        s = (meta.get("specialty") or "").strip()
        if y:
            bits.append(y)
        if s:
            bits.append(s)
        if bits:
            st.caption(" • ".join(bits))

        st.divider()

        # --- One-click delete support via ?gid=...&delrec=N ---
        pending_del = (st.session_state.pop("db_search_delete_rec", "") or "").strip()
        if pending_del:
            nums = _parse_rec_nums(pending_del)
            if nums:
                cur = (get_guideline_recommendations_display(gid) or "").strip()
                new_md, removed = _delete_recs_from_guideline_md(cur, nums)
                if removed:
                    update_guideline_recommendations_display(gid, new_md)
                    st.session_state[f"dbs_guideline_edit_{gid}"] = True  # keep Edit on
                    st.success(f"Deleted: {', '.join([f'Rec {n}' for n in removed])}")
                else:
                    st.info("No matching recommendation numbers found.")

        # Reload after any possible update above
        disp = (get_guideline_recommendations_display(gid) or "").strip()

        # Tiny edit toggle (keeps default view clean)
        cL, cR = st.columns([6, 1], gap="small")
        with cR:
            edit_mode = st.toggle(
                "Quick Delete",
                value=False,
                key=f"dbs_guideline_edit_{gid}",
            )
        with cL:
            if edit_mode:
                st.caption("Click 🗑️ to delete a recommendation permanently. Recommendations can also be edited in the Guidelines page.")

        # Render
        if disp:
            if edit_mode:
                st.markdown(_guideline_md_with_delete_links(disp, gid), unsafe_allow_html=True)
            else:
                st.markdown(disp)
        else:
            st.info("No clinician-friendly recommendations display saved for this guideline yet.")


# =======================
# Page: DB Browse
# =======================
elif page == "DB Browse":
    st.title("🗂️ Browse")

    by_specialty = st.toggle(
        "Browse by specialty",
        value=False,
        key="browse_by_specialty",
        help="On: Specialty → Year. Off: Year only.",
    )

    items: List[Dict[str, str]] = []
    items.extend(list_browse_items(limit=BROWSE_MAX_ROWS))
    items.extend(list_browse_guideline_items(limit=BROWSE_MAX_ROWS))

    if not items:
        st.info("No saved articles yet.")
        st.stop()

    if by_specialty:
        grouped: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        for it in items:
            year = (it.get("year") or "").strip() or "Unknown"
            for spec in _split_specialties(it.get("specialty") or ""):
                grouped.setdefault(spec, {}).setdefault(year, []).append(it)

        specialties = sorted(grouped.keys(), key=lambda s: (s == "Unspecified", s.lower()))

        for spec in specialties:
            years_map = grouped.get(spec, {})
            years = sorted(years_map.keys(), key=_year_sort_key)
            years = list(reversed(years))

            with st.expander(spec, expanded=False):
                for y in years:
                    st.markdown(f"**{y}**")
                    for it in years_map.get(y, []):
                        if (it.get("type") or "") == "guideline":
                            title = (it.get("title") or "").strip() or "(no name)"
                            gid = (it.get("guideline_id") or "").strip()
                            safe_title = html.escape(title)
                            if gid:
                                st.markdown(f"- {safe_title}{_browse_search_link(gid=gid)}", unsafe_allow_html=True)
                            else:
                                st.markdown(f"- {safe_title}", unsafe_allow_html=True)
                        else:
                            pmid = it.get("pmid") or ""
                            title = (it.get("title") or "").strip() or "(no title)"
                            concl = (it.get("authors_conclusions") or "").strip()

                            pub_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                            safe_title = html.escape(title)
                            safe_pmid = html.escape(pmid)
                            st.markdown(
                                f"- <a href='{pub_url}' target='_blank'>{safe_title}</a> — <code>{safe_pmid}</code>{_browse_search_link(pmid=pmid)}",
                                unsafe_allow_html=True,
                            )

                            j = (it.get("journal") or "").strip()
                            pn = (it.get("patient_n") or "").strip()

                            meta_bits = []
                            if pn:
                                meta_bits.append(f"N={pn}")
                            if j:
                                meta_bits.append(j)
                            meta = ", ".join(meta_bits)

                            if concl:
                                st.caption(f"{concl}{f' ({meta})' if meta else ''}")
                            elif meta:
                                st.caption(f"({meta})")

                    st.markdown("")
    else:
        by_year: Dict[str, List[Dict[str, str]]] = {}
        for it in items:
            year = (it.get("year") or "").strip() or "Unknown"
            by_year.setdefault(year, []).append(it)

        years = sorted(by_year.keys(), key=_year_sort_key)
        years = list(reversed(years))

        for idx, y in enumerate(years):
            if idx > 0:
                st.markdown("---")
            st.markdown(f"### {y}")

            rows = by_year.get(y, [])
            rows = sorted(
                rows,
                key=lambda r: (
                    (r.get("type") or "").lower(),
                    (r.get("title") or "").lower(),
                    (r.get("pmid") or "").lower(),
                ),
            )

            for it in rows:
                if (it.get("type") or "") == "guideline":
                    title = (it.get("title") or "").strip() or "(no name)"
                    gid = (it.get("guideline_id") or "").strip()
                    safe_title = html.escape(title)
                    if gid:
                        st.markdown(f"- {safe_title}{_browse_search_link(gid=gid)}", unsafe_allow_html=True)
                    else:
                        st.markdown(f"- {safe_title}", unsafe_allow_html=True)
                else:
                    pmid = it.get("pmid") or ""
                    title = (it.get("title") or "").strip() or "(no title)"
                    concl = (it.get("authors_conclusions") or "").strip()

                    pub_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    safe_title = html.escape(title)
                    safe_pmid = html.escape(pmid)
                    st.markdown(
                        f"- <a href='{pub_url}' target='_blank'>{safe_title}</a> — <code>{safe_pmid}</code>{_browse_search_link(pmid=pmid)}",
                        unsafe_allow_html=True,
                    )

                    j = (it.get("journal") or "").strip()
                    pn = (it.get("patient_n") or "").strip()

                    meta_bits = []
                    if pn:
                        meta_bits.append(f"N={pn}")
                    if j:
                        meta_bits.append(j)
                    meta = ", ".join(meta_bits)

                    if concl:
                        st.caption(f"{concl}{f' ({meta})' if meta else ''}")
                    elif meta:
                        st.caption(f"({meta})")

# =======================
# Page: Guidelines (PDF Upload + Azure Extract)
# =======================
elif page == "Guidelines (PDF Upload)":
    st.title("📄 Guidelines — Upload PDF")

    # ---- One-button flow: Upload → Save → Extract metadata → Extract recommendations ----
    up = st.file_uploader("Upload a guideline PDF", type=["pdf"], accept_multiple_files=False)
    if up is not None:
        pdf_bytes = up.getvalue()

        if st.button("Upload + Extract", type="primary", width="stretch", key="guidelines_upload_extract_btn"):
            try:
                with st.spinner("Saving PDF…"):
                    rec = save_guideline_pdf(up.name, pdf_bytes)
                gid_saved = (rec.get("guideline_id") or "").strip()

                # Ultra-minimal dedupe behavior:
                # If this exact PDF was uploaded before AND we already have a final display, do nothing.
                existing_disp = (get_guideline_recommendations_display(gid_saved) or "").strip()
                if existing_disp:
                    st.session_state["guidelines_last_saved"] = gid_saved
                    st.info("This PDF already exists in your database (final display already saved). Skipping extraction.")
                    st.rerun()

                if not gid_saved:
                    st.error("Save succeeded but returned no guideline_id.")
                    st.stop()

                # Extract metadata
                extracted_meta: Dict[str, str] = {}
                try:
                    with st.spinner("Extracting metadata (name/year/specialty)…"):
                        outm = extract_and_store_guideline_metadata_azure(gid_saved, pdf_bytes)
                    if isinstance(outm, dict):
                        extracted_meta = {
                            "gid": gid_saved,
                            "name": str(outm.get("guideline_name") or "").strip(),
                            "year": str(outm.get("pub_year") or "").strip(),
                            "spec": str(outm.get("specialty") or "").strip(),
                        }
                except Exception:
                    extracted_meta = {}

                # Recommendations: only extract if none exist
                n_recs = 0
                disp_now = (get_guideline_recommendations_display(gid_saved) or "").strip()
                if disp_now:
                    st.info("This guideline already has a saved recommendations display; skipping extraction.")
                else:
                    # --- richer, phase-aware progress UI (replaces vague "Processing") ---
                    phase_ph = st.empty()
                    detail_ph = st.empty()
                    prog_ph = st.empty()

                    def _cb(done, total, msg="Working…", detail=""):
                        m = (msg or "").strip()
                        d = (detail or "").strip()

                        if m:
                            phase_ph.caption(m)

                        if total and total > 0:
                            try:
                                frac = float(done) / float(total)
                            except Exception:
                                frac = 0.0
                            pct = int(max(0, min(100, round(frac * 100))))
                            prog_ph.progress(pct)

                            if d:
                                detail_ph.caption(f"{d} ({done}/{total})")
                            else:
                                detail_ph.caption(f"{done}/{total}")
                        else:
                            # hide bar when we don't have a meaningful denominator
                            prog_ph.empty()
                            detail_ph.caption(d if d else "")


                    with st.spinner("Extracting recommendations + generating final display…"):
                        n_recs = extract_and_store_guideline_recommendations_azure(gid_saved, pdf_bytes, progress_cb=_cb)


                st.success(f"Done. Guideline ID: `{gid_saved}` • Extracted recommendations: {n_recs if n_recs else '—'}")
                st.rerun()

            except Exception as e:
                st.error(f"Upload/extract failed: {e}")

    st.divider()

    rows = list_guidelines(limit=GUIDELINES_MAX_LIST)
    if not rows:
        st.info("No guideline PDFs uploaded yet.")
        st.stop()

    def _fmt_g(g):
        name = (g.get("guideline_name") or "").strip() or (g.get("filename") or "")
        year = (g.get("pub_year") or "").strip()
        spec = (g.get("specialty") or "").strip()
        bits = [b for b in [year, spec] if b]
        meta = (" • ".join(bits) + " — ") if bits else ""
        return f"{name} — {meta}{g.get('uploaded_at','')}"

    default_gid = (st.session_state.get("guidelines_last_saved") or "").strip()
    default_idx = 0
    if default_gid:
        for i, r in enumerate(rows):
            if (r.get("guideline_id") or "") == default_gid:
                default_idx = i
                break

    chosen = st.selectbox("Choose a guideline", options=rows, format_func=_fmt_g, index=default_idx)
    gid = (chosen.get("guideline_id") or "").strip()

    if st.session_state.get("guideline_meta_loaded_gid") != gid:
        st.session_state["guideline_meta_loaded_gid"] = gid
        st.session_state["guideline_meta_name"] = (chosen.get("guideline_name") or "").strip()
        st.session_state["guideline_meta_year"] = (chosen.get("pub_year") or "").strip()
        st.session_state["guideline_meta_spec"] = (chosen.get("specialty") or "").strip()

    # ---- Apply pending extracted metadata BEFORE widgets are instantiated ----
    pending = st.session_state.pop("guideline_meta_pending", None)
    if isinstance(pending, dict) and (pending.get("gid") or "") == gid:
        st.session_state["guideline_meta_name"] = (pending.get("name") or "").strip()
        st.session_state["guideline_meta_year"] = (pending.get("year") or "").strip()
        st.session_state["guideline_meta_spec"] = (pending.get("spec") or "").strip()

    st.divider()
    st.subheader("Guideline metadata")

    m1, m2, m3, m4 = st.columns([2, 1, 1, 1], gap="large")

    with m1:
        st.text_input("Name", key="guideline_meta_name", placeholder=(chosen.get("filename") or "Guideline name"))
    with m2:
        st.text_input("Published year", key="guideline_meta_year", placeholder="e.g., 2023")
    with m3:
        st.text_input("Specialty", key="guideline_meta_spec", placeholder="e.g., Cardiology, Critical Care")

    with m4:
        if st.button("Save metadata (if changed)", type="primary", width="stretch", key="guideline_meta_save"):
            name_raw = (st.session_state.get("guideline_meta_name") or "").strip()
            year_raw = (st.session_state.get("guideline_meta_year") or "").strip()
            spec_raw = (st.session_state.get("guideline_meta_spec") or "").strip()

            year_parsed = _parse_year4(year_raw) if year_raw else ""
            if year_raw and not year_parsed:
                st.error("Published year must be a 4-digit year (e.g., 2023) or blank.")
            else:
                try:
                    update_guideline_metadata(
                        guideline_id=gid,
                        guideline_name=name_raw or None,
                        pub_year=year_parsed or None,
                        specialty=_parse_tag_list(spec_raw) or None,
                    )
                    st.success("Metadata saved.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save metadata: {e}")

    meta = get_guideline_meta(gid)

    st.divider()

     # =======================
    # Clinician-friendly display (editable)
    # =======================
    st.markdown("##### Clinician-friendly recommendations display (editable)")

    # Load display into session state when guideline changes
    if st.session_state.get("guideline_display_loaded_gid") != gid:
        st.session_state["guideline_display_loaded_gid"] = gid
        st.session_state["guideline_display_md"] = get_guideline_recommendations_display(gid) or ""

    st.text_area(
        "Display (Markdown)",
        key="guideline_display_md",
        height=520,
        placeholder="Saved clinician-friendly display (Markdown). You can edit freely and click Save.",
    )

    cA, cC = st.columns([1, 2], gap="large")

    with cA:
        if st.button("Save display", type="primary", width="stretch", key=f"guideline_disp_save_{gid}"):
            try:
                update_guideline_recommendations_display(gid, st.session_state.get("guideline_display_md") or "")
                st.success("Display saved.")
            except Exception as e:
                st.error(str(e))

    with cC:
        with st.expander("Preview (read-only)", expanded=False):
            preview_md = (st.session_state.get("guideline_display_md") or "").strip()
            if preview_md:
                st.markdown(preview_md)
            else:
                st.markdown("—")


# =======================
# Page: Generate meta
# =======================
elif page == "Generate meta":
    st.title("🧠 Generate meta (Answer focused question)")
    st.caption(
        "Select multiple saved studies and/or guidelines and generate a single-paragraph output."
    )

    # Always use abstracts for synthesis input.
    include_abstract = True
    left = st.container()

    # Left-hand panel: source selection
    with left:
        if st.session_state.pop("meta_clear_selected_requested", False):
            st.session_state["meta_manual_selected_pmids"] = []
            st.session_state["meta_manual_selected_gids"] = []
            st.session_state["meta_load_folder_ids"] = []
            st.session_state.pop("meta_pick_paper_table", None)
            st.session_state.pop("meta_pick_guideline_table", None)
            for k in list(st.session_state.keys()):
                if k.startswith("meta_keep_selected_pmid_") or k.startswith("meta_keep_selected_gid_"):
                    st.session_state.pop(k, None)

        folder_pmids: List[str] = []
        folder_gids: List[str] = []
        if "meta_manual_selected_pmids" not in st.session_state:
            st.session_state["meta_manual_selected_pmids"] = []
        if "meta_manual_selected_gids" not in st.session_state:
            st.session_state["meta_manual_selected_gids"] = []

        manual_pmids = [
            str(p).strip()
            for p in (st.session_state.get("meta_manual_selected_pmids") or [])
            if str(p).strip()
        ]
        manual_gids = [
            str(g).strip()
            for g in (st.session_state.get("meta_manual_selected_gids") or [])
            if str(g).strip()
        ]

        load_folder_rows = list_folders(limit=FOLDERS_MAX_LIST)
        load_folder_by_id: Dict[str, Dict[str, str]] = {
            (f.get("folder_id") or "").strip(): f
            for f in load_folder_rows
            if (f.get("folder_id") or "").strip()
        }
        load_folder_ids = [fid for fid in load_folder_by_id.keys() if fid]

        selected_load_folder_ids = st.multiselect(
            "Choose folder(s) to load",
            options=load_folder_ids,
            format_func=lambda fid: (
                f"{(load_folder_by_id[fid].get('name') or '').strip()} "
                f"({load_folder_by_id[fid].get('item_count') or '0'} items)"
            ),
            key="meta_load_folder_ids",
        )

        if not load_folder_ids:
            st.caption("No folders yet. Save some items to a folder first.")
        elif selected_load_folder_ids:
            pmids_accum: List[str] = []
            gids_accum: List[str] = []
            for fid in selected_load_folder_ids:
                loaded = get_folder_item_ids(fid)
                pmids_accum.extend(loaded.get("pmids") or [])
                gids_accum.extend(loaded.get("guideline_ids") or [])

            folder_pmids = list(dict.fromkeys(pmids_accum))
            folder_gids = list(dict.fromkeys(gids_accum))
            st.caption(
                f"Loaded from {len(selected_load_folder_ids)} folder(s): "
                f"{len(folder_pmids)} papers • {len(folder_gids)} guidelines"
            )
        else:
            st.caption("No folders selected.")

        q = st.text_input(
            "Filter papers/guidelines",
            placeholder="Type to filter your DB (title/abstract/tags/etc). Leave blank to show recent.",
            key="meta_filter_q",
        )

        # Retrieve candidate papers
        candidate_limit = 250
        if (q or "").strip():
            paper_candidates = search_records(limit=int(candidate_limit), q=q)
            guideline_candidates = search_guidelines(limit=GUIDELINES_MAX_LIST, q=q)
        else:
            paper_candidates = list_recent_records(limit=int(candidate_limit))
            guideline_candidates = list_guidelines(limit=GUIDELINES_MAX_LIST)

        if not paper_candidates and not guideline_candidates:
            if (folder_pmids or folder_gids):
                st.info("No manual matches for this filter. Folder sources are still included.")
            elif (manual_pmids or manual_gids):
                st.info("No results for this filter. Your previously selected manual items are still selected.")
            else:
                st.info("No saved papers or guidelines found.")
        else:
            folder_pmid_set = set(folder_pmids)
            folder_gid_set = set(folder_gids)
            manual_pmid_set = set(manual_pmids)
            manual_gid_set = set(manual_gids)

            # Papers table
            if paper_candidates:
                st.markdown("##### Papers")
                st.caption("`Pick` = include manually for this run. `From folder` = already included via folder selection.")
                pdf = pd.DataFrame(paper_candidates)
                if "pmid" in pdf.columns:
                    paper_ids = [str(p).strip() for p in pdf["pmid"].tolist()]
                else:
                    paper_ids = []
                pdf.insert(0, "Pick", [p in manual_pmid_set for p in paper_ids] if paper_ids else False)
                if "pmid" in pdf.columns:
                    pdf.insert(1, "From folder", [p in folder_pmid_set for p in paper_ids])
                # UI: omit Specialty in this table
                if "specialty" in pdf.columns:
                    pdf = pdf.drop(columns=["specialty"])
                p_edited = st.data_editor(
                    pdf,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Pick": st.column_config.CheckboxColumn("Pick", help="Select for synthesis"),
                        "From folder": st.column_config.CheckboxColumn("From folder"),
                        "pmid": st.column_config.TextColumn("PMID", width="small"),
                        "year": st.column_config.TextColumn("Year", width="small"),
                        "patient_n": st.column_config.TextColumn("N", width="small"),
                        "title": st.column_config.TextColumn("Title", width="large"),
                        "journal": st.column_config.TextColumn("Journal", width="medium"),
                        "study_design": st.column_config.TextColumn("Design tags", width="medium"),
                    },
                    disabled=[
                        "From folder",
                        "pmid",
                        "year",
                        "patient_n",
                        "title",
                        "journal",
                        "study_design",
                    ],
                    key="meta_pick_paper_table",
                )

                if "pmid" in p_edited.columns:
                    visible_pmids: List[str] = []
                    visible_picked_pmids: List[str] = []
                    for _, row in p_edited.iterrows():
                        pmid = str(row.get("pmid") or "").strip()
                        if not pmid:
                            continue
                        visible_pmids.append(pmid)
                        if bool(row.get("Pick")):
                            visible_picked_pmids.append(pmid)

                    visible_set = set(visible_pmids)
                    manual_pmids = [p for p in manual_pmids if p not in visible_set]
                    for pmid in visible_picked_pmids:
                        if pmid not in manual_pmids:
                            manual_pmids.append(pmid)

            # Guidelines table
            if guideline_candidates:
                st.markdown("##### Guidelines")
                gdf_rows = []
                for g in guideline_candidates:
                    gid = (g.get("guideline_id") or "").strip()
                    # Use guideline_name if present; fall back to title (used by search_guidelines) or filename
                    name = (
                        g.get("guideline_name")
                        or g.get("title")
                        or g.get("filename")
                        or ""
                    ).strip()
                    year = (g.get("pub_year") or g.get("year") or "").strip()
                    gdf_rows.append(
                        {
                            "guideline_id": gid,
                            "Pick": gid in manual_gid_set,
                            "From folder": gid in folder_gid_set,
                            "title": name,
                            "year": year,
                        }
                    )
                gdf = pd.DataFrame(gdf_rows)
                # UI: hide ID by putting it in the index (hide_index=True already)
                if "guideline_id" in gdf.columns:
                    gdf = gdf.set_index("guideline_id")
                g_edited = st.data_editor(
                    gdf,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Pick": st.column_config.CheckboxColumn("Pick", help="Select for synthesis"),
                        "From folder": st.column_config.CheckboxColumn("From folder"),
                        "title": st.column_config.TextColumn("Title", width="large"),
                        "year": st.column_config.TextColumn("Year", width="small"),
                    },
                    disabled=["From folder", "title", "year"],
                    key="meta_pick_guideline_table",
                )

                visible_gids: List[str] = []
                visible_picked_gids: List[str] = []
                for gid, row in g_edited.iterrows():
                    gid_s = str(gid or "").strip()
                    if not gid_s:
                        continue
                    visible_gids.append(gid_s)
                    if bool(row.get("Pick")):
                        visible_picked_gids.append(gid_s)

                visible_gid_set = set(visible_gids)
                manual_gids = [g for g in manual_gids if g not in visible_gid_set]
                for gid in visible_picked_gids:
                    if gid not in manual_gids:
                        manual_gids.append(gid)

        st.session_state["meta_manual_selected_pmids"] = manual_pmids
        st.session_state["meta_manual_selected_gids"] = manual_gids

        picked_pmids = list(dict.fromkeys(folder_pmids + manual_pmids))
        picked_gids = list(dict.fromkeys(folder_gids + manual_gids))

        # Validate selection
        if not picked_pmids and not picked_gids:
            st.info("Pick at least one paper or guideline.")
            st.stop()

        # Enforce hard cap across all sources
        total_picks = len(picked_pmids) + len(picked_gids)
        max_allowed = int(META_MAX_STUDIES_HARD_CAP)
        if total_picks > max_allowed:
            st.warning(
                f"You picked {total_picks} sources; only the first {max_allowed} will be used."
            )
            # Create combined list preserving order (papers first, then guidelines)
            combo = [("paper", p) for p in picked_pmids] + [("guideline", g) for g in picked_gids]
            combo = combo[:max_allowed]
            picked_pmids = [id for t, id in combo if t == "paper"]
            picked_gids = [id for t, id in combo if t == "guideline"]

        # Display selected sources (can unselect inline)
        c_sel_l, c_sel_r = st.columns([5, 1], gap="small")
        with c_sel_l:
            st.markdown("#### Selected")
        with c_sel_r:
            if st.button("Clear selected", key="meta_clear_selected_btn", use_container_width=True):
                st.session_state["meta_clear_selected_requested"] = True
                st.rerun()

        st.caption("Uncheck any item to remove it from this run.")

        kept_pmids: List[str] = []
        kept_gids: List[str] = []

        for p in picked_pmids:
            r = get_record(p)
            title = (r.get("title") or "").strip() if r else ""
            c_info, c_keep = st.columns([7, 1], gap="small")
            with c_info:
                st.markdown(f"- [{title or p}](https://pubmed.ncbi.nlm.nih.gov/{p}/) — `{p}`")
            with c_keep:
                keep = st.checkbox("Use", value=True, key=f"meta_keep_selected_pmid_{p}")
            if keep:
                kept_pmids.append(p)

        for gid in picked_gids:
            meta = get_guideline_meta(gid) or {}
            name = (meta.get("guideline_name") or meta.get("filename") or "").strip()
            c_info, c_keep = st.columns([7, 1], gap="small")
            with c_info:
                st.markdown(f"- [Guideline] {name or gid} — `{gid}`")
            with c_keep:
                keep = st.checkbox("Use", value=True, key=f"meta_keep_selected_gid_{gid}")
            if keep:
                kept_gids.append(gid)

        picked_pmids = kept_pmids
        picked_gids = kept_gids

        if not picked_pmids and not picked_gids:
            st.info("All selected items are unchecked. Check at least one to continue.")
            st.stop()

        st.markdown("##### Folders")
        folder_toggle = st.toggle(
            "Add selected items to a folder",
            value=False,
            key="meta_folder_toggle",
        )

        if folder_toggle:
            folder_rows = list_folders(limit=FOLDERS_MAX_LIST)
            folder_mode = st.radio(
                "Folder destination",
                options=["Existing folder", "New folder"],
                horizontal=True,
                key="meta_folder_mode",
            )

            selected_folder_id = ""
            if folder_mode == "Existing folder":
                folder_by_id: Dict[str, Dict[str, str]] = {
                    (f.get("folder_id") or "").strip(): f
                    for f in folder_rows
                    if (f.get("folder_id") or "").strip()
                }
                folder_ids = [fid for fid in folder_by_id.keys() if fid]
                if not folder_ids:
                    st.info("No folders yet. Choose `New folder` to create one.")
                else:
                    selected_folder_id = st.selectbox(
                        "Choose folder",
                        options=folder_ids,
                        format_func=lambda fid: (
                            f"{(folder_by_id[fid].get('name') or '').strip()} "
                            f"({folder_by_id[fid].get('item_count') or '0'} items)"
                        ),
                        key="meta_folder_existing",
                    )
            else:
                st.text_input(
                    "New folder name",
                    key="meta_folder_new_name",
                    placeholder="e.g., Atrial fibrillation updates",
                )

            if st.button(
                "Add selected to folder",
                key="meta_add_selected_to_folder_btn",
                use_container_width=True,
            ):
                try:
                    target_folder_id = ""
                    target_folder_name = ""
                    was_created = False

                    if folder_mode == "Existing folder":
                        target_folder_id = (selected_folder_id or "").strip()
                        if not target_folder_id:
                            raise ValueError("Choose an existing folder first.")

                        for f in folder_rows:
                            if (f.get("folder_id") or "").strip() == target_folder_id:
                                target_folder_name = (f.get("name") or "").strip()
                                break
                    else:
                        new_folder_name = (st.session_state.get("meta_folder_new_name") or "").strip()
                        if not new_folder_name:
                            raise ValueError("Enter a folder name.")
                        created = create_or_get_folder(new_folder_name)
                        target_folder_id = (created.get("folder_id") or "").strip()
                        target_folder_name = (created.get("name") or "").strip()
                        was_created = (created.get("created") or "0") == "1"

                    stats = add_items_to_folder(
                        folder_id=target_folder_id,
                        pmids=picked_pmids,
                        guideline_ids=picked_gids,
                    )
                    papers_added = int(stats.get("papers_added") or "0")
                    guidelines_added = int(stats.get("guidelines_added") or "0")
                    total_added = int(stats.get("total_added") or "0")

                    if total_added > 0:
                        if was_created:
                            st.success(f"Created `{target_folder_name}` and added {total_added} item(s).")
                        else:
                            st.success(f"Added {total_added} item(s) to `{target_folder_name}`.")
                    else:
                        st.info("No new items were added (they may already be in that folder).")
                    st.caption(f"Papers added: {papers_added} • Guidelines added: {guidelines_added}")
                except Exception as e:
                    st.error(f"Folder update failed: {e}")


        st.divider()
        prompt_text = st.text_input(
            "Focused question",
            placeholder="e.g., Does X improve Y in Z population?",
            key="meta_focused_question",
        )

        # Generate button
        if st.button("Answer focused question", type="primary", key="meta_generate_btn", use_container_width=True):
            if not (prompt_text or "").strip():
                st.error("Enter a focused question.")
            else:
                with st.spinner("Generating…"):
                    try:
                        out = gpt_generate_meta_combined(
                            pmids=picked_pmids,
                            guideline_ids=picked_gids,
                            mode="answer",
                            prompt_text=prompt_text,
                            include_abstract=include_abstract,
                            tone="Clear and organized",
                        )
                        st.session_state["meta_last_output"] = out
                    except Exception as e:
                        st.error(str(e))

    # Display output if available
    out = (st.session_state.get("meta_last_output") or "").strip()
    if out:
        st.divider()
        st.subheader("Output")
        st.write(out)

# =======================
# Page: Delete
# =======================
elif page == "Delete":
    st.title("🗑️ Delete")
    st.caption("Permanently remove saved papers or guidelines + extracted content. This cannot be undone.")

    tab_papers, tab_guidelines = st.tabs(["Papers", "Guidelines"])

    with tab_papers:
        st.subheader("Delete a saved paper")

        q = st.text_input(
            "Filter papers",
            placeholder="Search title/journal/specialty/PMID… (default is most recent)",
            key="delete_paper_filter",
        )

        paper_rows = search_records(limit=200, q=q) if (q or "").strip() else list_recent_records(limit=200)

        if not paper_rows:
            st.info("No saved papers found.")
        else:
            def _paper_label(r: Dict[str, str]) -> str:
                pmid = (r.get("pmid") or "").strip()
                title = (r.get("title") or "").strip()
                year = (r.get("year") or "").strip()
                journal = (r.get("journal") or "").strip()
                bits = [title]
                if year:
                    bits.append(f"({year})")
                if journal:
                    bits.append(f"— {journal}")
                return " ".join([b for b in bits if b]).strip()

            sel_i = st.selectbox(
                "Select a paper",
                list(range(len(paper_rows))),
                format_func=lambda i: _paper_label(paper_rows[i]),
                key="delete_paper_select_idx",
            )

            sel_pmid = (paper_rows[sel_i].get("pmid") or "").strip()
            rec = get_record(sel_pmid) or {}

            st.write(f"**PMID:** {sel_pmid}")
            st.write(f"**Specialty:** {(rec.get('specialty') or paper_rows[sel_i].get('specialty') or '').strip()}")

            with st.expander("Show abstract", expanded=False):
                abs_txt = (rec.get('abstract') or '').strip()
                if abs_txt:
                    st.write(abs_txt)

            confirm = st.checkbox("Confirm permanent delete", key=f"confirm_delete_paper_{sel_pmid}")
            if st.button(
                "Delete paper",
                type="primary",
                width="stretch",
                disabled=not confirm,
                key=f"btn_delete_paper_{sel_pmid}",
            ):
                try:
                    delete_record(sel_pmid)
                    st.success("Deleted paper.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    with tab_guidelines:
        st.subheader("Delete a saved guideline")

        gq = st.text_input(
            "Filter guidelines",
            placeholder="Search name/filename/year/specialty… (leave blank for recent)",
            key="delete_guideline_filter",
        )

        raw_rows = search_guidelines(limit=200, q=gq) if (gq or "").strip() else list_guidelines(limit=200)

        guidelines: List[Dict[str, str]] = []
        for r in raw_rows:
            gid = (r.get("guideline_id") or "").strip()
            if not gid:
                continue
            title = (r.get("title") or r.get("guideline_name") or r.get("filename") or "").strip()
            year = (r.get("year") or r.get("pub_year") or "").strip()
            specialty = (r.get("specialty") or "").strip()
            guidelines.append({"guideline_id": gid, "title": title, "year": year, "specialty": specialty})

        # Helper for guideline label.
        def _guideline_label(r: Dict[str, str]) -> str:
            gid = (r.get("guideline_id") or "").strip()
            title = (r.get("title") or "").strip()
            year = (r.get("year") or "").strip()
            spec = (r.get("specialty") or "").strip()
            bits = [title]
            if year:
                bits.append(f"({year})")
            if spec:
                bits.append(f"— {spec}")
            return " ".join([b for b in bits if b]).strip()
        
        # --- Use stable guideline_id values (prevents None/index drift after delete/filter) ---
        gid_options = [g["guideline_id"] for g in guidelines if (g.get("guideline_id") or "").strip()]
        gid_to_row = {g["guideline_id"]: g for g in guidelines if (g.get("guideline_id") or "").strip()}

        if not gid_options:
            st.info("No saved guidelines found.")
            st.stop()

        _state_key = "delete_guideline_selected_gid"

        # If the previously-selected gid no longer exists (e.g., after deletion/filter), clear it
        prev = st.session_state.get(_state_key)
        if prev and prev not in gid_options:
            st.session_state.pop(_state_key, None)

        sel_gid = st.selectbox(
            "Select a guideline",
            options=gid_options,
            format_func=lambda gid: _guideline_label(gid_to_row.get(gid, {"guideline_id": gid, "title": gid, "year": "", "specialty": ""})),
            key=_state_key,
        )

        meta = get_guideline_meta(sel_gid) or {}


        st.write(f"**Filename:** {(meta.get('filename') or '').strip()}")
        st.write(f"**Uploaded:** {(meta.get('uploaded_at') or '').strip()}")

        gconfirm = st.checkbox("Confirm permanent delete", key=f"confirm_delete_guideline_{sel_gid}")
        if st.button(
            "Delete guideline",
            type="primary",
            width="stretch",
            disabled=not gconfirm,
            key=f"btn_delete_guideline_{sel_gid}",
        ):
            try:
                delete_guideline(sel_gid)
                st.success("Deleted guideline.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# =======================
# Page: About
# =======================
elif page == "About":
    render_help_about_page()

# =======================
# Page: History
# =======================
elif page == "History":
    render_history_page()
elif page == "Search PubMed":
    render_search_pubmed_page()
