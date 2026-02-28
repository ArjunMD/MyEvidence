import html
from typing import Dict, List

import requests
import streamlit as st

from db import is_saved, save_record
from extract import (
    _parse_nonneg_int,
    _parse_tag_list,
    fetch_pubmed_xml,
    get_s2_similar_papers,
    get_top_neighbors,
    gpt_extract_authors_conclusions,
    gpt_extract_intervention_comparison,
    gpt_extract_patient_details,
    gpt_extract_patient_n,
    gpt_extract_results,
    gpt_extract_specialty,
    gpt_extract_study_design,
    parse_abstract,
    parse_journal,
    parse_pub_month,
    parse_title,
    parse_year,
)
from pages_shared import _clean_pmid, _render_plain_text

_RELATED_TRAY_KEY = "pmid_related_tray"

_GPT_ERROR_KEYS = [
    "gpt_patient_n_error",
    "gpt_design_error",
    "gpt_details_error",
    "gpt_ic_error",
    "gpt_conclusions_error",
    "gpt_results_error",
    "gpt_specialty_error",
]

_GPT_RESULT_PAIRS = [
    ("gpt_patient_n", "patient_n_input", 0),
    ("gpt_study_design", "study_design_input", ""),
    ("gpt_patient_details", "patient_details_input", ""),
    ("gpt_intervention_comparison", "intervention_comparison_input", ""),
    ("gpt_authors_conclusions", "authors_conclusions_input", ""),
    ("gpt_results", "results_input", ""),
    ("gpt_specialty", "specialty_input", ""),
]


def _clear_gpt_errors() -> None:
    """Reset all GPT extraction error keys in session state."""
    for key in _GPT_ERROR_KEYS:
        st.session_state[key] = ""


def _clear_gpt_results() -> None:
    """Reset all GPT extraction result + input keys in session state."""
    for result_key, input_key, default in _GPT_RESULT_PAIRS:
        st.session_state[result_key] = default
        st.session_state[input_key] = "" if default == 0 else default


def _get_related_tray() -> List[Dict[str, str]]:
    raw = st.session_state.get(_RELATED_TRAY_KEY)
    if not isinstance(raw, list):
        raw = []

    out: List[Dict[str, str]] = []
    seen = set()
    for it in raw:
        if not isinstance(it, dict):
            continue
        pmid = _clean_pmid(str(it.get("pmid") or ""))
        if not pmid or pmid in seen:
            continue
        seen.add(pmid)
        out.append(
            {
                "pmid": pmid,
                "title": (it.get("title") or "").strip(),
                "source": (it.get("source") or "").strip(),
            }
        )

    st.session_state[_RELATED_TRAY_KEY] = out
    return out


def _add_related_pmid(pmid: str, title: str = "", source: str = "") -> bool:
    pid = _clean_pmid(pmid)
    if not pid:
        return False

    title = (title or "").strip()
    source = (source or "").strip()
    tray = _get_related_tray()

    for it in tray:
        if it.get("pmid") != pid:
            continue
        if title and not (it.get("title") or "").strip():
            it["title"] = title
        if source and not (it.get("source") or "").strip():
            it["source"] = source
        st.session_state[_RELATED_TRAY_KEY] = tray
        return False

    tray.append({"pmid": pid, "title": title, "source": source})
    st.session_state[_RELATED_TRAY_KEY] = tray
    return True


def _render_field(label: str, error_key: str, input_key: str, placeholder: str = "", height: int = 0) -> None:
    """Render an optional error banner followed by a text input or text area."""
    err = (st.session_state.get(error_key) or "").strip()
    if err:
        st.error(err)
    if height:
        st.text_area(label, key=input_key, placeholder=placeholder, height=height)
    else:
        st.text_input(label, key=input_key, placeholder=placeholder)


def _render_related_tray() -> None:
    tray = _get_related_tray()
    with st.expander("Clipboard", expanded=bool(tray)):

        if not tray:
            st.info("No PMIDs in clipboard yet. Use the clipboard icon in the related-paper lists below.")
            return

        for it in tray:
            pmid = (it.get("pmid") or "").strip()
            if not pmid:
                continue
            title = (it.get("title") or "").strip() or f"PMID {pmid}"
            st.markdown(f"- [{title}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/) — `{pmid}`")

        if st.button("Clear clipboard", key="pmid_related_tray_clear", width="stretch"):
            st.session_state[_RELATED_TRAY_KEY] = []
            st.rerun()


