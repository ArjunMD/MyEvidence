import calendar
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests
import streamlit as st

from db import hide_pubmed_pmid, list_search_pubmed_ledger, upsert_search_pubmed_ledger
from extract import search_pubmed_by_date_filters_page
from pages_shared import _filter_search_pubmed_rows

SEARCH_FETCH_LIMIT = 200


def _run_search_page(
    start_date: str,
    end_date: str,
    journal_term: str,
    publication_type_terms: List[str],
    retmax: int,
    retstart: int,
) -> Dict[str, object]:
    page = search_pubmed_by_date_filters_page(
        start_date=start_date,
        end_date=end_date,
        journal_term=journal_term,
        publication_type_terms=publication_type_terms,
        retmax=int(retmax),
        retstart=int(retstart),
    )
    rows = [r for r in (page.get("rows") or []) if isinstance(r, dict)]
    try:
        total_count = int(page.get("total_count") or 0)
    except Exception:
        total_count = 0
    return {"rows": rows, "total_count": max(0, total_count)}


def _parse_year_month_parts(year_month: str) -> Dict[str, str]:
    ym = (year_month or "").strip()
    try:
        parts = ym.split("-")
        if len(parts) == 2:
            y = int(parts[0])
            m = int(parts[1])
            if 1 <= m <= 12:
                return {"year": str(y), "month": calendar.month_name[m]}
    except Exception:
        pass
    return {"year": ym or "—", "month": "—"}


def _parse_year_month_key(year_month: str) -> Optional[Tuple[int, int]]:
    ym = (year_month or "").strip()
    try:
        parts = ym.split("-")
        if len(parts) != 2:
            return None
        y = int(parts[0])
        m = int(parts[1])
        if y < 1900 or not (1 <= m <= 12):
            return None
        return (y, m)
    except Exception:
        return None


def _clearable_on_date_for_month(year: int, month: int):
    """
    Month is clearable 30 days after month-end to allow late indexing/backfill.
    """
    end_day = int(calendar.monthrange(int(year), int(month))[1])
    end_date = datetime(int(year), int(month), end_day, tzinfo=timezone.utc).date()
    return end_date + timedelta(days=30)


def _is_year_month_clearable(year_month: str, today) -> bool:
    ym = _parse_year_month_key(year_month)
    if ym is None:
        return True
    yy, mm = ym
    return bool(today >= _clearable_on_date_for_month(yy, mm))


def _render_search_ledger() -> None:
    st.markdown("##### Cleared Ledger")
    st.caption("Entries are eligible to clear 30 days after month-end.")
    today = datetime.now(timezone.utc).date()
    rows = list_search_pubmed_ledger(limit=100)
    cleared_rows = [
        r
        for r in rows
        if (r.get("is_cleared") or "0") == "1"
        and _is_year_month_clearable((r.get("year_month") or "").strip(), today=today)
    ]
    if not cleared_rows:
        st.caption("No cleared entries yet.")
        return

    for r in cleared_rows:
        ym = _parse_year_month_parts(r.get("year_month") or "")
        journal = (r.get("journal_label") or "").strip() or "—"
        study_type = (r.get("study_type_label") or "").strip() or "—"
        year = (ym.get("year") or "").strip() or "—"
        month = (ym.get("month") or "").strip() or "—"

        st.markdown(f"- {journal} · {study_type} · {year} · {month}")


