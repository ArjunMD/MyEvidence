import html
from typing import Dict, List

import streamlit as st

from db import list_browse_guideline_items, list_browse_items, search_guidelines, search_records
from pages_shared import (
    BROWSE_MAX_ROWS,
    _add_to_evidence_cart,
    _browse_cart_link,
    _browse_search_link,
    _clear_evidence_cart,
    _get_evidence_cart_ids,
    _remove_from_evidence_cart,
    _split_specialties,
    _year_sort_key,
)

BROWSE_INLINE_CART_WIDGET_LIMIT = 1200


def _month_sort_value(item: Dict[str, str]) -> int:
    if (item.get("type") or "").strip().lower() == "guideline":
        return 0
    raw = (item.get("pub_month") or "").strip()
    if raw.isdigit():
        n = int(raw)
        if 1 <= n <= 12:
            return n
    return 0


def _browse_item_sort_key(item: Dict[str, str]) -> tuple:
    item_type = (item.get("type") or "").lower()
    title = (item.get("title") or "").lower()
    pmid = (item.get("pmid") or "").lower()
    gid = (item.get("guideline_id") or "").lower()
    return (item_type, -_month_sort_value(item), title, pmid, gid)


def _cart_badge(in_cart: bool) -> str:
    if not in_cart:
        return ""
    return (
        "<span style='background:#EAF7F0; color:#125C3A; border:1px solid #B9E3CB; "
        "border-radius:999px; padding:0.02rem 0.4rem; margin-left:0.35rem; font-size:0.76em;'>"
        "In cart</span>"
    )


def _set_cart_toast(msg: str) -> None:
    st.session_state["browse_cart_toast"] = (msg or "").strip()


def _toggle_cart_item(item_type: str, item_id: str, in_cart: bool) -> None:
    item_kind = (item_type or "").strip().lower()
    item_key = (item_id or "").strip()
    if not item_key:
        return

    if item_kind == "guideline":
        if in_cart:
            stats = _remove_from_evidence_cart(gid=item_key)
            if (stats.get("guideline_removed") or "0") == "1":
                _set_cart_toast(f"Removed guideline `{item_key}` from evidence cart.")
        else:
            stats = _add_to_evidence_cart(gid=item_key)
            if (stats.get("guideline_added") or "0") == "1":
                _set_cart_toast(f"Added guideline `{item_key}` to evidence cart.")
        return

    if in_cart:
        stats = _remove_from_evidence_cart(pmid=item_key)
        if (stats.get("paper_removed") or "0") == "1":
            _set_cart_toast(f"Removed PMID `{item_key}` from evidence cart.")
    else:
        stats = _add_to_evidence_cart(pmid=item_key)
        if (stats.get("paper_added") or "0") == "1":
            _set_cart_toast(f"Added PMID `{item_key}` to evidence cart.")


def _clear_cart_from_browse() -> None:
    _clear_evidence_cart()
    _set_cart_toast("Evidence cart cleared.")


