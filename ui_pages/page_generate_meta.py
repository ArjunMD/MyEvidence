from typing import Dict, List

import pandas as pd
import streamlit as st

from db import get_guideline_meta, get_record
from pages_shared import (
    META_MAX_STUDIES_HARD_CAP,
    _get_evidence_cart_ids,
    _set_evidence_cart_ids,
    gpt_generate_meta_combined,
)


def _dedupe_ids(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in (values or []):
        v = str(raw or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _clip_to_cap(pmids: List[str], gids: List[str], max_allowed: int) -> Dict[str, List[str]]:
    picked_pmids = _dedupe_ids(pmids)
    picked_gids = _dedupe_ids(gids)
    total = len(picked_pmids) + len(picked_gids)
    if total <= int(max_allowed):
        return {"pmids": picked_pmids, "guideline_ids": picked_gids}

    st.warning(f"Evidence cart has {total} sources; only the first {int(max_allowed)} will be used.")
    combo = [("paper", p) for p in picked_pmids] + [("guideline", g) for g in picked_gids]
    combo = combo[: int(max_allowed)]
    clipped_pmids = [item_id for t, item_id in combo if t == "paper"]
    clipped_gids = [item_id for t, item_id in combo if t == "guideline"]
    return {"pmids": clipped_pmids, "guideline_ids": clipped_gids}


def _review_rows(pmids: List[str], gids: List[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    for pmid in _dedupe_ids(pmids):
        rec = get_record(pmid) or {}
        title = (rec.get("title") or "").strip() or pmid
        year = (rec.get("year") or "").strip()
        journal = (rec.get("journal") or "").strip() or "—"
        patient_n = (rec.get("patient_n") or "").strip() or "—"
        study_design = (rec.get("study_design") or "").strip() or "—"
        rows.append(
            {
                "Type": "Abstract",
                "Title": title,
                "Year": year,
                "Journal": journal,
                "Patients (N)": patient_n,
                "Study design": study_design,
            }
        )

    for gid in _dedupe_ids(gids):
        meta = get_guideline_meta(gid) or {}
        title = (meta.get("guideline_name") or meta.get("filename") or "").strip() or gid
        year = (meta.get("pub_year") or "").strip()
        rows.append(
            {
                "Type": "Guideline",
                "Title": title,
                "Year": year,
                "Journal": "—",
                "Patients (N)": "—",
                "Study design": "Guideline",
            }
        )

    return rows


def render() -> None:
    st.title("🧠 Generate meta (Answer focused question)")
    include_abstract = True
    max_allowed = int(META_MAX_STUDIES_HARD_CAP)

    cart = _get_evidence_cart_ids()
    cart_pmids = _dedupe_ids(cart.get("pmids") or [])
    cart_gids = _dedupe_ids(cart.get("guideline_ids") or [])

    c_top_l, c_top_r = st.columns([5, 1], gap="small")
    with c_top_l:
        st.caption(
            f"Evidence cart loaded: {len(cart_pmids)} abstracts • {len(cart_gids)} guidelines "
            f"({len(cart_pmids) + len(cart_gids)} total)"
        )
    with c_top_r:
        if st.button("Clear cart", key="meta_clear_cart_btn", width="stretch"):
            _set_evidence_cart_ids(pmids=[], guideline_ids=[])
            st.rerun()

    if not cart_pmids and not cart_gids:
        st.info("Evidence cart is empty. Add studies from Browse studies, then return here.")

    clipped = _clip_to_cap(cart_pmids, cart_gids, max_allowed=max_allowed)
    kept_pmids = _dedupe_ids(clipped.get("pmids") or [])
    kept_gids = _dedupe_ids(clipped.get("guideline_ids") or [])

    st.divider()
    st.markdown("### 1) Review evidence cart")
    if not kept_pmids and not kept_gids:
        st.caption("No sources selected.")
    else:
        st.dataframe(pd.DataFrame(_review_rows(kept_pmids, kept_gids)), hide_index=True, width="stretch")

    st.divider()
    st.markdown("### 2) Ask focused question")
    prompt_text = st.text_input(
        "Focused question",
        placeholder="e.g., Does X improve Y in Z population?",
        key="meta_focused_question",
    )

    can_generate = bool(kept_pmids or kept_gids)
    if st.button(
        "Answer focused question",
        type="primary",
        key="meta_generate_btn",
        width="stretch",
        disabled=not can_generate,
    ):
        if not (prompt_text or "").strip():
            st.error("Enter a focused question.")
        elif not can_generate:
            st.error("Add at least one source to the evidence cart first.")
        else:
            with st.spinner("Generating…"):
                try:
                    out = gpt_generate_meta_combined(
                        pmids=kept_pmids,
                        guideline_ids=kept_gids,
                        mode="answer",
                        prompt_text=prompt_text,
                        include_abstract=include_abstract,
                    )
                    st.session_state["meta_last_output"] = out
                except Exception as e:
                    st.error(str(e))

    out = (st.session_state.get("meta_last_output") or "").strip()
    if out:
        st.divider()
        st.subheader("Response")
        st.write(out)
