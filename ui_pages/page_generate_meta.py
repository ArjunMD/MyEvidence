from typing import Dict, List

import pandas as pd
import streamlit as st

from db import (
    add_items_to_folder,
    create_or_get_folder,
    delete_folder,
    get_folder_item_ids,
    get_guideline_meta,
    get_record,
    list_folders,
    list_guidelines,
    list_recent_records,
    remove_items_from_folder,
    rename_folder,
    search_guidelines,
    search_records,
)
from pages_shared import (
    FOLDERS_MAX_LIST,
    GUIDELINES_MAX_LIST,
    META_MAX_STUDIES_HARD_CAP,
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


def _folder_label(folder_by_id: Dict[str, Dict[str, str]], folder_id: str) -> str:
    row = folder_by_id.get(folder_id) or {}
    name = (row.get("name") or "").strip() or folder_id
    count = (row.get("item_count") or "0").strip() or "0"
    return f"{name} ({count} items)"


def _source_label(in_folder: bool, in_manual: bool) -> str:
    if in_folder and in_manual:
        return "Folder + manual"
    if in_folder:
        return "Folder"
    return "Manual"


def _abstract_option_label(row: Dict[str, str]) -> str:
    pmid = (row.get("pmid") or "").strip()
    title = (row.get("title") or "").strip() or pmid
    year = (row.get("year") or "").strip()
    journal = (row.get("journal") or "").strip()
    bits = [title]
    meta_bits: List[str] = []
    if year:
        meta_bits.append(year)
    if journal:
        meta_bits.append(journal)
    if meta_bits:
        bits.append(f"({' • '.join(meta_bits)})")
    return " ".join(bits).strip()


def _guideline_option_label(row: Dict[str, str]) -> str:
    gid = (row.get("guideline_id") or "").strip()
    name = (row.get("guideline_name") or row.get("title") or row.get("filename") or "").strip() or gid
    year = (row.get("pub_year") or row.get("year") or "").strip()
    if year:
        return f"{name} ({year})"
    return name


def render() -> None:
    st.title("🧠 Generate meta (Answer focused question)")

    if st.session_state.pop("meta_clear_selected_requested", False):
        st.session_state["meta_manual_selected_pmids"] = []
        st.session_state["meta_manual_selected_gids"] = []
        st.session_state["meta_load_folder_ids"] = []
        st.session_state.pop("meta_manual_selected_pmids_ui", None)
        st.session_state.pop("meta_manual_selected_gids_ui", None)

    if "meta_manual_selected_pmids" not in st.session_state:
        st.session_state["meta_manual_selected_pmids"] = []
    if "meta_manual_selected_gids" not in st.session_state:
        st.session_state["meta_manual_selected_gids"] = []
    if "meta_load_folder_ids" not in st.session_state:
        st.session_state["meta_load_folder_ids"] = []

    include_abstract = True
    max_allowed = int(META_MAX_STUDIES_HARD_CAP)

    st.markdown("### 1) Build evidence set")
    q = st.text_input(
        "Filter folders/abstracts/guidelines by term",
        placeholder="Type keyword. Leave blank for recent.",
        key="meta_filter_q",
    )
    q_norm = (q or "").strip().lower()

    all_folder_rows = list_folders(limit=FOLDERS_MAX_LIST)
    folder_by_id: Dict[str, Dict[str, str]] = {
        (f.get("folder_id") or "").strip(): f
        for f in all_folder_rows
        if (f.get("folder_id") or "").strip()
    }
    folder_ids = [fid for fid in folder_by_id.keys() if fid]
    folder_filtered_ids = [
        fid
        for fid in folder_ids
        if (not q_norm)
        or (q_norm in fid.lower())
        or (q_norm in (folder_by_id.get(fid, {}).get("name") or "").strip().lower())
    ]
    selected_folder_ids_existing = [
        fid
        for fid in (st.session_state.get("meta_load_folder_ids") or [])
        if str(fid or "").strip() in folder_by_id
    ]
    folder_option_ids = _dedupe_ids(selected_folder_ids_existing + folder_filtered_ids)

    folder_pmids: List[str] = []
    folder_gids: List[str] = []
    selected_load_folder_ids = st.multiselect(
        "Choose folder(s) to load",
        options=folder_option_ids,
        format_func=lambda fid: _folder_label(folder_by_id, fid),
        key="meta_load_folder_ids",
    )
    if not folder_ids:
        st.caption("No folders yet. Save some items to a folder first.")
    elif q_norm and not folder_filtered_ids:
        st.caption("No folders match the current filter.")

    if selected_load_folder_ids:
        pmids_accum: List[str] = []
        gids_accum: List[str] = []
        for fid in selected_load_folder_ids:
            loaded = get_folder_item_ids(fid)
            pmids_accum.extend(loaded.get("pmids") or [])
            gids_accum.extend(loaded.get("guideline_ids") or [])
        folder_pmids = _dedupe_ids(pmids_accum)
        folder_gids = _dedupe_ids(gids_accum)
        st.caption(
            f"Loaded from {len(selected_load_folder_ids)} folder(s): "
            f"{len(folder_pmids)} abstracts • {len(folder_gids)} guidelines"
        )

    manual_pmids = _dedupe_ids(st.session_state.get("meta_manual_selected_pmids") or [])
    manual_gids = _dedupe_ids(st.session_state.get("meta_manual_selected_gids") or [])

    abstract_candidate_limit = 250
    guideline_candidate_limit = min(500, int(GUIDELINES_MAX_LIST))
    if (q or "").strip():
        abstract_candidates = search_records(limit=int(abstract_candidate_limit), q=q)
        guideline_candidates = search_guidelines(limit=int(guideline_candidate_limit), q=q)
    else:
        abstract_candidates = list_recent_records(limit=int(abstract_candidate_limit))
        guideline_candidates = list_guidelines(limit=int(guideline_candidate_limit))

    if not abstract_candidates and not guideline_candidates:
        if folder_pmids or folder_gids:
            st.info("No manual matches for this filter. Folder sources are still included.")
        elif manual_pmids or manual_gids:
            st.info("No results for this filter. Your previous manual picks are still selected.")
        else:
            st.info("No saved abstracts or guidelines found.")

    abstract_option_ids: List[str] = list(manual_pmids)
    abstract_option_label_by_id: Dict[str, str] = {}
    for row in (abstract_candidates or []):
        pmid = (row.get("pmid") or "").strip()
        if not pmid:
            continue
        abstract_option_ids.append(pmid)
        abstract_option_label_by_id[pmid] = _abstract_option_label(row)
    abstract_option_ids = _dedupe_ids(abstract_option_ids)
    for pmid in abstract_option_ids:
        if pmid in abstract_option_label_by_id:
            continue
        rec = get_record(pmid) or {}
        title = (rec.get("title") or "").strip() or pmid
        year = (rec.get("year") or "").strip()
        abstract_option_label_by_id[pmid] = f"{title}{f' ({year})' if year else ''}"

    guideline_option_ids: List[str] = list(manual_gids)
    guideline_option_label_by_id: Dict[str, str] = {}
    for row in (guideline_candidates or []):
        gid = (row.get("guideline_id") or "").strip()
        if not gid:
            continue
        guideline_option_ids.append(gid)
        guideline_option_label_by_id[gid] = _guideline_option_label(row)
    guideline_option_ids = _dedupe_ids(guideline_option_ids)
    for gid in guideline_option_ids:
        if gid in guideline_option_label_by_id:
            continue
        meta = get_guideline_meta(gid) or {}
        title = (meta.get("guideline_name") or meta.get("filename") or "").strip() or gid
        year = (meta.get("pub_year") or "").strip()
        guideline_option_label_by_id[gid] = f"{title}{f' ({year})' if year else ''}"

    if not abstract_option_ids:
        st.caption("No abstracts in current filter.")
        manual_pmids = []
    else:
        if "meta_manual_selected_pmids_ui" not in st.session_state:
            st.session_state["meta_manual_selected_pmids_ui"] = _dedupe_ids(
                [p for p in manual_pmids if p in abstract_option_ids]
            )
        else:
            st.session_state["meta_manual_selected_pmids_ui"] = _dedupe_ids(
                [p for p in (st.session_state.get("meta_manual_selected_pmids_ui") or []) if p in abstract_option_ids]
            )
        manual_pmids = _dedupe_ids(
            st.multiselect(
                "Choose abstracts",
                options=abstract_option_ids,
                format_func=lambda pmid: abstract_option_label_by_id.get(pmid, pmid),
                key="meta_manual_selected_pmids_ui",
            )
        )

    if not guideline_option_ids:
        st.caption("No guidelines in current filter.")
        manual_gids = []
    else:
        if "meta_manual_selected_gids_ui" not in st.session_state:
            st.session_state["meta_manual_selected_gids_ui"] = _dedupe_ids(
                [g for g in manual_gids if g in guideline_option_ids]
            )
        else:
            st.session_state["meta_manual_selected_gids_ui"] = _dedupe_ids(
                [g for g in (st.session_state.get("meta_manual_selected_gids_ui") or []) if g in guideline_option_ids]
            )
        manual_gids = _dedupe_ids(
            st.multiselect(
                "Choose guidelines",
                options=guideline_option_ids,
                format_func=lambda gid: guideline_option_label_by_id.get(gid, gid),
                key="meta_manual_selected_gids_ui",
            )
        )

    manual_pmids = _dedupe_ids(manual_pmids)
    manual_gids = _dedupe_ids(manual_gids)
    st.session_state["meta_manual_selected_pmids"] = manual_pmids
    st.session_state["meta_manual_selected_gids"] = manual_gids

    active_manual_pmids = manual_pmids
    active_manual_gids = manual_gids
    active_folder_pmids = folder_pmids
    active_folder_gids = folder_gids

    picked_pmids = _dedupe_ids(active_folder_pmids + active_manual_pmids)
    picked_gids = _dedupe_ids(active_folder_gids + active_manual_gids)
    total_picks = len(picked_pmids) + len(picked_gids)
    if total_picks > max_allowed:
        st.warning(f"You picked {total_picks} sources; only the first {max_allowed} will be used.")
        combo = [("paper", p) for p in picked_pmids] + [("guideline", g) for g in picked_gids]
        combo = combo[:max_allowed]
        picked_pmids = [item_id for t, item_id in combo if t == "paper"]
        picked_gids = [item_id for t, item_id in combo if t == "guideline"]

    st.divider()
    c_sel_l, c_sel_r = st.columns([5, 1], gap="small")
    with c_sel_l:
        st.markdown("### 2) Review selection")
    with c_sel_r:
        if st.button("Clear all", key="meta_clear_selected_btn", width='stretch'):
            st.session_state["meta_clear_selected_requested"] = True
            st.rerun()

    kept_pmids: List[str] = _dedupe_ids(picked_pmids)
    kept_gids: List[str] = _dedupe_ids(picked_gids)
    if not picked_pmids and not picked_gids:
        st.info("No sources selected yet.")
    else:
        folder_pmid_set = set(active_folder_pmids)
        manual_pmid_set = set(active_manual_pmids)
        folder_gid_set = set(active_folder_gids)
        manual_gid_set = set(active_manual_gids)

        review_rows: List[Dict[str, str]] = []

        for pmid in picked_pmids:
            rec = get_record(pmid) or {}
            title = (rec.get("title") or "").strip() or pmid
            year = (rec.get("year") or "").strip()
            source = _source_label(pmid in folder_pmid_set, pmid in manual_pmid_set)
            review_rows.append(
                {
                    "Type": "Abstract",
                    "Source": source,
                    "Title": title,
                    "Year": year,
                    "ID": pmid,
                }
            )

        for gid in picked_gids:
            meta = get_guideline_meta(gid) or {}
            title = (meta.get("guideline_name") or meta.get("filename") or "").strip() or gid
            year = (meta.get("pub_year") or "").strip()
            source = _source_label(gid in folder_gid_set, gid in manual_gid_set)
            review_rows.append(
                {
                    "Type": "Guideline",
                    "Source": source,
                    "Title": title,
                    "Year": year,
                    "ID": gid,
                }
            )

        review_df = pd.DataFrame(review_rows)
        st.dataframe(review_df, hide_index=True, width='stretch')
    st.divider()
    st.markdown("### 3) Save/manage folders (optional)")
    tab_save, tab_manage = st.tabs(["Save current selection", "Manage existing folder"])

    with tab_save:
        if not kept_pmids and not kept_gids:
            st.info("Select at least one source in Step 1 before saving to a folder.")
        else:
            save_folder_rows = list_folders(limit=FOLDERS_MAX_LIST)
            save_folder_by_id: Dict[str, Dict[str, str]] = {
                (f.get("folder_id") or "").strip(): f
                for f in save_folder_rows
                if (f.get("folder_id") or "").strip()
            }
            save_folder_ids = [fid for fid in save_folder_by_id.keys() if fid]

            folder_mode = st.radio(
                "Folder destination",
                options=["Existing folder", "New folder"],
                horizontal=True,
                key="meta_folder_mode",
            )

            selected_folder_id = ""
            if folder_mode == "Existing folder":
                if not save_folder_ids:
                    st.info("No folders yet. Choose `New folder` to create one.")
                else:
                    selected_folder_id = st.selectbox(
                        "Choose folder",
                        options=save_folder_ids,
                        format_func=lambda fid: _folder_label(save_folder_by_id, fid),
                        key="meta_folder_existing",
                    )
            else:
                st.text_input(
                    "New folder name",
                    key="meta_folder_new_name",
                    placeholder="e.g., Atrial fibrillation updates",
                )

            if st.button(
                "Add current selection to folder",
                key="meta_add_selected_to_folder_btn",
                width='stretch',
            ):
                try:
                    target_folder_id = ""
                    target_folder_name = ""
                    was_created = False

                    if folder_mode == "Existing folder":
                        target_folder_id = (selected_folder_id or "").strip()
                        if not target_folder_id:
                            raise ValueError("Choose an existing folder first.")
                        target_folder_name = (
                            save_folder_by_id.get(target_folder_id, {}).get("name") or ""
                        ).strip()
                    else:
                        new_folder_name = (st.session_state.get("meta_folder_new_name") or "").strip()
                        if not new_folder_name:
                            raise ValueError("Enter a folder name.")
                        created = create_or_get_folder(new_folder_name)
                        target_folder_id = (created.get("folder_id") or "").strip()
                        target_folder_name = (created.get("name") or "").strip()
                        was_created = (created.get("created") or "0") == "1"

                    stats = add_items_to_folder(
                        folder_id=target_folder_id,
                        pmids=kept_pmids,
                        guideline_ids=kept_gids,
                    )
                    abstracts_added = int(stats.get("papers_added") or "0")
                    guidelines_added = int(stats.get("guidelines_added") or "0")
                    total_added = int(stats.get("total_added") or "0")
                    if total_added > 0:
                        if was_created:
                            st.success(f"Created `{target_folder_name}` and added {total_added} item(s).")
                        else:
                            st.success(f"Added {total_added} item(s) to `{target_folder_name}`.")
                    else:
                        st.info("No new items were added (they may already be in that folder).")
                    st.caption(f"Abstracts added: {abstracts_added} • Guidelines added: {guidelines_added}")
                except Exception as e:
                    st.error(f"Folder update failed: {e}")

    with tab_manage:
        manage_folder_rows = list_folders(limit=FOLDERS_MAX_LIST)
        manage_folder_by_id: Dict[str, Dict[str, str]] = {
            (f.get("folder_id") or "").strip(): f
            for f in manage_folder_rows
            if (f.get("folder_id") or "").strip()
        }
        manage_folder_ids = [fid for fid in manage_folder_by_id.keys() if fid]

        if not manage_folder_ids:
            st.info("No folders to manage yet.")
        else:
            selected_manage_folder_id = st.selectbox(
                "Folder",
                options=manage_folder_ids,
                format_func=lambda fid: _folder_label(manage_folder_by_id, fid),
                key="meta_folder_manage_selected",
            )
            selected_manage_name = (
                manage_folder_by_id.get(selected_manage_folder_id, {}).get("name") or ""
            ).strip()

            folder_items = get_folder_item_ids(selected_manage_folder_id)
            folder_item_pmids = _dedupe_ids(folder_items.get("pmids") or [])
            folder_item_gids = _dedupe_ids(folder_items.get("guideline_ids") or [])

            if st.session_state.get("meta_folder_remove_context") != selected_manage_folder_id:
                st.session_state["meta_folder_remove_context"] = selected_manage_folder_id
                st.session_state["meta_folder_remove_items"] = []

            option_label_by_token: Dict[str, str] = {}
            remove_option_tokens: List[str] = []
            for pmid in folder_item_pmids:
                rec = get_record(pmid) or {}
                title = (rec.get("title") or "").strip() or pmid
                year = (rec.get("year") or "").strip()
                token = f"abstract::{pmid}"
                remove_option_tokens.append(token)
                option_label_by_token[token] = f"[Abstract] {title}{f' ({year})' if year else ''} — {pmid}"

            for gid in folder_item_gids:
                meta = get_guideline_meta(gid) or {}
                title = (meta.get("guideline_name") or meta.get("filename") or "").strip() or gid
                year = (meta.get("pub_year") or "").strip()
                token = f"guideline::{gid}"
                remove_option_tokens.append(token)
                option_label_by_token[token] = f"[Guideline] {title}{f' ({year})' if year else ''} — {gid}"

            remove_option_tokens = _dedupe_ids(remove_option_tokens)
            remove_option_set = set(remove_option_tokens)
            if "meta_folder_remove_items" not in st.session_state:
                st.session_state["meta_folder_remove_items"] = []
            else:
                st.session_state["meta_folder_remove_items"] = _dedupe_ids(
                    [tok for tok in (st.session_state.get("meta_folder_remove_items") or []) if tok in remove_option_set]
                )

            st.multiselect(
                "Remove items",
                options=remove_option_tokens,
                format_func=lambda tok: option_label_by_token.get(tok, tok),
                key="meta_folder_remove_items",
            )

            remove_pmids: List[str] = []
            remove_gids: List[str] = []
            for tok in _dedupe_ids(st.session_state.get("meta_folder_remove_items") or []):
                if tok.startswith("abstract::"):
                    item_id = tok.replace("abstract::", "", 1).strip()
                    if item_id:
                        remove_pmids.append(item_id)
                elif tok.startswith("guideline::"):
                    item_id = tok.replace("guideline::", "", 1).strip()
                    if item_id:
                        remove_gids.append(item_id)

            remove_disabled = not (remove_pmids or remove_gids)
            if st.button(
                "Remove selected items from folder",
                key="meta_folder_remove_selected_items_btn",
                width='stretch',
                disabled=remove_disabled,
            ):
                try:
                    stats = remove_items_from_folder(
                        folder_id=selected_manage_folder_id,
                        pmids=remove_pmids,
                        guideline_ids=remove_gids,
                    )
                    abstracts_removed = int(stats.get("papers_removed") or "0")
                    guidelines_removed = int(stats.get("guidelines_removed") or "0")
                    total_removed = int(stats.get("total_removed") or "0")
                    if total_removed > 0:
                        st.success(
                            f"Removed {total_removed} item(s) from "
                            f"`{selected_manage_name or selected_manage_folder_id}`."
                        )
                    else:
                        st.info("No matching items were removed.")
                    st.caption(
                        f"Abstracts removed: {abstracts_removed} • Guidelines removed: {guidelines_removed}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Remove failed: {e}")

            st.text_input(
                "Rename",
                key="meta_folder_manage_new_name",
                placeholder=selected_manage_name or "New folder name",
            )

            if st.button("Rename folder", key="meta_folder_rename_btn", width='stretch'):
                try:
                    new_name = (st.session_state.get("meta_folder_manage_new_name") or "").strip()
                    if not new_name:
                        raise ValueError("Enter a new folder name first.")
                    renamed = rename_folder(selected_manage_folder_id, new_name)
                    st.success(f"Renamed folder to `{(renamed.get('name') or '').strip()}`.")
                except Exception as e:
                    st.error(f"Rename failed: {e}")

            confirm_delete = st.checkbox(
                f"Confirm delete `{selected_manage_name or selected_manage_folder_id}`",
                key=f"meta_confirm_delete_folder_{selected_manage_folder_id}",
            )
            if st.button(
                "Delete folder",
                key="meta_folder_delete_btn",
                width='stretch',
                disabled=not confirm_delete,
            ):
                try:
                    deleted = delete_folder(selected_manage_folder_id)
                    st.session_state["meta_load_folder_ids"] = [
                        fid
                        for fid in (st.session_state.get("meta_load_folder_ids") or [])
                        if str(fid or "").strip() != selected_manage_folder_id
                    ]
                    st.success(f"Deleted folder `{(deleted.get('name') or '').strip()}`.")
                except Exception as e:
                    st.error(f"Delete failed: {e}")

    st.divider()
    st.markdown("### 4) Ask focused question")
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
        width='stretch',
        disabled=not can_generate,
    ):
        if not (prompt_text or "").strip():
            st.error("Enter a focused question.")
        elif not can_generate:
            st.error("Pick at least one source first.")
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