def render() -> None:
    st.title("🔎 Search PubMed")
    st.caption("Search PubMed by one calendar month, journal, and study type.")

    today = datetime.now(timezone.utc).date()
    default_month_date = today - timedelta(days=30)
    default_year = int(default_month_date.year)
    default_month = int(default_month_date.month)
    min_year = max(1900, default_year - 25)
    year_options = list(range(default_year, min_year - 1, -1))

    c1, c2 = st.columns(2)
    with c1:
        selected_year = st.selectbox("Year", options=year_options, index=0, key="search_pubmed_year")
    with c2:
        selected_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=max(0, min(11, default_month - 1)),
            format_func=lambda m: calendar.month_name[int(m)],
            key="search_pubmed_month",
        )

    journal_query_by_label = {
        "NEJM": '"N Engl J Med"[jour]',
        "JAMA": '"JAMA"[jour]',
        "Lancet": '"Lancet"[jour]',
        "BMJ": '"BMJ"[jour]',
        "Nat Med": '"Nat Med"[jour]',
    }
    study_type_queries = {
        "Clinical Trial": ['"Clinical Trial"[Publication Type]'],
        "Meta analysis": ['"Meta-Analysis"[Publication Type]'],
        "Systematic Review": ['"Systematic Review"[Publication Type]'],
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

    b_search, b_clear = st.columns(2)
    with b_search:
        search_clicked = st.button("Search", type="primary", width="stretch", key="search_pubmed_btn")
    with b_clear:
        clear_clicked = st.button("Clear search", width="stretch", key="search_pubmed_clear_btn")

    if clear_clicked:
        for k in ["search_pubmed_rows", "search_pubmed_total_count", "search_pubmed_range", "search_pubmed_filters"]:
            st.session_state.pop(k, None)
        st.rerun()

    if search_clicked:
        try:
            start_date = datetime(int(selected_year), int(selected_month), 1, tzinfo=timezone.utc).date()
            end_day = int(calendar.monthrange(int(selected_year), int(selected_month))[1])
            end_date = datetime(int(selected_year), int(selected_month), end_day, tzinfo=timezone.utc).date()
        except Exception:
            st.error("Invalid year/month selection.")
            st.stop()

        start_s = start_date.strftime("%Y/%m/%d")
        end_s = end_date.strftime("%Y/%m/%d")
        journal_term = journal_query_by_label.get(journal_label, "")
        pub_terms = study_type_queries.get(study_type_label, [])
        try:
            with st.spinner("Searching PubMed…"):
                page = _run_search_page(
                    start_date=start_s,
                    end_date=end_s,
                    journal_term=journal_term,
                    publication_type_terms=pub_terms,
                    retmax=int(SEARCH_FETCH_LIMIT),
                    retstart=0,
                )
            rows = [r for r in (page.get("rows") or []) if isinstance(r, dict)]
            total_count = int(page.get("total_count") or 0)
            st.session_state["search_pubmed_rows"] = rows
            st.session_state["search_pubmed_total_count"] = total_count
            st.session_state["search_pubmed_range"] = {
                "start": start_s,
                "end": end_s,
                "year_month": f"{int(selected_year)}-{int(selected_month):02d}",
                "year_month_label": f"{calendar.month_name[int(selected_month)]} {int(selected_year)}",
            }
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
        st.divider()
        _render_search_ledger()
        return

    total_count = int(st.session_state.get("search_pubmed_total_count") or 0)
    rows = [r for r in (st.session_state.get("search_pubmed_rows") or []) if isinstance(r, dict)]
    visible_rows = _filter_search_pubmed_rows(rows)

    visible_count = len(visible_rows)
    hidden_count = max(0, total_count - visible_count)
    rng = st.session_state.get("search_pubmed_range") or {}
    start_s = (rng.get("start") or "").strip()
    end_s = (rng.get("end") or "").strip()
    ym_label = (rng.get("year_month_label") or "").strip()
    filters = st.session_state.get("search_pubmed_filters") or {}
    journal_label = (filters.get("journal") or "").strip()
    study_type_label = (filters.get("study_type") or "").strip()
    header_bits = []
    if ym_label:
        header_bits.append(f"Month: {ym_label}")
    elif start_s and end_s:
        header_bits.append(f"Range: {start_s} to {end_s}")
    if journal_label or study_type_label:
        header_bits.append(f"Filters: {journal_label or '—'} • {study_type_label or '—'}")
    if header_bits:
        st.caption(" | ".join(header_bits))
    st.caption(f"{total_count} matches ({visible_count} visible, {hidden_count} hidden)")

    ym_key = (rng.get("year_month") or "").strip()
    is_verified = total_count <= int(SEARCH_FETCH_LIMIT)
    is_time_clearable = _is_year_month_clearable(ym_key, today=today)
    is_cleared = bool(visible_count == 0 and is_verified and is_time_clearable)
    upsert_search_pubmed_ledger(
        year_month=ym_key,
        journal_label=journal_label,
        study_type_label=study_type_label,
        total_matches=total_count,
        visible_matches=visible_count,
        hidden_matches=hidden_count,
        is_cleared=is_cleared,
        is_verified=is_verified,
    )

    if total_count > int(SEARCH_FETCH_LIMIT):
        st.warning(
            f"Failsafe: this monthly query returned {total_count} matches (> {SEARCH_FETCH_LIMIT}). "
            f"Only the first {SEARCH_FETCH_LIMIT} were fetched."
        )

    if not visible_rows:
        st.info("No visible results for this month and filter selection.")
        st.divider()
        _render_search_ledger()
        return

    for r in visible_rows:
        title = (r.get("title") or "").strip() or "(no title)"
        pmid = (r.get("pmid") or "").strip() or "—"
        c_left, c_right = st.columns([5, 3])
        with c_left:
            st.markdown(f"- {title} — `{pmid}`")
        with c_right:
            if pmid != "—":
                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if st.button(
                        "Don't show again",
                        key=f"search_pubmed_hide_{pmid}",
                        use_container_width=True,
                    ):
                        hide_pubmed_pmid(pmid)
                        st.rerun()
                with b2:
                    if st.button(
                        "Open abstract",
                        key=f"search_pubmed_open_abstract_{pmid}",
                        use_container_width=True,
                    ):
                        try:
                            st.query_params["open_abs_pmid"] = pmid
                        except Exception:
                            st.experimental_set_query_params(open_abs_pmid=pmid)
                        st.rerun()

    st.divider()
    _render_search_ledger()
