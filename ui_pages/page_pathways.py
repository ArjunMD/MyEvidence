import streamlit as st

from db import (
    add_pathway_citation,
    create_pathway,
    delete_pathway,
    get_guideline_recommendations_display,
    get_pathway,
    get_record,
    get_guideline_meta,
    list_pathway_citations,
    list_pathways,
    remove_pathway_citation,
    search_guidelines,
    search_records,
    update_pathway_content,
)


# ---- helpers ----

def _citation_display(item_type: str, item_id: str) -> str:
    """Return a short human-readable string for a citation."""
    if item_type == "abstract":
        rec = get_record(item_id)
        if not rec:
            return f"Abstract {item_id} (not found)"
        title = rec.get("title") or "Untitled"
        year = rec.get("year") or ""
        journal = rec.get("journal") or ""
        parts = [f'"{title}"']
        if year:
            parts.append(f"({year})")
        if journal:
            parts.append(f"\u2014 *{journal}*")
        return " ".join(parts)
    else:
        meta = get_guideline_meta(item_id)
        if not meta:
            return f"Guideline {item_id} (not found)"
        name = meta.get("guideline_name") or meta.get("filename") or "Untitled"
        year = meta.get("pub_year") or ""
        if year:
            return f"{name} ({year})"
        return name


def _render_citation_preview(item_type: str, item_id: str) -> None:
    """Render a read-only preview of a citation inside a popover."""
    if item_type == "abstract":
        rec = get_record(item_id)
        if not rec:
            st.warning("Record not found.")
            return
        title = rec.get("title") or "Untitled"
        st.markdown(f"**{title}**")
        meta_bits = []
        if rec.get("journal"):
            meta_bits.append(rec["journal"])
        if rec.get("year"):
            meta_bits.append(rec["year"])
        if meta_bits:
            st.caption(" \u2022 ".join(meta_bits))
        if rec.get("patient_n") or rec.get("study_design"):
            n = rec.get("patient_n") or "\u2014"
            design = rec.get("study_design") or "\u2014"
            st.markdown(f"**N:** {n} &nbsp; **Design:** {design}")
        for label, field in [
            ("**P \u2014 Population:**", "patient_details"),
            ("**I/C \u2014 Intervention / Comparison:**", "intervention_comparison"),
            ("**O \u2014 Outcomes / Results:**", "results"),
        ]:
            val = (rec.get(field) or "").strip()
            if val:
                st.markdown(label)
                lines = val.splitlines()
                for ln in lines:
                    ln = ln.strip()
                    if ln:
                        st.markdown(f"- {ln}" if not ln.startswith("- ") else ln)
        concl = (rec.get("authors_conclusions") or "").strip()
        if concl:
            st.markdown("**Authors\u2019 conclusion:**")
            st.markdown(concl)
    else:
        meta = get_guideline_meta(item_id)
        if not meta:
            st.warning("Guideline not found.")
            return
        name = meta.get("guideline_name") or meta.get("filename") or "Untitled"
        st.markdown(f"**{name}**")
        bits = []
        if meta.get("pub_year"):
            bits.append(meta["pub_year"])
        if meta.get("specialty"):
            bits.append(meta["specialty"])
        if bits:
            st.caption(" \u2022 ".join(bits))
        disp = (get_guideline_recommendations_display(item_id) or "").strip()
        if disp:
            st.markdown(disp)
        else:
            st.info("No recommendations extracted yet.")


def _render_references_view(citations: list) -> None:
    """Render the numbered reference list in view mode."""
    if not citations:
        return
    st.markdown("---")
    st.markdown("#### References")
    for c in citations:
        key = c["cite_key"]
        display = _citation_display(c["item_type"], c["item_id"])
        col_text, col_icon = st.columns([0.93, 0.07])
        with col_text:
            st.markdown(f"**[{key}]** {display}")
        with col_icon:
            with st.popover("\U0001f50d", use_container_width=True):
                _render_citation_preview(c["item_type"], c["item_id"])


def _render_pathway_expander(pw: dict) -> None:
    """Render a single pathway inside its expander."""
    pid = pw["pathway_id"]
    editing = st.session_state.get(f"editing_{pid}", False)

    if editing:
        _render_edit_mode(pw)
    else:
        # -- View mode --
        has_admission = pw["admission_md"].strip()
        has_progress = pw["progress_md"].strip()

        if not has_admission and not has_progress:
            st.info("This pathway is empty. Click Edit to start writing.")
        else:
            if has_admission:
                st.markdown("#### Admission")
                st.markdown(pw["admission_md"])
            if has_progress:
                if has_admission:
                    st.markdown("---")
                st.markdown("#### Progress")
                st.markdown(pw["progress_md"])

        citations = list_pathway_citations(pid)
        _render_references_view(citations)

        st.markdown("---")
        col_edit, col_del = st.columns([0.15, 0.85])
        with col_edit:
            if st.button("\u270f\ufe0f Edit", key=f"edit_btn_{pid}"):
                st.session_state[f"editing_{pid}"] = True
                st.rerun()
        with col_del:
            if st.button("\U0001f5d1\ufe0f Delete pathway", key=f"del_btn_{pid}"):
                delete_pathway(pid)
                st.rerun()


