import re
import html
from typing import Dict, List, Tuple, Optional

import pandas as pd
import requests
import streamlit as st

from pathlib import Path


from db import (
    _db_path,
    ensure_schema,
    ensure_guidelines_schema,
    db_count,
    is_saved,
    save_record,
    search_records,
    search_guidelines,
    list_browse_items,
    list_browse_guideline_items,
    get_record,
    update_pico_fields,
    delete_record,
    delete_guideline,
    save_guideline_pdf,
    list_guidelines,
    get_guideline_meta,
    get_cached_layout_markdown,
    guideline_rec_counts,
    list_guideline_recommendations,
    normalize_relevance_status,
    mark_guideline_recommendation_relevant,
    mark_guideline_recommendation_irrelevant,
    delete_guideline_recommendation,
    update_guideline_metadata,
    list_recent_records,
)
from extract import (
    fetch_pubmed_xml,
    parse_abstract,
    parse_year,
    parse_journal,
    parse_title,
    get_top_neighbors,
    gpt_extract_patient_n,
    gpt_extract_study_design,
    gpt_extract_patient_details,
    gpt_extract_intervention_comparison,
    gpt_extract_authors_conclusions,
    gpt_extract_results,
    gpt_extract_specialty,
    _parse_nonneg_int,
    _parse_tag_list,
    _normalize_bullets,
    get_or_create_markdown,
    extract_and_store_guideline_recommendations_azure,
    extract_and_store_guideline_metadata_azure,
    gpt_generate_meta_paragraph,
    _parse_year4,
    # Import helpers for custom meta synthesis
    _pack_study_for_meta,
    _openai_api_key,
    _openai_model,
    _post_with_retries,
    _extract_output_text,
    OPENAI_RESPONSES_URL,
)

import json
import random
import time

# silent safety caps (avoid loading/rendering huge DBs by accident)
SEARCH_MAX_DEFAULT = 1500
BROWSE_MAX_ROWS = 30000

GUIDELINES_MAX_LIST = 30000  # UI list cap
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


def _year_sort_key(y: str) -> Tuple[int, str]:
    ys = (y or "").strip()
    if re.fullmatch(r"\d{4}", ys):
        return (0, ys)
    if not ys:
        return (2, "0000")
    return (1, ys)

# --------------- Meta synthesis helpers (papers + guidelines) ---------------

def _pack_guideline_for_meta(gid: str, idx: int, max_recs: int = 10) -> str:
    """
    Construct a block of text representing a guideline for the meta synthesis prompt.

    This uses the guideline's metadata (name/year/specialty) and the text of its
    recommendations. All recommendations are included regardless of their review
    status (relevant, unreviewed or irrelevant). Strength and evidence descriptors
    are appended parenthetically when present and not already present in the
    recommendation text. At most ``max_recs`` recommendations are included to
    keep the prompt concise.
    """
    gid = (gid or "").strip()
    if not gid:
        return ""
    # Fetch guideline metadata (name, year, specialty)
    meta = get_guideline_meta(gid) or {}
    name = (meta.get("guideline_name") or meta.get("filename") or "").strip()
    year = (meta.get("pub_year") or "").strip()
    spec = (meta.get("specialty") or "").strip()
    # Compose header line
    header_bits: List[str] = []
    if name:
        header_bits.append(name)
    else:
        header_bits.append(f"Guideline {gid}")
    if year:
        header_bits.append(year)
    if spec:
        header_bits.append(spec)
    header = f"{idx}. " + " • ".join(header_bits) 
    # Collect recommendations
    recs = list_guideline_recommendations(gid)
    lines: List[str] = []
    count = 0
    for r in recs:
        # Do not filter by relevance status; include relevant, unreviewed, and irrelevant recommendations
        rec_text = (r.get("recommendation_text") or "").strip()
        if not rec_text:
            continue
        strength = (r.get("strength_raw") or "").strip()
        evidence = (r.get("evidence_raw") or "").strip()
        # Append strength/evidence parenthetically if not already in text
        extra_bits: List[str] = []
        for s in [strength, evidence]:
            if s and (s.lower() not in rec_text.lower()):
                extra_bits.append(s)
        if extra_bits:
            full_text = f"{rec_text} ({'; '.join(extra_bits)})"
        else:
            full_text = rec_text
        lines.append(f"- {full_text}")
        count += 1
        if count >= max_recs:
            break
    if not lines:
        # No usable recommendations; just return header
        return header
    return f"{header}\n" + "\n".join(lines)


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
            "- Tone: Clinical, professional.",
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

