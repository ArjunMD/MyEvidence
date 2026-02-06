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
    list_guidelines,
    list_recent_records,
    search_guidelines,
    search_records,
)
from pages_shared import (
    FOLDERS_MAX_LIST,
    GUIDELINES_MAX_LIST,
    META_MAX_STUDIES_HARD_CAP,
    gpt_generate_meta_combined,
)


def render() -> None:
    st.title("🧠 Generate meta (Answer focused question)")
    st.caption("Select multiple saved studies and/or guidelines and generate a single-paragraph output.")

    include_abstract = True
    left = st.container()

    with left:
        if st.session_state.pop("meta_clear_selected_requested", False):
            st.session_state["meta_manual_selected_pmids"] = []
            st.session_state["meta_manual_selected_gids"] = []
            st.session_state["meta_load_folder_ids"] = []
            st.session_state.pop("meta_pick_paper_table", None)
            st.session_state.pop("meta_pick_guideline_table", None)
            for k in list(st.session_state.keys()):
                if k.startswith("meta_keep_selected_pmid_") or k.startswith("meta_keep_selected_gid_"):
                    st.session_state.pop(k, None)

        folder_pmids: List[str] = []
        folder_gids: List[str] = []
        if "meta_manual_selected_pmids" not in st.session_state:
            st.session_state["meta_manual_selected_pmids"] = []
        if "meta_manual_selected_gids" not in st.session_state:
            st.session_state["meta_manual_selected_gids"] = []

        manual_pmids = [
            str(p).strip()
            for p in (st.session_state.get("meta_manual_selected_pmids") or [])
            if str(p).strip()
        ]
        manual_gids = [
            str(g).strip()
            for g in (st.session_state.get("meta_manual_selected_gids") or [])
            if str(g).strip()
        ]

        load_folder_rows = list_folders(limit=FOLDERS_MAX_LIST)
        load_folder_by_id: Dict[str, Dict[str, str]] = {
            (f.get("folder_id") or "").strip(): f
            for f in load_folder_rows
            if (f.get("folder_id") or "").strip()
        }
        load_folder_ids = [fid for fid in load_folder_by_id.keys() if fid]

        selected_load_folder_ids = st.multiselect(
            "Choose folder(s) to load",
            options=load_folder_ids,
            format_func=lambda fid: (
                f"{(load_folder_by_id[fid].get('name') or '').strip()} "
                f"({load_folder_by_id[fid].get('item_count') or '0'} items)"
            ),
            key="meta_load_folder_ids",
        )

        if not load_folder_ids:
            st.caption("No folders yet. Save some items to a folder first.")
        elif selected_load_folder_ids:
            pmids_accum: List[str] = []
            gids_accum: List[str] = []
            for fid in selected_load_folder_ids:
                loaded = get_folder_item_ids(fid)
                pmids_accum.extend(loaded.get("pmids") or [])
                gids_accum.extend(loaded.get("guideline_ids") or [])

            folder_pmids = list(dict.fromkeys(pmids_accum))
            folder_gids = list(dict.fromkeys(gids_accum))
            st.caption(
                f"Loaded from {len(selected_load_folder_ids)} folder(s): "
                f"{len(folder_pmids)} papers • {len(folder_gids)} guidelines"
            )
        else:
            st.caption("No folders selected.")

        q = st.text_input(
            "Filter papers/guidelines",
            placeholder="Type to filter your DB (title/abstract/tags/etc). Leave blank to show recent.",
            key="meta_filter_q",
        )

        candidate_limit = 250
        if (q or "").strip():
            paper_candidates = search_records(limit=int(candidate_limit), q=q)
            guideline_candidates = search_guidelines(limit=GUIDELINES_MAX_LIST, q=q)
        else:
            paper_candidates = list_recent_records(limit=int(candidate_limit))
            guideline_candidates = list_guidelines(limit=GUIDELINES_MAX_LIST)

        if not paper_candidates and not guideline_candidates:
            if folder_pmids or folder_gids:
                st.info("No manual matches for this filter. Folder sources are still included.")
            elif manual_pmids or manual_gids:
                st.info("No results for this filter. Your previously selected manual items are still selected.")
            else:
                st.info("No saved papers or guidelines found.")
        else:
            folder_pmid_set = set(folder_pmids)
            folder_gid_set = set(folder_gids)
            manual_pmid_set = set(manual_pmids)
            manual_gid_set = set(manual_gids)

            if paper_candidates:
                st.markdown("##### Papers")
                st.caption("`Pick` = include manually for this run. `From folder` = already included via folder selection.")
                pdf = pd.DataFrame(paper_candidates)
                if "pmid" in pdf.columns:
                    paper_ids = [str(p).strip() for p in pdf["pmid"].tolist()]
                else:
                    paper_ids = []
                pdf.insert(0, "Pick", [p in manual_pmid_set for p in paper_ids] if paper_ids else False)
                if "pmid" in pdf.columns:
                    pdf.insert(1, "From folder", [p in folder_pmid_set for p in paper_ids])
                if "specialty" in pdf.columns:
                    pdf = pdf.drop(columns=["specialty"])
                p_edited = st.data_editor(
                    pdf,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Pick": st.column_config.CheckboxColumn("Pick", help="Select for synthesis"),
                        "From folder": st.column_config.CheckboxColumn("From folder"),
                        "pmid": st.column_config.TextColumn("PMID", width="small"),
                        "year": st.column_config.TextColumn("Year", width="small"),
                        "patient_n": st.column_config.TextColumn("N", width="small"),
                        "title": st.column_config.TextColumn("Title", width="large"),
                        "journal": st.column_config.TextColumn("Journal", width="medium"),
                        "study_design": st.column_config.TextColumn("Design tags", width="medium"),
                    },
                    disabled=[
                        "From folder",
                        "pmid",
                        "year",
                        "patient_n",
                        "title",
                        "journal",
                        "study_design",
                    ],
                    key="meta_pick_paper_table",
                )

                if "pmid" in p_edited.columns:
                    visible_pmids: List[str] = []
                    visible_picked_pmids: List[str] = []
                    for _, row in p_edited.iterrows():
                        pmid = str(row.get("pmid") or "").strip()
                        if not pmid:
                            continue
                        visible_pmids.append(pmid)
                        if bool(row.get("Pick")):
                            visible_picked_pmids.append(pmid)

                    visible_set = set(visible_pmids)
                    manual_pmids = [p for p in manual_pmids if p not in visible_set]
                    for pmid in visible_picked_pmids:
                        if pmid not in manual_pmids:
                            manual_pmids.append(pmid)

            if guideline_candidates:
                st.markdown("##### Guidelines")
                gdf_rows = []
                for g in guideline_candidates:
                    gid = (g.get("guideline_id") or "").strip()
                    name = (g.get("guideline_name") or g.get("title") or g.get("filename") or "").strip()
                    year = (g.get("pub_year") or g.get("year") or "").strip()
                    gdf_rows.append(
                        {
                            "guideline_id": gid,
                            "Pick": gid in manual_gid_set,
                            "From folder": gid in folder_gid_set,
                            "title": name,
                            "year": year,
                        }
                    )
                gdf = pd.DataFrame(gdf_rows)
                if "guideline_id" in gdf.columns:
                    gdf = gdf.set_index("guideline_id")
                g_edited = st.data_editor(
                    gdf,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Pick": st.column_config.CheckboxColumn("Pick", help="Select for synthesis"),
                        "From folder": st.column_config.CheckboxColumn("From folder"),
                        "title": st.column_config.TextColumn("Title", width="large"),
                        "year": st.column_config.TextColumn("Year", width="small"),
                    },
                    disabled=["From folder", "title", "year"],
                    key="meta_pick_guideline_table",
                )

                visible_gids: List[str] = []
                visible_picked_gids: List[str] = []
                for gid, row in g_edited.iterrows():
                    gid_s = str(gid or "").strip()
                    if not gid_s:
                        continue
                    visible_gids.append(gid_s)
                    if bool(row.get("Pick")):
                        visible_picked_gids.append(gid_s)

                visible_gid_set = set(visible_gids)
                manual_gids = [g for g in manual_gids if g not in visible_gid_set]
                for gid in visible_picked_gids:
                    if gid not in manual_gids:
                        manual_gids.append(gid)

        st.session_state["meta_manual_selected_pmids"] = manual_pmids
        st.session_state["meta_manual_selected_gids"] = manual_gids

        picked_pmids = list(dict.fromkeys(folder_pmids + manual_pmids))
        picked_gids = list(dict.fromkeys(folder_gids + manual_gids))

        if not picked_pmids and not picked_gids:
            st.info("Pick at least one paper or guideline.")
            st.stop()

        total_picks = len(picked_pmids) + len(picked_gids)
        max_allowed = int(META_MAX_STUDIES_HARD_CAP)
        if total_picks > max_allowed:
            st.warning(f"You picked {total_picks} sources; only the first {max_allowed} will be used.")
            combo = [("paper", p) for p in picked_pmids] + [("guideline", g) for g in picked_gids]
            combo = combo[:max_allowed]
            picked_pmids = [item_id for t, item_id in combo if t == "paper"]
            picked_gids = [item_id for t, item_id in combo if t == "guideline"]

        c_sel_l, c_sel_r = st.columns([5, 1], gap="small")
        with c_sel_l:
            st.markdown("#### Selected")
        with c_sel_r:
            if st.button("Clear selected", key="meta_clear_selected_btn", use_container_width=True):
                st.session_state["meta_clear_selected_requested"] = True
                st.rerun()

        st.caption("Uncheck any item to remove it from this run.")

        kept_pmids: List[str] = []
        kept_gids: List[str] = []

        for p in picked_pmids:
            r = get_record(p)
            title = (r.get("title") or "").strip() if r else ""
            c_info, c_keep = st.columns([7, 1], gap="small")
            with c_info:
                st.markdown(f"- [{title or p}](https://pubmed.ncbi.nlm.nih.gov/{p}/) — `{p}`")
            with c_keep:
                keep = st.checkbox("Use", value=True, key=f"meta_keep_selected_pmid_{p}")
            if keep:
                kept_pmids.append(p)

        for gid in picked_gids:
            meta = get_guideline_meta(gid) or {}
            name = (meta.get("guideline_name") or meta.get("filename") or "").strip()
            c_info, c_keep = st.columns([7, 1], gap="small")
            with c_info:
                st.markdown(f"- [Guideline] {name or gid} — `{gid}`")
            with c_keep:
                keep = st.checkbox("Use", value=True, key=f"meta_keep_selected_gid_{gid}")
            if keep:
                kept_gids.append(gid)

        picked_pmids = kept_pmids
        picked_gids = kept_gids

        if not picked_pmids and not picked_gids:
            st.info("All selected items are unchecked. Check at least one to continue.")
            st.stop()

        st.markdown("##### Folders")
        folder_toggle = st.toggle(
            "Add selected items to a folder",
            value=False,
            key="meta_folder_toggle",
        )

        if folder_toggle:
            folder_rows = list_folders(limit=FOLDERS_MAX_LIST)
            folder_mode = st.radio(
                "Folder destination",
                options=["Existing folder", "New folder"],
                horizontal=True,
                key="meta_folder_mode",
            )

            selected_folder_id = ""
            if folder_mode == "Existing folder":
                folder_by_id: Dict[str, Dict[str, str]] = {
                    (f.get("folder_id") or "").strip(): f
                    for f in folder_rows
                    if (f.get("folder_id") or "").strip()
                }
                folder_ids = [fid for fid in folder_by_id.keys() if fid]
                if not folder_ids:
                    st.info("No folders yet. Choose `New folder` to create one.")
                else:
                    selected_folder_id = st.selectbox(
                        "Choose folder",
                        options=folder_ids,
                        format_func=lambda fid: (
                            f"{(folder_by_id[fid].get('name') or '').strip()} "
                            f"({folder_by_id[fid].get('item_count') or '0'} items)"
                        ),
                        key="meta_folder_existing",
                    )
            else:
                st.text_input(
                    "New folder name",
                    key="meta_folder_new_name",
                    placeholder="e.g., Atrial fibrillation updates",
                )

            if st.button(
                "Add selected to folder",
                key="meta_add_selected_to_folder_btn",
                use_container_width=True,
            ):
                try:
                    target_folder_id = ""
                    target_folder_name = ""
                    was_created = False

                    if folder_mode == "Existing folder":
                        target_folder_id = (selected_folder_id or "").strip()
                        if not target_folder_id:
                            raise ValueError("Choose an existing folder first.")

                        for f in folder_rows:
                            if (f.get("folder_id") or "").strip() == target_folder_id:
                                target_folder_name = (f.get("name") or "").strip()
                                break
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
                        pmids=picked_pmids,
                        guideline_ids=picked_gids,
                    )
                    papers_added = int(stats.get("papers_added") or "0")
                    guidelines_added = int(stats.get("guidelines_added") or "0")
                    total_added = int(stats.get("total_added") or "0")

                    if total_added > 0:
                        if was_created:
                            st.success(f"Created `{target_folder_name}` and added {total_added} item(s).")
                        else:
                            st.success(f"Added {total_added} item(s) to `{target_folder_name}`.")
                    else:
                        st.info("No new items were added (they may already be in that folder).")
                    st.caption(f"Papers added: {papers_added} • Guidelines added: {guidelines_added}")
                except Exception as e:
                    st.error(f"Folder update failed: {e}")

        st.divider()
        prompt_text = st.text_input(
            "Focused question",
            placeholder="e.g., Does X improve Y in Z population?",
            key="meta_focused_question",
        )

        if st.button("Answer focused question", type="primary", key="meta_generate_btn", use_container_width=True):
            if not (prompt_text or "").strip():
                st.error("Enter a focused question.")
            else:
                with st.spinner("Generating…"):
                    try:
                        out = gpt_generate_meta_combined(
                            pmids=picked_pmids,
                            guideline_ids=picked_gids,
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
        st.subheader("Output")
        st.write(out)
