import streamlit as st

from ui_pages.rrt_meds_data import MED_POINT_FIELDS, RRT_MED_GUIDE


def _build_medication_block(name: str, med: dict) -> str:
    lines = [f"**{name}**"]
    for idx, (field_key, field_label) in enumerate(MED_POINT_FIELDS, start=1):
        value = str(med.get(field_key) or "").strip() or "See local protocol."
        lines.append(f"{idx}. **{field_label}:** {value}")
    return "\n".join(lines)


def _build_procedure_block(name: str, proc: dict) -> str:
    lines = [f"**{name}**"]

    summary = str(proc.get("summary") or "").strip()
    if summary:
        lines.append(summary)

    steps = proc.get("steps") or []
    if steps:
        lines.append("Steps:")
    for idx, step in enumerate(steps, start=1):
        step_text = str(step or "").strip()
        if step_text:
            lines.append(f"{idx}. {step_text}")

    cautions = str(proc.get("cautions") or "").strip()
    if cautions:
        lines.append(f"**Cautions:** {cautions}")

    fun_fact = str(proc.get("fun_fact") or "").strip()
    if fun_fact:
        lines.append(f"**Fun fact:** {fun_fact}")

    return "\n".join(lines)


def render() -> None:
    st.title("🚨 RRT stuff")
    st.caption(
        "Adult emergency quick reference only. Use institutional protocols, pharmacy guidance, and clinical judgment."
    )

    brady = RRT_MED_GUIDE.get("Bradycardia") or {}
    with st.expander("Bradycardia", expanded=False):
        items = brady.get("medications") or []
        blocks = []
        for item in items:
            name = str(item.get("name") or "").strip() or "Item"
            if str(item.get("item_type") or "").strip().lower() == "procedure":
                blocks.append(_build_procedure_block(name, item))
            else:
                blocks.append(_build_medication_block(name, item))
        if blocks:
            st.markdown("\n\n".join(blocks))