page = st.sidebar.radio(
    "Navigate",
    ["PMID → Abstract", "Guidelines (PDF Upload)", "DB Search", "DB Browse", "Generate meta", "Delete", "About"],
    index=0,
    key="nav_page",
)


st.sidebar.caption(f"DB: `{_db_path()}`")
st.sidebar.caption(f"Saved: **{db_count()}**")

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

    st.download_button(
        "Download README.md",
        data=md,
        file_name="README.md",
        mime="text/markdown",
        use_container_width=True,
    )
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

                        raw_spec = (st.session_state.get("specialty_input", "") or "").strip()
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

            with st.expander("Related articles (top 5)"):
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

            st.divider()

            serr = (st.session_state.get("gpt_specialty_error") or "").strip()
            if serr:
                st.error(serr)
            st.text_input("Specialty", key="specialty_input", placeholder="e.g., Infectious Disease, Critical Care")


# =======================
# Page: DB Search
# =======================
elif page == "DB Search":
    st.title("📚 Database")

    q = st.text_input(
        "Search",
        placeholder="Search anything (title, abstract text, intervention, journal, etc)…",
        key="db_search_any",
    )

    if not (q or "").strip():
        st.stop()

    paper_rows = search_records(limit=SEARCH_MAX_DEFAULT, q=q)
    guideline_rows = search_guidelines(limit=SEARCH_MAX_DEFAULT, q=q)

    rows: List[Dict[str, str]] = []
    rows.extend(guideline_rows)
    rows.extend(paper_rows)

    if not rows:
        st.warning("No matches.")
        st.stop()

    selected = st.selectbox("Results", options=rows, format_func=_fmt_search_item, index=0)

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

        with st.expander("Related articles (top 5)"):
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

    else:
        gid = (selected.get("guideline_id") or "").strip()
        meta = get_guideline_meta(gid) or {}
        title = (meta.get("guideline_name") or "").strip() or (meta.get("filename") or "").strip() or (selected.get("title") or "")
        year = (meta.get("pub_year") or "").strip() or (selected.get("year") or "")
        spec = (meta.get("specialty") or "").strip() or (selected.get("specialty") or "")

        st.subheader(f"📘 {title}")

        bits = [b for b in [year, spec] if b]
        if bits:
            st.caption(" • ".join(bits))

        counts = guideline_rec_counts(gid)
        # m1, m2, m3 = st.columns(3, gap="large")
        # with m1:
        #     st.metric("Relevant", str(counts.get("relevant", 0)))
        # with m2:
        #     st.metric("Unreviewed", str(counts.get("unreviewed", 0)))
        # with m3:
        #     st.metric("Irrelevant", str(counts.get("irrelevant", 0)))

        st.divider()

        rec_filter = st.selectbox(
            "Show",
            ["Relevant", "Unreviewed", "Irrelevant", "All"],
            index=0,
            key=f"guideline_view_filter_{gid}",
        )

        recs_all = list_guideline_recommendations(gid)

        relevant = [r for r in recs_all if normalize_relevance_status(r.get("relevance_status") or "") == "relevant"]
        unreviewed = [r for r in recs_all if normalize_relevance_status(r.get("relevance_status") or "") == "unreviewed"]
        irrelevant = [r for r in recs_all if normalize_relevance_status(r.get("relevance_status") or "") == "irrelevant"]

        def _render_relevant_list(items: List[Dict[str, str]]) -> None:
            if not items:
                st.info("None.")
                return
            for r in items:
                txt = (r.get("recommendation_text") or "").strip()
                if txt:
                    st.markdown(f"- {txt}")

        def _merge_into_one_string(rec_text: str, strength: str, evidence: str) -> str:
            t = (rec_text or "").strip()
            s = (strength or "").strip()
            e = (evidence or "").strip()
            if not t:
                return ""
            bits2 = [x for x in [s, e] if x]
            if not bits2:
                return t
            low = t.lower()
            if (s and s.lower() in low) or (e and e.lower() in low):
                return t
            return f"{t} ({'; '.join(bits2)})"

        def _render_unreviewed_review(items: List[Dict[str, str]]) -> None:
            if not items:
                st.info("None.")
                return
            for r in items:
                rec_id = (r.get("rec_id") or "").strip()
                if not rec_id:
                    continue
                idx = (r.get("idx") or "").strip()
                default_text = _merge_into_one_string(
                    (r.get("recommendation_text") or "").strip(),
                    (r.get("strength_raw") or "").strip(),
                    (r.get("evidence_raw") or "").strip(),
                )
                with st.container(border=True):
                    c_text, c_keep, c_remove, c_delete = st.columns([8, 1, 1, 1], gap="large")

                    with c_text:
                        st.text_area(
                            label=f"Recommendation".strip(),
                            value=default_text,
                            height=90,
                            key=f"rec_text_{gid}_{rec_id}",
                        )

                    with c_keep:
                        if st.button("Keep", type="primary", use_container_width=True, key=f"rec_keep_{gid}_{rec_id}"):
                            try:
                                new_text = (st.session_state.get(f"rec_text_{gid}_{rec_id}") or "").strip()
                                mark_guideline_recommendation_relevant(rec_id=rec_id, recommendation_text=new_text)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Keep failed: {e}")

                    with c_remove:
                        if st.button("Remove", type="secondary", use_container_width=True, key=f"rec_remove_{gid}_{rec_id}"):
                            try:
                                mark_guideline_recommendation_irrelevant(rec_id=rec_id)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Remove failed: {e}")

                    with c_delete:
                        if st.button("Delete", type="secondary", use_container_width=True, key=f"rec_delete_{gid}_{rec_id}"):
                            try:
                                delete_guideline_recommendation(rec_id=rec_id)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {e}")


        if rec_filter == "Relevant":
            _render_relevant_list(relevant)
        elif rec_filter == "Irrelevant":
            _render_relevant_list(irrelevant)
        elif rec_filter == "Unreviewed":
            _render_unreviewed_review(unreviewed)
        else:
            st.markdown("### Relevant")
            _render_relevant_list(relevant)
            st.markdown("### Unreviewed")
            _render_unreviewed_review(unreviewed)
            st.markdown("### Irrelevant")
            _render_relevant_list(irrelevant)


