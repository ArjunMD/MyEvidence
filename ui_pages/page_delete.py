from typing import Dict, List

import streamlit as st

from db import (
    delete_guideline,
    delete_record,
    get_guideline_meta,
    get_record,
    list_guidelines,
    list_recent_records,
    search_guidelines,
    search_records,
)


def render() -> None:
    st.title("🗑️ Delete")

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
        else:

            def _paper_label(r: Dict[str, str]) -> str:
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
            st.write(f"**Specialty:** {(rec.get('specialty') or paper_rows[sel_i].get('specialty') or '').strip()}")

            with st.expander("Show abstract", expanded=False):
                abs_txt = (rec.get("abstract") or "").strip()
                if abs_txt:
                    st.write(abs_txt)

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

        def _guideline_label(r: Dict[str, str]) -> str:
            title = (r.get("title") or "").strip()
            year = (r.get("year") or "").strip()
            spec = (r.get("specialty") or "").strip()
            bits = [title]
            if year:
                bits.append(f"({year})")
            if spec:
                bits.append(f"— {spec}")
            return " ".join([b for b in bits if b]).strip()

        gid_options = [g["guideline_id"] for g in guidelines if (g.get("guideline_id") or "").strip()]
        gid_to_row = {g["guideline_id"]: g for g in guidelines if (g.get("guideline_id") or "").strip()}

        if not gid_options:
            st.info("No saved guidelines found.")
            st.stop()

        _state_key = "delete_guideline_selected_gid"

        prev = st.session_state.get(_state_key)
        if prev and prev not in gid_options:
            st.session_state.pop(_state_key, None)

        sel_gid = st.selectbox(
            "Select a guideline",
            options=gid_options,
            format_func=lambda gid: _guideline_label(
                gid_to_row.get(gid, {"guideline_id": gid, "title": gid, "year": "", "specialty": ""})
            ),
            key=_state_key,
        )

        meta = get_guideline_meta(sel_gid) or {}

        st.write(f"**Filename:** {(meta.get('filename') or '').strip()}")
        st.write(f"**Uploaded:** {(meta.get('uploaded_at') or '').strip()}")

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
