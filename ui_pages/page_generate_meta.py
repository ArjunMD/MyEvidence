from typing import Dict, List

import pandas as pd
import streamlit as st

from db import (
    add_items_to_folder,
    create_or_get_folder,
    get_folder_item_ids,
    get_guideline_meta,
    get_record,
    list_folders,
)
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


def _folder_option_label(folder: Dict[str, str]) -> str:
    name = (folder.get("name") or "").strip() or "(unnamed folder)"
    paper_n = int(folder.get("paper_count") or "0")
    guideline_n = int(folder.get("guideline_count") or "0")
    total_n = paper_n + guideline_n
    return f"{name} ({total_n} total: {paper_n} abstracts, {guideline_n} guidelines)"

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

    flash = (st.session_state.pop("meta_folder_flash", "") or "").strip()
    if flash:
        st.toast(flash)

    cart = _get_evidence_cart_ids()
    cart_pmids = _dedupe_ids(cart.get("pmids") or [])
    cart_gids = _dedupe_ids(cart.get("guideline_ids") or [])
    folders = list_folders(limit=500)
    folder_by_id = {
        (f.get("folder_id") or "").strip(): f
        for f in folders
        if (f.get("folder_id") or "").strip()
    }
    folder_ids = list(folder_by_id.keys())

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

    st.divider()
    st.markdown("### 1) Add Folder to Evidence Cart or Evidence Cart to Folder")
    c_folder_add, c_folder_save = st.columns([1, 1], gap="large")

    with c_folder_add:
        st.markdown("**Folder → Cart**")
        if not folder_ids:
            st.caption("No folders yet.")
        else:
            selected_add_folder_id = st.selectbox(
                "Folder",
                options=folder_ids,
                key="meta_add_folder_id",
                format_func=lambda fid: _folder_option_label(folder_by_id.get(fid, {})),
            )
            if st.button("Add folder to cart", key="meta_add_folder_to_cart_btn", width="stretch"):
                selected_folder = folder_by_id.get(selected_add_folder_id, {})
                folder_name = (selected_folder.get("name") or selected_add_folder_id).strip()
                folder_items = get_folder_item_ids(selected_add_folder_id)

                folder_pmids = _dedupe_ids(folder_items.get("pmids") or [])
                folder_gids = _dedupe_ids(folder_items.get("guideline_ids") or [])
                merged_pmids = _dedupe_ids(cart_pmids + folder_pmids)
                merged_gids = _dedupe_ids(cart_gids + folder_gids)

                added_papers = len(set(merged_pmids) - set(cart_pmids))
                added_guidelines = len(set(merged_gids) - set(cart_gids))
                added_total = added_papers + added_guidelines

                if added_total > 0:
                    _set_evidence_cart_ids(pmids=merged_pmids, guideline_ids=merged_gids)
                    st.session_state["meta_folder_flash"] = (
                        f"Added {added_papers} abstracts and {added_guidelines} guidelines "
                        f"from folder `{folder_name}` to evidence cart."
                    )
                else:
                    st.session_state["meta_folder_flash"] = (
                        f"Folder `{folder_name}` did not add any new items to the cart."
                    )
                st.rerun()

    with c_folder_save:
        st.markdown("**Cart → Folder**")
        selected_existing_folder_id = ""
        if not folder_ids:
            st.caption("No existing folders yet.")
        else:
            selected_existing_folder_id = st.selectbox(
                "Existing folder (optional)",
                options=folder_ids,
                key="meta_save_existing_folder_id",
                format_func=lambda fid: _folder_option_label(folder_by_id.get(fid, {})),
            )
        new_folder_name = st.text_input(
            "New folder name (optional)",
            key="meta_new_folder_name",
            placeholder="e.g., Heart failure core evidence",
        )
        st.caption(
            "If a new folder name is entered, it will be used. "
            "Otherwise, the selected existing folder is used."
        )

        if st.button(
            "Save cart to folder",
            key="meta_save_cart_to_folder_btn",
            width="stretch",
            disabled=not bool(cart_pmids or cart_gids),
        ):
            target_folder_id = ""
            target_folder_name = ""
            folder_created = False

            if (new_folder_name or "").strip():
                created = create_or_get_folder(new_folder_name)
                target_folder_id = (created.get("folder_id") or "").strip()
                target_folder_name = (created.get("name") or "").strip()
                folder_created = (created.get("created") or "0") == "1"
                if not target_folder_id:
                    st.error("Enter a folder name.")
            elif selected_existing_folder_id:
                target_folder_id = selected_existing_folder_id
                target_folder_name = (
                    folder_by_id.get(selected_existing_folder_id, {}).get("name")
                    or selected_existing_folder_id
                ).strip()
            else:
                st.error("Pick an existing folder or enter a new folder name.")

            if target_folder_id:
                stats = add_items_to_folder(
                    folder_id=target_folder_id,
                    pmids=cart_pmids,
                    guideline_ids=cart_gids,
                )
                added_papers = int(stats.get("papers_added") or "0")
                added_guidelines = int(stats.get("guidelines_added") or "0")
                added_total = added_papers + added_guidelines

                if added_total > 0:
                    prefix = f"Created folder `{target_folder_name}`. " if folder_created else ""
                    st.session_state["meta_folder_flash"] = (
                        f"{prefix}Added {added_papers} abstracts and {added_guidelines} guidelines "
                        f"from evidence cart to folder `{target_folder_name}`."
                    )
                elif folder_created:
                    st.session_state["meta_folder_flash"] = (
                        f"Created folder `{target_folder_name}`. It already contains all cart items."
                    )
                else:
                    st.session_state["meta_folder_flash"] = (
                        f"Folder `{target_folder_name}` already contains all evidence cart items."
                    )
                st.rerun()

    clipped = _clip_to_cap(cart_pmids, cart_gids, max_allowed=max_allowed)
    kept_pmids = _dedupe_ids(clipped.get("pmids") or [])
    kept_gids = _dedupe_ids(clipped.get("guideline_ids") or [])

    st.divider()
    st.markdown("### 2) Review evidence cart")
    if not kept_pmids and not kept_gids:
        st.caption("No sources selected.")
    else:
        st.dataframe(pd.DataFrame(_review_rows(kept_pmids, kept_gids)), hide_index=True, width="stretch")

    st.divider()
    st.markdown("### 3) Ask focused question")
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