# =======================
# Page: DB Browse
# =======================
elif page == "DB Browse":
    st.title("🗂️ Browse")

    items: List[Dict[str, str]] = []
    items.extend(list_browse_items(limit=BROWSE_MAX_ROWS))
    items.extend(list_browse_guideline_items(limit=BROWSE_MAX_ROWS))

    if not items:
        st.info("No saved articles yet.")
        st.stop()

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
                        st.markdown(f"- {title}")
                    else:
                        pmid = it.get("pmid") or ""
                        title = (it.get("title") or "").strip() or "(no title)"
                        concl = (it.get("authors_conclusions") or "").strip()
                        st.markdown(f"- [{title}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/) — `{pmid}`")
                        if concl:
                            st.caption(concl)
                st.markdown("")

# =======================
# Page: Guidelines (PDF Upload + Azure Extract)
# =======================
elif page == "Guidelines (PDF Upload)":
    st.title("📄 Guidelines — Upload PDF")
    st.caption("Upload PDFs, then extract recommendations.")

    up = st.file_uploader("Upload a guideline PDF", type=["pdf"], accept_multiple_files=False)
    if up is not None:
        pdf_bytes = up.getvalue()
        size_mb = (len(pdf_bytes) / (1024 * 1024)) if pdf_bytes else 0.0
        st.write(f"**Selected:** {up.name}  \n**Size:** {size_mb:.2f} MB")

        if st.button("Save PDF", type="primary", width="stretch"):
            try:
                rec = save_guideline_pdf(up.name, pdf_bytes)
                st.session_state["guidelines_last_saved"] = rec.get("guideline_id") or ""
                st.success(f"Saved guideline PDF. ID: `{rec.get('guideline_id','')}`")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")

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

        if st.button("Extract metadata", type="secondary", width="stretch", key="guideline_meta_extract"):
            try:
                with st.spinner("Extracting guideline name/year/specialty…"):
                    out = extract_and_store_guideline_metadata_azure(gid)

                if isinstance(out, dict):
                    st.session_state["guideline_meta_pending"] = {
                        "gid": gid,
                        "name": str(out.get("guideline_name") or "").strip(),
                        "year": str(out.get("pub_year") or "").strip(),
                        "spec": str(out.get("specialty") or "").strip(),
                    }

                st.success("Metadata extracted.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    meta_ex_at = (chosen.get("meta_extracted_at") or "").strip()
    if meta_ex_at:
        st.caption(f"Last metadata update: {meta_ex_at}")

    meta = get_guideline_meta(gid)
    cached_md = get_cached_layout_markdown(gid, meta.get("sha256", "")) if meta else ""
    st.caption(f"Markdown cached: **{'Yes' if (cached_md or '').strip() else 'No'}**")

    st.divider()

    st.subheader("Extract recommendations")
    existing = list_guideline_recommendations(gid)
    st.caption(f"Currently stored: **{len(existing)}** recommendations")

    already_extracted = len(existing) > 0
    if already_extracted:
        st.info("Recommendations already extracted for this PDF. To re-run, delete/clear existing recommendations first.")

    if st.button(
        "Extract recommendations now",
        type="primary",
        width="stretch",
        disabled=already_extracted,
        key=f"extract_recs_{gid}",
    ):
        prog = st.progress(0)
        status = st.empty()

        def _cb(done, total):
            if total <= 0:
                return
            prog.progress(min(1.0, max(0.0, done / float(total))))
            status.write(f"Processing candidate {done} / {total} …")

        try:
            with st.spinner("Extracting…"):
                try:
                    if not (chosen.get("guideline_name") or "").strip() or not (chosen.get("pub_year") or "").strip() or not (chosen.get("specialty") or "").strip():
                        extract_and_store_guideline_metadata_azure(gid)
                except Exception:
                    pass

                n = extract_and_store_guideline_recommendations_azure(gid, progress_cb=_cb)
            st.success(f"Stored {n} recommendations.")
            st.rerun()
        except Exception as e:
            st.error(str(e))


    st.divider()

    recs = list_guideline_recommendations(gid)
    if not recs:
        st.info("No recommendations extracted yet.")
        st.stop()

    st.subheader("Recommendation list")

    def _merge_into_one_string(rec_text: str, strength: str, evidence: str) -> str:
        t = (rec_text or "").strip()
        s = (strength or "").strip()
        e = (evidence or "").strip()
        if not t:
            return ""
        bits3 = [x for x in [s, e] if x]
        if not bits3:
            return t
        low = t.lower()
        if (s and s.lower() in low) or (e and e.lower() in low):
            return t
        return f"{t} ({'; '.join(bits3)})"

    def _is_unreviewed(status: str) -> bool:
        return normalize_relevance_status(status) == "unreviewed"

    unreviewed = [r for r in recs if _is_unreviewed(r.get("relevance_status") or "")]

    if not unreviewed:
        st.info("No unreviewed recommendations.")
        st.stop()

    for r in unreviewed:
        rec_id = (r.get("rec_id") or "").strip()
        if not rec_id:
            continue

        idx = (r.get("idx") or "").strip()
        default_text = _merge_into_one_string(
            (r.get("recommendation_text") or "").strip(),
            (r.get("strength_raw") or "").strip(),
            (r.get("evidence_raw") or "").strip(),
        )

        with st.container(border=True):
            c_text, c_keep, c_remove, c_delete = st.columns([8, 1, 1, 1], gap="large")

            with c_text:
                st.text_area(
                    label=f"Recommendation".strip(),
                    value=default_text,
                    height=90,
                    key=f"rec_text_{gid}_{rec_id}",
                )

            with c_keep:
                if st.button("Keep", type="primary", use_container_width=True, key=f"rec_keep_{gid}_{rec_id}"):
                    try:
                        new_text = (st.session_state.get(f"rec_text_{gid}_{rec_id}") or "").strip()
                        mark_guideline_recommendation_relevant(rec_id=rec_id, recommendation_text=new_text)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Keep failed: {e}")

            with c_remove:
                if st.button("Remove", type="secondary", use_container_width=True, key=f"rec_remove_{gid}_{rec_id}"):
                    try:
                        mark_guideline_recommendation_irrelevant(rec_id=rec_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Remove failed: {e}")

            with c_delete:
                if st.button("Delete", type="secondary", use_container_width=True, key=f"rec_delete_{gid}_{rec_id}"):
                    try:
                        delete_guideline_recommendation(rec_id=rec_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")


# =======================
# Page: Generate meta
# =======================
elif page == "Generate meta":
    st.title("🧠 Generate meta (qualitative synthesis)")
    st.caption(
        "Select multiple saved studies and/or guidelines and generate a single-paragraph output."
    )

    # Layout: left for selecting sources, right for generation options
    left, right = st.columns([2, 1], gap="large")

    # Right-hand sidebar: generation options
    with right:
        # Paper content selection (mutually exclusive)
        if "meta_send_abstracts" not in st.session_state:
            st.session_state["meta_send_abstracts"] = True
        if "meta_send_extracted" not in st.session_state:
            st.session_state["meta_send_extracted"] = False

        def _meta_abstracts_toggle() -> None:
            # If abstracts selected, turn off extracted.
            if st.session_state.get("meta_send_abstracts"):
                st.session_state["meta_send_extracted"] = False
            else:
                # Keep at least one option enabled.
                if not st.session_state.get("meta_send_extracted"):
                    st.session_state["meta_send_abstracts"] = True

        def _meta_extracted_toggle() -> None:
            # If extracted selected, turn off abstracts.
            if st.session_state.get("meta_send_extracted"):
                st.session_state["meta_send_abstracts"] = False
            else:
                # Keep at least one option enabled.
                if not st.session_state.get("meta_send_abstracts"):
                    st.session_state["meta_send_abstracts"] = True

        st.markdown("##### Paper content")
        send_abstracts = st.checkbox(
            "Send abstracts",
            key="meta_send_abstracts",
            on_change=_meta_abstracts_toggle,
        )
        send_extracted = st.checkbox(
            "Send extracted data (faster, but possibly less accurate)",
            key="meta_send_extracted",
            on_change=_meta_extracted_toggle,
        )

        # Internal flag expected downstream
        include_abstract = bool(send_abstracts) and not bool(send_extracted)
        mode = st.selectbox(
            "Generation mode",
            ["Synthesize", "Answer focused question"],
            index=0,
        )
        # Prompt input depending on mode
        prompt_text = ""
        if mode == "Answer focused question":
            prompt_text = st.text_input(
                "Focused question", placeholder="e.g., Does X improve Y in Z population?"
            )

    # Left-hand panel: source selection
    with left:
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
            st.info("No saved papers or guidelines found.")
            st.stop()

        picked_pmids: List[str] = []
        picked_gids: List[str] = []

        # Papers table
        if paper_candidates:
            st.markdown("##### Papers")
            pdf = pd.DataFrame(paper_candidates)
            pdf.insert(0, "Pick", False)
            # UI: omit Specialty in this table
            if "specialty" in pdf.columns:
                pdf = pdf.drop(columns=["specialty"])
            p_edited = st.data_editor(
                pdf,
                width='stretch',
                hide_index=True,
                column_config={
                    "Pick": st.column_config.CheckboxColumn("Pick", help="Select for synthesis"),
                    "pmid": st.column_config.TextColumn("PMID", width="small"),
                    "year": st.column_config.TextColumn("Year", width="small"),
                    "patient_n": st.column_config.TextColumn("N", width="small"),
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "journal": st.column_config.TextColumn("Journal", width="medium"),
                    "study_design": st.column_config.TextColumn("Design tags", width="medium"),
                },
                disabled=[
                    "pmid",
                    "year",
                    "patient_n",
                    "title",
                    "journal",
                    "study_design",
                ],
                key="meta_pick_paper_table",
            )

            p_sel = p_edited[p_edited["Pick"] == True]  # noqa: E712
            picked_pmids = [str(p).strip() for p in p_sel["pmid"].tolist() if str(p).strip()]

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
                spec = (g.get("specialty") or "").strip()
                gdf_rows.append(
                    {
                        "guideline_id": gid,
                        "title": name,
                        "year": year,
                    }
                )
            gdf = pd.DataFrame(gdf_rows)
            # UI: hide ID by putting it in the index (hide_index=True already)
            if "guideline_id" in gdf.columns:
                gdf = gdf.set_index("guideline_id")
            gdf.insert(0, "Pick", False)
            g_edited = st.data_editor(
                gdf,
                width='stretch',
                hide_index=True,
                column_config={
                    "Pick": st.column_config.CheckboxColumn("Pick", help="Select for synthesis"),
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "year": st.column_config.TextColumn("Year", width="small"),
                },
                disabled=["title", "year"],
                key="meta_pick_guideline_table",
            )

            g_sel = g_edited[g_edited["Pick"] == True]  # noqa: E712
            picked_gids = [str(gid).strip() for gid in g_sel.index.tolist() if str(gid).strip()]

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

        # Display selected sources
        st.markdown("#### Selected")
        for p in picked_pmids:
            r = get_record(p)
            title = (r.get("title") or "").strip() if r else ""
            st.markdown(f"- [{title or p}](https://pubmed.ncbi.nlm.nih.gov/{p}/) — `{p}`")
        for gid in picked_gids:
            meta = get_guideline_meta(gid) or {}
            name = (meta.get("guideline_name") or meta.get("filename") or "").strip()
            st.markdown(f"- [Guideline] {name or gid} — `{gid}`")

        # Generate button
        if st.button("Generate", type="primary", key="meta_generate_btn", use_container_width=True):
            # Normalize mode string to internal identifier
            m = (mode or "").strip().lower()
            if m.startswith("answer"):
                mode_key = "answer"
            else:
                mode_key = "synthesize"
            with st.spinner("Generating…"):
                try:
                    out = gpt_generate_meta_combined(
                        pmids=picked_pmids,
                        guideline_ids=picked_gids,
                        mode=mode_key,
                        prompt_text=prompt_text,
                        include_abstract=include_abstract,
                        tone="Clinical, professional",
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
            st.stop()

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
        st.write(f"**Title:** {(rec.get('title') or paper_rows[sel_i].get('title') or '').strip()}")

        with st.expander("Show details", expanded=False):
            st.write(f"**Year:** {(rec.get('year') or paper_rows[sel_i].get('year') or '').strip()}")
            st.write(f"**Journal:** {(rec.get('journal') or paper_rows[sel_i].get('journal') or '').strip()}")
            st.write(f"**Specialty:** {(rec.get('specialty') or paper_rows[sel_i].get('specialty') or '').strip()}")
            abs_txt = (rec.get('abstract') or '').strip()
            if abs_txt:
                st.markdown("**Abstract (preview):**")
                st.write(abs_txt[:1200] + ("…" if len(abs_txt) > 1200 else ""))

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

        if not guidelines:
            st.info("No saved guidelines found.")
            st.stop()

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

        gsel_i = st.selectbox(
            "Select a guideline",
            list(range(len(guidelines))),
            format_func=lambda i: _guideline_label(guidelines[i]),
            key="delete_guideline_select_idx",
        )

        sel_gid = (guidelines[gsel_i].get("guideline_id") or "").strip()
        meta = get_guideline_meta(sel_gid) or {}
        counts = guideline_rec_counts(sel_gid)

        st.write(f"**Title:** {(meta.get('guideline_name') or meta.get('filename') or guidelines[gsel_i].get('title') or '').strip()}")

        with st.expander("Show details", expanded=False):
            st.write(f"**Filename:** {(meta.get('filename') or '').strip()}")
            st.write(f"**Uploaded:** {(meta.get('uploaded_at') or '').strip()}")
            st.write(f"**Year:** {(meta.get('pub_year') or guidelines[gsel_i].get('year') or '').strip()}")
            st.write(f"**Specialty:** {(meta.get('specialty') or guidelines[gsel_i].get('specialty') or '').strip()}")

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