def _render_browse_item(
    it: Dict[str, str],
    cart_pmids: set,
    cart_gids: set,
    use_widget_cart: bool,
    row_key: str,
    browse_q: str,
    by_specialty: bool,
    guidelines_only: bool,
) -> None:
    if (it.get("type") or "") == "guideline":
        title = (it.get("title") or "").strip() or "(no name)"
        gid = (it.get("guideline_id") or "").strip()
        safe_title = html.escape(title)
        if gid:
            in_cart = gid in cart_gids
            if use_widget_cart:
                c_text, c_btn = st.columns([18, 1], gap="small")
                with c_text:
                    st.markdown(
                        f"- {safe_title}{_browse_search_link(gid=gid)}{_cart_badge(in_cart)}",
                        unsafe_allow_html=True,
                    )
                with c_btn:
                    st.button(
                        "➖" if in_cart else "➕",
                        key=f"browse_cart_btn_{row_key}",
                        help="Remove from evidence cart" if in_cart else "Add to evidence cart",
                        on_click=_toggle_cart_item,
                        args=("guideline", gid, in_cart),
                        use_container_width=True,
                    )
            else:
                st.markdown(
                    f"- {safe_title}{_browse_search_link(gid=gid)}"
                    f"{_browse_cart_link(gid=gid, in_cart=in_cart, browse_q=browse_q, by_specialty=by_specialty, guidelines_only=guidelines_only)}"
                    f"{_cart_badge(in_cart)}",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(f"- {safe_title}", unsafe_allow_html=True)
        return

    pmid = (it.get("pmid") or "").strip()
    title = (it.get("title") or "").strip() or "(no title)"
    concl = (it.get("authors_conclusions") or "").strip()

    pub_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    safe_title = html.escape(title)
    safe_pmid = html.escape(pmid)
    in_cart = pmid in cart_pmids

    j = (it.get("journal") or "").strip()
    pn = (it.get("patient_n") or "").strip()

    meta_bits = []
    if pn:
        meta_bits.append(f"N={pn}")
    if j:
        meta_bits.append(j)
    meta = ", ".join(meta_bits)

    if use_widget_cart:
        c_text, c_btn = st.columns([18, 1], gap="small")
        with c_text:
            st.markdown(
                f"- <a href='{pub_url}' target='_blank'>{safe_title}</a> — <code>{safe_pmid}</code>"
                f"{_browse_search_link(pmid=pmid)}{_cart_badge(in_cart)}",
                unsafe_allow_html=True,
            )
            if concl:
                st.caption(f"{concl}{f' ({meta})' if meta else ''}")
            elif meta:
                st.caption(f"({meta})")
        with c_btn:
            st.button(
                "➖" if in_cart else "➕",
                key=f"browse_cart_btn_{row_key}",
                help="Remove from evidence cart" if in_cart else "Add to evidence cart",
                on_click=_toggle_cart_item,
                args=("paper", pmid, in_cart),
                use_container_width=True,
            )
        return

    st.markdown(
        f"- <a href='{pub_url}' target='_blank'>{safe_title}</a> — <code>{safe_pmid}</code>"
        f"{_browse_search_link(pmid=pmid)}"
        f"{_browse_cart_link(pmid=pmid, in_cart=in_cart, browse_q=browse_q, by_specialty=by_specialty, guidelines_only=guidelines_only)}"
        f"{_cart_badge(in_cart)}",
        unsafe_allow_html=True,
    )
    if concl:
        st.caption(f"{concl}{f' ({meta})' if meta else ''}")
    elif meta:
        st.caption(f"({meta})")


@st.fragment
def _render_browse_body() -> None:
    flash = (st.session_state.pop("evidence_cart_flash", "") or "").strip()
    if flash:
        st.toast(flash)
    toast = (st.session_state.pop("browse_cart_toast", "") or "").strip()
    if toast:
        st.toast(toast)

    cart = _get_evidence_cart_ids()
    cart_pmids = set(cart.get("pmids") or [])
    cart_gids = set(cart.get("guideline_ids") or [])
    cart_total = len(cart_pmids) + len(cart_gids)
    c_cart_l, c_cart_r = st.columns([5, 1], gap="small")
    with c_cart_l:
        st.caption(
            f"Evidence cart: {len(cart_pmids)} abstracts • {len(cart_gids)} guidelines ({cart_total} total)"
        )
    with c_cart_r:
        st.button(
            "Clear cart",
            key="browse_clear_cart_btn",
            on_click=_clear_cart_from_browse,
            disabled=(cart_total == 0),
            use_container_width=True,
        )

    by_specialty = st.toggle(
        "Browse by specialty",
        value=False,
        key="browse_by_specialty",
    )
    guidelines_only = st.toggle(
        "Guidelines only",
        value=False,
        key="browse_guidelines_only",
    )
    browse_q = st.text_input(
        "Search",
        placeholder='Filter this browse view by any field. Supports AND, OR, and "exact phrase"…',
        key="db_browse_any",
    )
    st.caption('Example: `heart AND "reduced ejection fraction"` or `sepsis OR septic shock`')

    items: List[Dict[str, str]] = []
    if guidelines_only:
        items.extend(list_browse_guideline_items(limit=BROWSE_MAX_ROWS))
    else:
        items.extend(list_browse_items(limit=BROWSE_MAX_ROWS))
        items.extend(list_browse_guideline_items(limit=BROWSE_MAX_ROWS))

    if not items:
        if guidelines_only:
            st.info("No saved guidelines yet.")
        else:
            st.info("No saved items yet.")
        st.stop()

    q = (browse_q or "").strip()
    if q:
        if guidelines_only:
            matched_guideline_rows = search_guidelines(limit=BROWSE_MAX_ROWS, q=q)
            matched_gids = {
                (r.get("guideline_id") or "").strip()
                for r in (matched_guideline_rows or [])
                if (r.get("guideline_id") or "").strip()
            }
            items = [
                it
                for it in items
                if (it.get("type") or "").strip() == "guideline"
                and (it.get("guideline_id") or "").strip() in matched_gids
            ]
        else:
            matched_paper_rows = search_records(limit=BROWSE_MAX_ROWS, q=q)
            matched_guideline_rows = search_guidelines(limit=BROWSE_MAX_ROWS, q=q)
            matched_pmids = {
                (r.get("pmid") or "").strip()
                for r in (matched_paper_rows or [])
                if (r.get("pmid") or "").strip()
            }
            matched_gids = {
                (r.get("guideline_id") or "").strip()
                for r in (matched_guideline_rows or [])
                if (r.get("guideline_id") or "").strip()
            }
            items = [
                it
                for it in items
                if (
                    ((it.get("type") or "").strip() == "guideline" and (it.get("guideline_id") or "").strip() in matched_gids)
                    or ((it.get("type") or "").strip() != "guideline" and (it.get("pmid") or "").strip() in matched_pmids)
                )
            ]

        if not items:
            st.info("No matches in current browse view.")
            st.stop()

    use_widget_cart = len(items) <= int(BROWSE_INLINE_CART_WIDGET_LIMIT)
    if not use_widget_cart:
        st.caption(
            "Large result set detected. Inline no-reload cart buttons are disabled for performance; "
            "add a search filter to enable them."
        )

    row_idx = 0
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
                    rows = sorted(years_map.get(y, []), key=_browse_item_sort_key)
                    for it in rows:
                        row_idx += 1
                        _render_browse_item(
                            it,
                            cart_pmids=cart_pmids,
                            cart_gids=cart_gids,
                            use_widget_cart=use_widget_cart,
                            row_key=f"{row_idx}",
                            browse_q=browse_q,
                            by_specialty=by_specialty,
                            guidelines_only=guidelines_only,
                        )

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
            rows = sorted(rows, key=_browse_item_sort_key)

            for it in rows:
                row_idx += 1
                _render_browse_item(
                    it,
                    cart_pmids=cart_pmids,
                    cart_gids=cart_gids,
                    use_widget_cart=use_widget_cart,
                    row_key=f"{row_idx}",
                    browse_q=browse_q,
                    by_specialty=by_specialty,
                    guidelines_only=guidelines_only,
                )


def render() -> None:
    st.title("🗂️ Browse studies")
    _render_browse_body()
