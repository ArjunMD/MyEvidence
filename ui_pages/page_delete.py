from typing import Dict, List

import streamlit as st

from db import (
    delete_folder,
    delete_guideline,
    delete_record,
    get_folder_item_ids,
    get_guideline_meta,
    get_record,
    list_folders,
    list_guidelines,
    list_recent_records,
    remove_items_from_folder,
    search_guidelines,
    search_records,
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


def _clip_text(value: str, max_len: int = 90) -> str:
    s = (value or "").strip()
    if len(s) <= int(max_len):
        return s
    return s[: max(0, int(max_len) - 1)].rstrip() + "…"


def _folder_option_label(folder: Dict[str, str]) -> str:
    name = (folder.get("name") or "").strip() or "(unnamed folder)"
    paper_n = int(folder.get("paper_count") or "0")
    guideline_n = int(folder.get("guideline_count") or "0")
    total_n = paper_n + guideline_n
    return f"{name} ({total_n} total: {paper_n} abstracts, {guideline_n} guidelines)"


def _folder_item_option_labels(pmids: List[str], gids: List[str]) -> Dict[str, str]:
    labels: Dict[str, str] = {}

    for pmid in _dedupe_ids(pmids):
        rec = get_record(pmid) or {}
        title = _clip_text((rec.get("title") or "").strip() or pmid)
        year = (rec.get("year") or "").strip()
        suffix = f" ({year})" if year else ""
        labels[f"paper:{pmid}"] = f"Abstract • {title}{suffix} [PMID {pmid}]"

    for gid in _dedupe_ids(gids):
        meta = get_guideline_meta(gid) or {}
        title = _clip_text((meta.get("guideline_name") or meta.get("filename") or "").strip() or gid)
        year = (meta.get("pub_year") or "").strip()
        suffix = f" ({year})" if year else ""
        labels[f"guideline:{gid}"] = f"Guideline • {title}{suffix} [ID {gid}]"

    return labels


def render() -> None:
    st.title("🗑️ Delete")
    flash = (st.session_state.pop("delete_folder_flash", "") or "").strip()
    if flash:
        st.toast(flash)

    tab_papers, tab_guidelines, tab_folders = st.tabs(["Papers", "Guidelines", "Folders"])

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
        else:
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

    with tab_folders:
        st.subheader("Manage folders")
        folders = list_folders(limit=500)
        folder_by_id = {
            (f.get("folder_id") or "").strip(): f
            for f in folders
            if (f.get("folder_id") or "").strip()
        }
        folder_ids = list(folder_by_id.keys())

        if not folder_ids:
            st.info("No folders to manage yet.")
        else:
            selected_folder_id = st.selectbox(
                "Select a folder",
                options=folder_ids,
                key="delete_manage_folder_id",
                format_func=lambda fid: _folder_option_label(folder_by_id.get(fid, {})),
            )
            selected_folder = folder_by_id.get(selected_folder_id, {})
            selected_folder_name = (selected_folder.get("name") or selected_folder_id).strip()

            folder_items = get_folder_item_ids(selected_folder_id)
            folder_pmids = _dedupe_ids(folder_items.get("pmids") or [])
            folder_gids = _dedupe_ids(folder_items.get("guideline_ids") or [])
            folder_total = len(folder_pmids) + len(folder_gids)
            st.caption(
                f"`{selected_folder_name}` has {len(folder_pmids)} abstracts and "
                f"{len(folder_gids)} guidelines ({folder_total} total)."
            )

            c_manage_l, c_manage_r = st.columns([3, 2], gap="large")

            with c_manage_l:
                st.markdown("**Remove items from folder**")
                option_labels = _folder_item_option_labels(folder_pmids, folder_gids)
                option_keys = list(option_labels.keys())

                if not option_keys:
                    st.caption("Folder is empty.")
                else:
                    selected_remove_tokens = st.multiselect(
                        "Items",
                        options=option_keys,
                        key=f"delete_remove_folder_items_{selected_folder_id}",
                        format_func=lambda tok: option_labels.get(tok, tok),
                        placeholder="Choose one or more items to remove",
                    )
                    if st.button(
                        "Remove selected items",
                        key=f"delete_remove_folder_items_btn_{selected_folder_id}",
                        width="stretch",
                        disabled=not bool(selected_remove_tokens),
                    ):
                        remove_pmids = [
                            tok.split(":", 1)[1]
                            for tok in selected_remove_tokens
                            if tok.startswith("paper:")
                        ]
                        remove_gids = [
                            tok.split(":", 1)[1]
                            for tok in selected_remove_tokens
                            if tok.startswith("guideline:")
                        ]
                        stats = remove_items_from_folder(
                            folder_id=selected_folder_id,
                            pmids=remove_pmids,
                            guideline_ids=remove_gids,
                        )
                        removed_papers = int(stats.get("papers_removed") or "0")
                        removed_guidelines = int(stats.get("guidelines_removed") or "0")
                        removed_total = removed_papers + removed_guidelines
                        if removed_total > 0:
                            st.session_state["delete_folder_flash"] = (
                                f"Removed {removed_papers} abstracts and {removed_guidelines} guidelines "
                                f"from folder `{selected_folder_name}`."
                            )
                        else:
                            st.session_state["delete_folder_flash"] = (
                                f"No items were removed from folder `{selected_folder_name}`."
                            )
                        st.rerun()

            with c_manage_r:
                st.markdown("**Delete folder**")
                st.caption(
                    "This deletes the folder and its memberships only. "
                    "It does not delete saved abstracts or guidelines."
                )
                confirm_delete = st.checkbox(
                    "Confirm folder delete",
                    key=f"delete_folder_confirm_{selected_folder_id}",
                )
                if st.button(
                    "Delete folder",
                    key=f"delete_folder_btn_{selected_folder_id}",
                    width="stretch",
                    disabled=not bool(confirm_delete),
                ):
                    stats = delete_folder(selected_folder_id)
                    deleted = (stats.get("deleted") or "0") == "1"
                    deleted_name = (stats.get("name") or selected_folder_name).strip()
                    deleted_papers = int(stats.get("papers_removed") or "0")
                    deleted_guidelines = int(stats.get("guidelines_removed") or "0")
                    if deleted:
                        st.session_state["delete_folder_flash"] = (
                            f"Deleted folder `{deleted_name}` "
                            f"({deleted_papers} abstracts, {deleted_guidelines} guidelines removed from folder)."
                        )
                    else:
                        st.session_state["delete_folder_flash"] = "Folder no longer exists."
                    st.rerun()
