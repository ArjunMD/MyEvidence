import streamlit as st

from ui_pages.rrt_meds_data import MED_POINT_FIELDS, RRT_MED_GUIDE

OPTIONAL_MED_POINT_FIELDS = [("comments", "Comments")]


def _build_medication_block(name: str, med: dict) -> str:
    lines = [f"**{name}**"]
    point_idx = 1
    for field_key, field_label in MED_POINT_FIELDS + OPTIONAL_MED_POINT_FIELDS:
        value = str(med.get(field_key) or "").strip()
        if not value:
            continue
        lines.append(f"{point_idx}. **{field_label}:** {value}")
        point_idx += 1

    return "\n".join(lines)


def _build_procedure_block(name: str, proc: dict) -> str:
    lines = [f"**{name}**"]

    summary = str(proc.get("summary") or "").strip()
    if summary:
        lines.append(f"- {summary}")

    steps = proc.get("steps") or []
    for step in steps:
        step_text = str(step or "").strip()
        if step_text:
            lines.append(f"- {step_text}")

    cautions = str(proc.get("cautions") or "").strip()
    if cautions:
        lines.append(f"- Cautions: {cautions}")

    fun_fact = str(proc.get("fun_fact") or "").strip()
    if fun_fact:
        lines.append(f"- Fun fact: {fun_fact}")

    return "\n".join(lines)


def render() -> None:
    st.title("🚨 RRT stuff")
    st.caption(
        "Adult emergency quick reference only. Use institutional protocols, pharmacy guidance, and clinical judgment."
    )
    with st.expander("Extensions", expanded=False):
        st.markdown("- Telemetry: `8944`")
        st.markdown("- Radiology: `5244`")

    for rrt_name, rrt_data in RRT_MED_GUIDE.items():
        with st.expander(rrt_name, expanded=False):
            blocks = []
            items = rrt_data.get("medications") or []
            for item in items:
                name = str(item.get("name") or "").strip() or "Item"
                if str(item.get("item_type") or "").strip().lower() == "procedure":
                    blocks.append(_build_procedure_block(name, item))
                else:
                    blocks.append(_build_medication_block(name, item))
            if blocks:
                st.markdown("\n\n".join(blocks))
