import streamlit as st

from db import (
    _db_path,
    db_count,
    db_count_all,
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
from pages_shared import (
    _add_to_evidence_cart,
    _clean_pmid,
    _clear_evidence_cart,
    _clear_query_params,
    _get_query_params,
    _qp_first,
    _remove_from_evidence_cart,
)

st.set_page_config(page_title="PMID → Abstract", page_icon="📄", layout="wide")
ensure_schema()
ensure_guidelines_schema()

_qp = _get_query_params()
_open_pmid = _clean_pmid(_qp_first(_qp, "pmid"))
_open_gid = (_qp_first(_qp, "gid") or "").strip()
_open_delrec = (_qp_first(_qp, "delrec") or "").strip()
_open_abs_pmid = _clean_pmid(_qp_first(_qp, "open_abs_pmid"))
_cart_add_pmid = _clean_pmid(_qp_first(_qp, "cart_add_pmid"))
_cart_remove_pmid = _clean_pmid(_qp_first(_qp, "cart_remove_pmid"))
_cart_add_gid = (_qp_first(_qp, "cart_add_gid") or "").strip()
_cart_remove_gid = (_qp_first(_qp, "cart_remove_gid") or "").strip()
_cart_clear = (_qp_first(_qp, "cart_clear") or "").strip()
_browse_q = (_qp_first(_qp, "browse_q") or "").strip()
_browse_spec = (_qp_first(_qp, "browse_spec") or "").strip().lower()
_browse_guidelines = (_qp_first(_qp, "browse_guidelines") or "").strip().lower()


def _qp_bool(raw: str, default: bool = False) -> bool:
    s = (raw or "").strip().lower()
    if not s:
        return bool(default)
    return s in ("1", "true", "t", "yes", "y", "on")


def _restore_browse_state_from_qp() -> None:
    if "browse_q" in _qp:
        st.session_state["db_browse_any"] = _browse_q
    if "browse_spec" in _qp:
        st.session_state["browse_by_specialty"] = _qp_bool(
            _browse_spec, default=bool(st.session_state.get("browse_by_specialty", False))
        )
    if "browse_guidelines" in _qp:
        st.session_state["browse_guidelines_only"] = _qp_bool(
            _browse_guidelines, default=bool(st.session_state.get("browse_guidelines_only", False))
        )

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
elif _cart_clear == "1":
    _clear_evidence_cart()
    _restore_browse_state_from_qp()
    st.session_state["evidence_cart_flash"] = "Evidence cart cleared."
    st.session_state["nav_page"] = "Browse studies"
    _clear_query_params()
elif _cart_add_pmid or _cart_add_gid or _cart_remove_pmid or _cart_remove_gid:
    _restore_browse_state_from_qp()
    flash_msgs = []

    if _cart_add_pmid:
        stats = _add_to_evidence_cart(pmid=_cart_add_pmid)
        if (stats.get("paper_added") or "0") == "1":
            flash_msgs.append(f"Added PMID `{_cart_add_pmid}` to evidence cart.")
    if _cart_add_gid:
        stats = _add_to_evidence_cart(gid=_cart_add_gid)
        if (stats.get("guideline_added") or "0") == "1":
            flash_msgs.append(f"Added guideline `{_cart_add_gid}` to evidence cart.")
    if _cart_remove_pmid:
        stats = _remove_from_evidence_cart(pmid=_cart_remove_pmid)
        if (stats.get("paper_removed") or "0") == "1":
            flash_msgs.append(f"Removed PMID `{_cart_remove_pmid}` from evidence cart.")
    if _cart_remove_gid:
        stats = _remove_from_evidence_cart(gid=_cart_remove_gid)
        if (stats.get("guideline_removed") or "0") == "1":
            flash_msgs.append(f"Removed guideline `{_cart_remove_gid}` from evidence cart.")

    if not flash_msgs:
        flash_msgs.append("No evidence cart changes were needed.")
    st.session_state["evidence_cart_flash"] = " ".join(flash_msgs)
    st.session_state["nav_page"] = "Browse studies"
    _clear_query_params()

if st.session_state.get("nav_page") in ("DB Search", "View"):
    st.session_state["nav_page"] = "Single-study view"
if st.session_state.get("nav_page") == "DB Browse":
    st.session_state["nav_page"] = "Browse studies"

page = st.sidebar.radio(
    "Navigate",
    [
        "PMID → Abstract",
        "Guidelines (PDF Upload)",
        "Single-study view",
        "Browse studies",
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
elif page == "Browse studies":
    render_db_browse()
elif page == "Single-study view":
    render_db_search()
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
