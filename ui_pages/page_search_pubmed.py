from datetime import datetime, timedelta, timezone

import requests
import streamlit as st

from db import get_hidden_pubmed_pmids, get_saved_pmids, hide_pubmed_pmid
from extract import search_pubmed_by_date_filters
from pages_shared import _filter_search_pubmed_rows


def render() -> None:
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
    result_pmids = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        pmid = (r.get("pmid") or "").strip()
        if pmid:
            result_pmids.append(pmid)
    result_pmid_set = set(result_pmids)
    saved_in_results = result_pmid_set.intersection(get_saved_pmids(result_pmids))
    hidden_in_results = result_pmid_set.intersection(get_hidden_pubmed_pmids(result_pmids))
    saved_count = len(saved_in_results)
    hidden_only_count = len(hidden_in_results.difference(saved_in_results))

    rows = _filter_search_pubmed_rows(rows)
    rng = st.session_state.get("search_pubmed_range") or {}
    start_s = (rng.get("start") or "").strip()
    end_s = (rng.get("end") or "").strip()
    filters = st.session_state.get("search_pubmed_filters") or {}
    journal_label = (filters.get("journal") or "").strip()
    study_type_label = (filters.get("study_type") or "").strip()
    header_bits = []
    if start_s and end_s:
        header_bits.append(f"Range: {start_s} to {end_s}")
    if journal_label or study_type_label:
        header_bits.append(f"Filters: {journal_label or '—'} • {study_type_label or '—'}")
    if header_bits:
        st.caption(" | ".join(header_bits))
    st.caption("Saved articles and items marked 'Don't show again' are automatically excluded.")

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
