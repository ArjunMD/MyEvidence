import html
from typing import Dict, List

import streamlit as st

from db import list_browse_guideline_items, list_browse_items
from pages_shared import BROWSE_MAX_ROWS, _browse_search_link, _split_specialties, _year_sort_key


def render() -> None:
    st.title("🗂️ Browse")

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