def _render_edit_mode(pathway: dict) -> None:
    """Render the edit interface for a pathway."""
    pid = pathway["pathway_id"]
    citations = list_pathway_citations(pid)

    # ---- 1. Current references (shown first for easy glance while writing) ----
    st.markdown("#### Your References")
    if citations:
        for c in citations:
            key = c["cite_key"]
            display = _citation_display(c["item_type"], c["item_id"])
            col_ref, col_btn = st.columns([0.9, 0.1])
            with col_ref:
                st.markdown(f"**[{key}]** {display}")
            with col_btn:
                if st.button("\u274c", key=f"rm_cite_{pid}_{key}"):
                    remove_pathway_citation(pid, int(key))
                    st.rerun()
    else:
        st.caption("No references yet. Add some below.")

    # ---- 2. Add reference ----
    st.markdown("#### Add Reference")
    search_q = st.text_input(
        "Search your abstracts & guidelines",
        placeholder="e.g. furosemide, heart failure, ACC ...",
        key=f"cite_search_{pid}",
    )
    if search_q and search_q.strip():
        abs_results = search_records(10, search_q)
        gd_results = search_guidelines(10, search_q)
        if not abs_results and not gd_results:
            st.info("No results found.")
        for r in abs_results:
            title = r.get("title") or "Untitled"
            year = r.get("year") or ""
            pmid = r.get("pmid") or ""
            label = f'{title} ({year})' if year else title
            col_t, col_a = st.columns([0.85, 0.15])
            with col_t:
                st.caption(f"Abstract \u2014 {label}")
            with col_a:
                if st.button("\u2795 Add", key=f"add_abs_{pid}_{pmid}"):
                    add_pathway_citation(pid, "abstract", pmid)
                    st.rerun()
        for r in gd_results:
            title = r.get("title") or "Untitled"
            year = r.get("year") or ""
            gid = r.get("guideline_id") or ""
            label = f'{title} ({year})' if year else title
            col_t, col_a = st.columns([0.85, 0.15])
            with col_t:
                st.caption(f"Guideline \u2014 {label}")
            with col_a:
                if st.button("\u2795 Add", key=f"add_gd_{pid}_{gid}"):
                    add_pathway_citation(pid, "guideline", gid)
                    st.rerun()

    st.markdown("---")

    # ---- 3. Two content text areas ----
    st.caption("Write in Markdown. Use [1], [2], etc. to cite your references above.")

    st.markdown("#### Admission")
    new_admission = st.text_area(
        "Admission content",
        value=pathway["admission_md"],
        height=400,
        key=f"edit_admission_{pid}",
        label_visibility="collapsed",
    )

    st.markdown("#### Progress")
    new_progress = st.text_area(
        "Progress content",
        value=pathway["progress_md"],
        height=400,
        key=f"edit_progress_{pid}",
        label_visibility="collapsed",
    )

    col_save, col_done = st.columns(2)
    with col_save:
        if st.button("\U0001f4be Save", key=f"save_{pid}"):
            update_pathway_content(pid, new_admission, new_progress)
            st.success("Saved!")
            st.rerun()
    with col_done:
        if st.button("Done editing", key=f"done_{pid}"):
            update_pathway_content(pid, new_admission, new_progress)
            st.session_state[f"editing_{pid}"] = False
            st.rerun()


# ---- main render ----

def render() -> None:
    st.title("\U0001f4cb Personalized Pathways")
    st.caption("Write your own clinical pathways and cite sources from your repository.")

    pathways = list_pathways()

    # -- Each pathway as an expander --
    for p in pathways:
        pw = get_pathway(p["pathway_id"])
        if not pw:
            continue
        with st.expander(pw["name"], expanded=False):
            _render_pathway_expander(pw)

    # -- Create new pathway --
    st.markdown("---")
    new_name = st.text_input("New pathway name", placeholder="e.g. Acute Decompensated Heart Failure")
    if st.button("Create") and new_name and new_name.strip():
        create_pathway(new_name.strip())
        st.rerun()