def _render_related_item_row(pmid: str, title: str, source: str = "") -> None:
    pid = _clean_pmid(pmid)
    if not pid:
        return
    raw_title = (title or "").strip() or pid
    safe_title = html.escape(raw_title)
    source_key = "".join([ch if ch.isalnum() else "_" for ch in source]).strip("_") or "related"
    c1, c2 = st.columns([18, 1], gap="small")
    with c1:
        st.markdown(
            f"- <a href='https://pubmed.ncbi.nlm.nih.gov/{pid}/' target='_blank'>{safe_title}</a> — <code>{pid}</code>",
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("📋", key=f"pmid_related_add_{source_key}_{pid}", help="Add PMID to clipboard", type="tertiary"):
            _add_related_pmid(pid, raw_title, source=source)
            st.rerun()


def render() -> None:
    st.title("📄 PMID → Abstract")

    if "pmid_input" not in st.session_state:
        st.session_state["pmid_input"] = st.session_state.get("last_pmid") or ""

    pmid_in = st.text_input("PMID", placeholder="e.g., 37212345", key="pmid_input")
    pmid = _clean_pmid(pmid_in)

    fetch_clicked = st.button("Fetch", type="primary", width="stretch")

    if fetch_clicked:
        if not pmid:
            st.error("Please enter a valid numeric PMID.")
            st.stop()

        if is_saved(pmid):
            for k in ["last_pmid", "last_abstract", "last_year", "last_pub_month", "last_journal", "last_title"]:
                st.session_state.pop(k, None)
            st.info(f"PMID {pmid} is saved in your database.")
            st.stop()

        with st.spinner("Fetching…"):
            try:
                xml_text = fetch_pubmed_xml(pmid)
                abstract = parse_abstract(xml_text)
                year = parse_year(xml_text)
                pub_month = parse_pub_month(xml_text)
                journal = parse_journal(xml_text)
                title = parse_title(xml_text)

                st.session_state["last_pmid"] = pmid
                st.session_state["last_abstract"] = abstract
                st.session_state["last_year"] = year
                st.session_state["last_pub_month"] = pub_month
                st.session_state["last_journal"] = journal
                st.session_state["last_title"] = title
            except requests.HTTPError as e:
                st.error(f"PubMed request failed: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.stop()

        _clear_gpt_errors()

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
            _clear_gpt_results()

    last_pmid = st.session_state.get("last_pmid")
    last_abstract = (st.session_state.get("last_abstract") or "").strip()
    last_year = (st.session_state.get("last_year") or "").strip()
    last_pub_month = (st.session_state.get("last_pub_month") or "").strip()
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
                if last_pub_month:
                    meta_bits.append(f"{last_year}-{last_pub_month}")
                else:
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
                                    last_pub_month,
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
                            _render_related_item_row(
                                n.get("pmid") or "",
                                n.get("title") or n.get("pmid") or "",
                                source="PubMed related",
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
                            title = (p.get("title") or "").strip() or (
                                p.get("pmid") or p.get("paperId") or "(no title)"
                            )
                            url = (p.get("url") or "").strip()
                            pmid_from_s2 = _clean_pmid(str(p.get("pmid") or ""))
                            if pmid_from_s2:
                                _render_related_item_row(
                                    pmid_from_s2,
                                    title,
                                    source="Semantic Scholar related",
                                )
                                continue
                            tag = ""
                            if (p.get("paperId") or "").strip():
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

            _render_related_tray()

        with right:
            _render_field("Author's conclusions", "gpt_conclusions_error", "authors_conclusions_input",
                          placeholder="Near-verbatim conclusion statement.", height=110)
            st.divider()
            _render_field("Specialty", "gpt_specialty_error", "specialty_input",
                          placeholder="e.g., Infectious Disease, Critical Care")
            st.divider()
            _render_field("Total patients", "gpt_patient_n_error", "patient_n_input",
                          placeholder="e.g., 250")
            st.divider()
            _render_field("Study design tags", "gpt_design_error", "study_design_input",
                          placeholder="e.g., Randomized controlled trial, Double-blind, Multicenter, USA", height=110)
            st.divider()
            _render_field("Patient details", "gpt_details_error", "patient_details_input",
                          placeholder="- Adults >=18 years with ...\n- Excluded if ...\n- Mean age ...\n- % male ...",
                          height=160)
            st.divider()
            _render_field("Intervention / comparison", "gpt_ic_error", "intervention_comparison_input",
                          placeholder="- Intervention: ...\n- Comparator: ...\n- Dose/duration: ...", height=140)
            st.divider()
            _render_field("Results", "gpt_results_error", "results_input",
                          placeholder="- Primary outcome: ... (effect estimate, CI)\n- Secondary outcome: ...",
                          height=200)
