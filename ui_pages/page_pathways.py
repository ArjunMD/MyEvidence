import re

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


# ---- evidence scoring ----

_EVIDENCE_TIERS: list[tuple[list[str], int, str]] = [
    # (keywords_any, score, label)  — first match wins
    (["systematic review", "meta-analysis"],            15, "SR/MA"),
    (["randomized"],                                    25, "RCT"),
    (["cohort"],                                        40, "Cohort"),
    (["observational"],                                 45, "Observational"),
    (["case-control", "case control"],                  50, "Case-control"),
    (["cross-sectional", "cross sectional"],            55, "Cross-sectional"),
    (["case series", "case report"],                    60, "Case series"),
    (["expert opinion", "narrative review", "editorial"], 70, "Expert opinion"),
]


def _evidence_score(item_type: str, item_id: str) -> tuple[int, str]:
    """Return (score, label).  Lower score = stronger evidence."""
    if item_type == "guideline":
        return (10, "Guideline")

    rec = get_record(item_id)
    if not rec:
        return (80, "Other")

    design = (rec.get("study_design") or "").lower()
    tags = [t.strip() for t in design.split(",")]

    for keywords, score, label in _EVIDENCE_TIERS:
        if any(kw in tag for kw in keywords for tag in tags):
            # Refine RCT score by blinding
            if label == "RCT" and any("double-blind" in t or "double blind" in t for t in tags):
                return (20, "RCT (double-blind)")
            return (score, label)

    return (80, "Other")


def _tiebreaker_keys(item_type: str, item_id: str) -> tuple[int, int, int]:
    """Return (year, patient_n, is_multicenter) for breaking ties among same-score citations.

    Guidelines: newest publication year first (year descending).
    Abstracts:  larger patient N first, then multicenter > single-center.
    """
    if item_type == "guideline":
        meta = get_guideline_meta(item_id)
        raw_year = (meta.get("pub_year") or "").strip() if meta else ""
        year = int(raw_year) if raw_year.isdigit() else 0
        return (year, 0, 0)

    rec = get_record(item_id)
    if not rec:
        return (0, 0, 0)

    # patient_n — extract the first integer from the free-text field
    raw_n = (rec.get("patient_n") or "").strip()
    patient_n = 0
    if raw_n:
        nums = re.findall(r"\d[\d,]*", raw_n)
        if nums:
            patient_n = int(nums[0].replace(",", ""))

    # multicenter — check study_design tags
    design = (rec.get("study_design") or "").lower()
    is_multi = 1 if any(
        kw in design
        for kw in ("multicenter", "multi-center", "multicentre", "multi-centre")
    ) else 0

    return (year, patient_n, is_multi)


def _sort_citations_by_evidence(citations: list[dict]) -> list[dict]:
    """Sort citations by evidence score (strongest first) and attach display_num + evidence_label.

    Tiebreakers for same evidence score:
      - Guidelines: newest publication year first
      - Abstracts:  larger patient N first, then multicenter > single-center
    """
    scored = []
    for c in citations:
        score, label = _evidence_score(c["item_type"], c["item_id"])
        year, patient_n, is_multi = _tiebreaker_keys(c["item_type"], c["item_id"])
        scored.append({**c, "_score": score, "evidence_label": label,
                       "_year": year, "_patient_n": patient_n, "_multicenter": is_multi})
    scored.sort(key=lambda x: (x["_score"], -x["_year"], -x["_patient_n"], -x["_multicenter"]))
    for i, c in enumerate(scored, start=1):
        c["display_num"] = i
    return scored


# ---- citation token resolution ----

_CITE_TOKEN_RE = re.compile(r"\[@(?:g:)?([A-Za-z0-9_-]+)\]")


def _build_cite_map(sorted_citations: list[dict]) -> dict[str, int]:
    """Build item_id -> display_num mapping from evidence-sorted citations."""
    m: dict[str, int] = {}
    for c in sorted_citations:
        m[c["item_id"]] = c["display_num"]
    return m


def _cite_tag(item_type: str, item_id: str) -> str:
    """Return the token the user types in their text."""
    if item_type == "guideline":
        return f"[@g:{item_id}]"
    return f"[@{item_id}]"


def _resolve_cite_tokens(text: str, cite_map: dict[str, int]) -> str:
    """Replace [@PMID] and [@g:GID] tokens with [N] for display."""
    def _replace(m: re.Match) -> str:
        item_id = m.group(1)
        num = cite_map.get(item_id)
        if num is not None:
            return f"[{num}]"
        return m.group(0)  # leave unresolved tokens as-is
    return _CITE_TOKEN_RE.sub(_replace, text)


# ---- display helpers ----

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


# ---- rendering ----

def _render_references_view(sorted_citations: list[dict]) -> None:
    """Render the numbered reference list in view mode (already evidence-sorted)."""
    if not sorted_citations:
        return
    st.markdown("---")
    st.markdown("#### References")
    for c in sorted_citations:
        num = c["display_num"]
        elabel = c.get("evidence_label") or ""
        display = _citation_display(c["item_type"], c["item_id"])
        col_text, col_icon = st.columns([0.93, 0.07])
        with col_text:
            st.markdown(f"**[{num}]** ({elabel}) {display}")
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
        # -- Build evidence-sorted citations + cite map --
        raw_citations = list_pathway_citations(pid)
        sorted_cites = _sort_citations_by_evidence(raw_citations)
        cite_map = _build_cite_map(sorted_cites)

        # -- View mode --
        has_admission = pw["admission_md"].strip()
        has_progress = pw["progress_md"].strip()

        if not has_admission and not has_progress:
            st.info("This pathway is empty. Click Edit to start writing.")
        else:
            if has_admission:
                st.markdown("#### Admission")
                st.markdown(_resolve_cite_tokens(pw["admission_md"], cite_map))
            if has_progress:
                if has_admission:
                    st.markdown("---")
                st.markdown("#### Progress")
                st.markdown(_resolve_cite_tokens(pw["progress_md"], cite_map))

        _render_references_view(sorted_cites)

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
    raw_citations = list_pathway_citations(pid)
    sorted_cites = _sort_citations_by_evidence(raw_citations)

    # ---- 1. Current references sorted by evidence (shown first for easy glance) ----
    st.markdown("#### Your References")
    st.caption("Sorted by level of evidence. Use the **cite tag** in your text to reference a study.")
    if sorted_cites:
        for c in sorted_cites:
            num = c["display_num"]
            elabel = c.get("evidence_label") or ""
            display = _citation_display(c["item_type"], c["item_id"])
            tag = _cite_tag(c["item_type"], c["item_id"])
            col_ref, col_tag, col_btn = st.columns([0.6, 0.3, 0.1])
            with col_ref:
                st.markdown(f"**[{num}]** ({elabel}) {display}")
            with col_tag:
                st.code(tag, language=None)
            with col_btn:
                if st.button("\u274c", key=f"rm_cite_{pid}_{c['cite_key']}"):
                    remove_pathway_citation(pid, int(c["cite_key"]))
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
    st.caption("Write in Markdown. Paste the **cite tag** (shown above) where you want a citation.")

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
