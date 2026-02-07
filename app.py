import streamlit as st

from db import (
    _db_path,
    db_count,
    db_count_all,
    ensure_folders_schema,
    ensure_guidelines_schema,
    ensure_schema,
    guidelines_count,
)
from ui_pages.page_about import render as render_about
from ui_pages.page_db_browse import render as render_db_browse
from ui_pages.page_db_search import render as render_db_search
from ui_pages.page_delete import render as render_delete
from ui_pages.page_generate_meta import render as render_generate_meta
from ui_pages.page_guidelines import render as render_guidelines
from ui_pages.page_history import render as render_history
from ui_pages.page_pmid_abstract import render as render_pmid_abstract
from ui_pages.page_search_pubmed import render as render_search_pubmed
from pages_shared import _clean_pmid, _clear_query_params, _get_query_params, _qp_first

st.set_page_config(page_title="PMID → Abstract", page_icon="📄", layout="wide")
ensure_schema()
ensure_guidelines_schema()
ensure_folders_schema()

_qp = _get_query_params()
_open_pmid = _clean_pmid(_qp_first(_qp, "pmid"))
_open_gid = (_qp_first(_qp, "gid") or "").strip()
_open_delrec = (_qp_first(_qp, "delrec") or "").strip()
_open_abs_pmid = _clean_pmid(_qp_first(_qp, "open_abs_pmid"))

if _open_abs_pmid:
    st.session_state["nav_page"] = "PMID → Abstract"
    st.session_state["pmid_input"] = _open_abs_pmid
    _clear_query_params()
elif _open_pmid or _open_gid:
    st.session_state["nav_page"] = "DB Search"
    st.session_state["db_search_any"] = ""

    if _open_pmid:
        st.session_state["db_search_open_pmid"] = _open_pmid
        st.session_state.pop("db_search_open_gid", None)
    if _open_gid:
        st.session_state["db_search_open_gid"] = _open_gid
        st.session_state.pop("db_search_open_pmid", None)

    if _open_delrec:
        st.session_state["db_search_delete_rec"] = _open_delrec
        if _open_gid:
            st.session_state[f"dbs_guideline_edit_{_open_gid}"] = True

    _clear_query_params()

page = st.sidebar.radio(
    "Navigate",
    [
        "PMID → Abstract",
        "Guidelines (PDF Upload)",
        "DB Search",
        "DB Browse",
        "Generate meta",
        "Search PubMed",
        "Delete",
        "About",
        "History",
    ],
    index=0,
    key="nav_page",
)

st.sidebar.caption(f"DB: `{_db_path()}`")
st.sidebar.caption(
    f"Saved: **{db_count_all()}**  "
    f"({db_count()} abstracts, {guidelines_count()} guidelines)"
)

if page == "PMID → Abstract":
    render_pmid_abstract()
elif page == "Guidelines (PDF Upload)":
    render_guidelines()
elif page == "DB Search":
    render_db_search()
elif page == "DB Browse":
    render_db_browse()
elif page == "Generate meta":
    render_generate_meta()
elif page == "Search PubMed":
    render_search_pubmed()
elif page == "Delete":
    render_delete()
elif page == "About":
    render_about()
elif page == "History":
    render_history()
