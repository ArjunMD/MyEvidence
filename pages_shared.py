import html
import re
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import quote_plus

import streamlit as st

from db import (
    get_guideline_meta,
    get_guideline_recommendations_display,
    get_hidden_pubmed_pmids,
    get_record,
    get_saved_pmids,
)
from extract import (
    OPENAI_RESPONSES_URL,
    _extract_output_text,
    _openai_api_key,
    _openai_model,
    _pack_study_for_meta,
    _post_with_retries,
)

SEARCH_MAX_DEFAULT = 1500
BROWSE_MAX_ROWS = 30000
GUIDELINES_MAX_LIST = 30000
FOLDERS_MAX_LIST = 5000
META_MAX_STUDIES_HARD_CAP = 30000

_REC_LINE_RE = re.compile(r"^\s*-\s+\*\*Rec\s+(\d+)\.\*\*\s*(.*)$")


def _clean_pmid(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    m = re.search(r"(\d{1,10})", s)
    return m.group(1) if m else ""


def _split_specialties(raw: str) -> List[str]:
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
        meta = year
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


def _parse_rec_nums(raw: str) -> List[int]:
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
    text = (md or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    delete_set = set(int(n) for n in (delete_nums or []) if isinstance(n, int) and n > 0)
    if not delete_set:
        return (md or "").strip(), []

    removed: List[int] = []
    filtered: List[str] = []

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
                (b or "").strip() and not _REC_LINE_RE.match(b or "")
                for b in block
            )

            if has_rec or has_meaningful_nonrec:
                out.append(heading)
                out.extend(block)
            else:
                if out and out[-1].strip():
                    out.append("")
        else:
            out.append(line)
            i += 1

    new_md = "\n".join(out).strip()

    still_has_any_rec = any(_REC_LINE_RE.match(ln or "") for ln in out)
    if not still_has_any_rec:
        if new_md:
            new_md += "\n\n_No recommendations remaining._"
        else:
            new_md = "_No recommendations remaining._"

    seen = set()
    removed_ordered: List[int] = []
    for n in removed:
        if n in seen:
            continue
        seen.add(n)
        removed_ordered.append(n)

    return new_md, removed_ordered


def _guideline_md_with_delete_links(md: str, gid: str) -> str:
    base = md or ""
    gid_q = quote_plus((gid or "").strip())

    pat = re.compile(r"(?m)^(\s*-\s+\*\*Rec\s+(\d+)\.\*\*)(\s*)")

    def repl(m: re.Match) -> str:
        num = m.group(2)
        icon = (
            f"<a href='?gid={gid_q}&delrec={num}' target='_self' "
            f"title='Delete Rec {num}' "
            f"style='text-decoration:none; opacity:0.35; margin-left:0.25rem;'>🗑️</a>"
        )
        return f"{m.group(1)} {icon}{m.group(3)}"

    return pat.sub(repl, base)


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
) -> str:
    pmids = [p.strip() for p in (pmids or []) if p and p.strip()]
    guideline_ids = [g.strip() for g in (guideline_ids or []) if g and g.strip()]
    if not pmids and not guideline_ids:
        return ""

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
    mode_clean = (mode or "").strip().lower()
    prompt_text = (prompt_text or "").strip()

    if mode_clean == "answer":
        descriptor_line = f"Question: {prompt_text}" if prompt_text else "Question: (none provided)"
    else:
        descriptor_line = ""

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

    if mode_clean == "answer":
        instructions_lines.append(
            "- Explicitly answer the question by summarizing the evidence across all sources."
        )
    elif prompt_text:
        instructions_lines.append(
            "- If a prompt is provided, orient the synthesis around it."
        )

    instructions = "\n".join(instructions_lines) + "\n"

    if descriptor_line:
        input_field = f"{descriptor_line}\n\nSOURCES:\n{content_text}\n\nNow write the single-paragraph output."
    else:
        input_field = f"SOURCES:\n{content_text}\n\nNow write the single-paragraph output."

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

    response = _post_with_retries(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    out = _extract_output_text(response.json())
    return (out or "").strip()


def _qp_first(qp: dict, key: str) -> str:
    v = qp.get(key)
    if isinstance(v, list):
        return v[0] if v else ""
    return str(v) if v is not None else ""


def _get_query_params() -> dict:
    try:
        return dict(st.query_params)
    except Exception:
        try:
            return st.experimental_get_query_params()
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


def _format_date_added(iso_str: str) -> str:
    s = (iso_str or "").strip()
    if not s:
        return "—"
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return dt.strftime("%b ") + str(dt.day) + dt.strftime(", %Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s or "—"
