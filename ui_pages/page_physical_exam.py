import streamlit as st

from ui_pages.rrt_meds_data import MED_POINT_FIELDS, PHYSICAL_EXAM_GUIDE

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
    st.title("🩺 Bedside")
    st.caption(
        "Bedside examination references. Use clinical judgment and institutional guidelines."
    )

    for section_name, section_data in PHYSICAL_EXAM_GUIDE.items():
        with st.expander(section_name, expanded=False):
            blocks = []
            items = section_data.get("medications") or []
            for item in items:
                name = str(item.get("name") or "").strip() or "Item"
                if str(item.get("item_type") or "").strip().lower() == "procedure":
                    blocks.append(_build_procedure_block(name, item))
                else:
                    blocks.append(_build_medication_block(name, item))
            if blocks:
                st.markdown("\n\n".join(blocks))

    with st.expander("Medications Incompatible with Lactated Ringer's", expanded=False):
        st.markdown(
            "Lactated Ringer's contains **calcium (Ca²⁺)**, which is the primary "
            "source of incompatibility. Always verify with pharmacy references.\n\n"
            "| Medication | Reason |\n"
            "| --- | --- |\n"
            "| **Ceftriaxone** | Risk of calcium–ceftriaxone precipitate (especially neonates) |\n"
            "| **Phenytoin / Fosphenytoin** | Crystallizes in calcium/dextrose-containing solutions; use NS only |\n"
            "| **Sodium bicarbonate** | Forms calcium carbonate precipitate |\n"
            "| **Blood products (pRBCs, FFP, platelets)** | Ca²⁺ overwhelms citrate anticoagulant → microclots |\n"
            "| **Amphotericin B** | Incompatible with electrolyte-containing solutions |\n"
            "| **Diazepam** | Precipitates in most IV solutions including LR |\n"
            "| **Propofol** | Manufacturer advises against dilution with LR |\n"
            "| **Mannitol** | Can crystallize with electrolyte solutions |\n"
            "| **Aminocaproic acid** | Incompatible with LR |\n"
            "| **Metoclopramide** | Incompatible with calcium-containing solutions |\n"
            "| **Ampicillin / Ampicillin-sulbactam** | Accelerated degradation in LR |\n"
            "| **Nitroglycerin** | Stability issues with LR |\n"
            "| **TPN (total parenteral nutrition)** | Ca²⁺ interaction with phosphate → precipitate |"
        )
