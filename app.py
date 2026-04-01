import os

import streamlit as st

from db import (
    db_count,
    db_count_all,
    ensure_guidelines_schema,
    ensure_pathways_schema,
    ensure_schema,
    guidelines_count,
)
from ui_pages.page_about import render as render_about
from ui_pages.page_db_browse import render as render_db_browse
from ui_pages.page_db_search import render as render_db_search
from ui_pages.page_delete import render as render_delete
from ui_pages.page_guidelines import render as render_guidelines
from ui_pages.page_history import render as render_history
from ui_pages.page_pmid_abstract import render as render_pmid_abstract
from ui_pages.page_bedside import render as render_physical_exam
from ui_pages.page_pathways import render as render_pathways
from ui_pages.page_reminders_id import render as render_reminders_id
from ui_pages.page_reminders_cardiology import render as render_reminders_cardiology
from ui_pages.page_reminders_neuro import render as render_reminders_neuro
from ui_pages.page_reminders_pulm import render as render_reminders_pulm
from ui_pages.page_reminders_nephro import render as render_reminders_nephro
from ui_pages.page_reminders_gi import render as render_reminders_gi
from ui_pages.page_reminders_onc import render as render_reminders_onc
from ui_pages.page_rrt_meds import render as render_rrt_meds
from ui_pages.page_search_pubmed import render as render_search_pubmed
from pages_shared import (
    _clean_pmid,
    _clear_query_params,
    _get_query_params,
    _qp_first,
)

st.set_page_config(page_title="PMID → Abstract", page_icon="📄", layout="wide")
ensure_schema()
ensure_guidelines_schema()
ensure_pathways_schema()

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
    st.session_state["nav_page"] = "Single-study view"
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

if st.session_state.get("nav_page") in ("DB Search", "View"):
    st.session_state["nav_page"] = "Single-study view"
if st.session_state.get("nav_page") == "DB Browse":
    st.session_state["nav_page"] = "Browse studies"
if st.session_state.get("nav_page") == "Rapid Reference":
    st.session_state["nav_page"] = "PMID → Abstract"
    st.session_state["rr_page"] = "RRT"
    st.session_state["active_section"] = "rr"

_IS_CLOUD = os.path.expanduser("~") == "/home/appuser"

_CLOUD_HIDDEN_PAGES = {
    "PMID → Abstract",
    "Upload Guideline",
    "Search PubMed",
    "Manage",
    "About",
}

_NAV_PAGES_ALL = [
    "PMID → Abstract",
    "Upload Guideline",
    "Browse studies",
    "Single-study view",
    "Search PubMed",
    "Manage",
    "About",
    "History",
]

_NAV_PAGES = [p for p in _NAV_PAGES_ALL if not (_IS_CLOUD and p in _CLOUD_HIDDEN_PAGES)]

_RR_PAGES = ["RRT", "Bedside"]

_RM_PAGES = [
    "Infectious Disease",
    "Cardiology",
    "Neurology",
    "Pulm / Critical Care",
    "Nephrology",
    "GI",
    "Oncology",
]

if "active_section" not in st.session_state:
    st.session_state["active_section"] = "nav"


def _on_nav_change() -> None:
    st.session_state["active_section"] = "nav"
    st.session_state["rr_page"] = None
    st.session_state["rm_page"] = None
    st.session_state["pw_page"] = None


def _on_rr_change() -> None:
    st.session_state["active_section"] = "rr"
    st.session_state["rm_page"] = None
    st.session_state["pw_page"] = None


def _on_rm_change() -> None:
    st.session_state["active_section"] = "rm"
    st.session_state["rr_page"] = None
    st.session_state["pw_page"] = None


def _on_pw_change() -> None:
    st.session_state["active_section"] = "pw"
    st.session_state["rr_page"] = None
    st.session_state["rm_page"] = None


_default_nav_index = _NAV_PAGES.index("Browse studies") if _IS_CLOUD else 0

nav_page = st.sidebar.radio(
    "Navigate",
    _NAV_PAGES,
    index=_default_nav_index,
    key="nav_page",
    on_change=_on_nav_change,
)

st.sidebar.caption(
    f"Saved: **{db_count_all()}**  "
    f"({db_count()} abstracts, {guidelines_count()} guidelines)"
)

st.sidebar.markdown("---")

rr_page = st.sidebar.radio(
    "\U0001f6a8 Rapid Reference",
    _RR_PAGES,
    index=None,
    key="rr_page",
    on_change=_on_rr_change,
)

st.sidebar.markdown("---")

rm_page = st.sidebar.radio(
    "\U0001f4dd Reminders",
    _RM_PAGES,
    index=None,
    key="rm_page",
    on_change=_on_rm_change,
)

st.sidebar.markdown("---")

pw_page = st.sidebar.radio(
    "\U0001f4cb Personalized Pathways",
    ["Pathways"],
    index=None,
    key="pw_page",
    on_change=_on_pw_change,
)

if st.session_state["active_section"] == "pw":
    render_pathways()
elif st.session_state["active_section"] == "rm":
    if rm_page == "Infectious Disease":
        render_reminders_id()
    elif rm_page == "Cardiology":
        render_reminders_cardiology()
    elif rm_page == "Neurology":
        render_reminders_neuro()
    elif rm_page == "Pulm / Critical Care":
        render_reminders_pulm()
    elif rm_page == "Nephrology":
        render_reminders_nephro()
    elif rm_page == "GI":
        render_reminders_gi()
    elif rm_page == "Oncology":
        render_reminders_onc()
elif st.session_state["active_section"] == "rr":
    if rr_page == "RRT":
        render_rrt_meds()
    elif rr_page == "Bedside":
        render_physical_exam()
elif nav_page == "PMID → Abstract":
    render_pmid_abstract()
elif nav_page == "Upload Guideline":
    render_guidelines()
elif nav_page == "Browse studies":
    render_db_browse()
elif nav_page == "Single-study view":
    render_db_search()
elif nav_page == "Search PubMed":
    render_search_pubmed()
elif nav_page == "Manage":
    render_delete()
elif nav_page == "About":
    render_about()
elif nav_page == "History":
    render_history()
