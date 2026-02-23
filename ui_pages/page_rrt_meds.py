import streamlit as st

from ui_pages.rrt_meds_data import MED_POINT_FIELDS, RRT_MED_GUIDE


def _render_medication_points(med: dict) -> None:
    for idx, (field_key, field_label) in enumerate(MED_POINT_FIELDS, start=1):
        value = str(med.get(field_key) or "").strip() or "See local protocol."
        st.markdown(f"{idx}. **{field_label}:** {value}")


def render() -> None:
    st.title("🚨 RRT meds")
    st.caption(
        "Adult emergency quick reference only. Use institutional protocols, pharmacy guidance, and clinical judgment."
    )

    for rrt_name, scenario in RRT_MED_GUIDE.items():
        with st.expander(rrt_name, expanded=False):
            st.markdown(f"**When to use:** {scenario.get('when_to_use', '')}")
            st.markdown("---")

            meds = scenario.get("medications") or []
            for idx, med in enumerate(meds):
                name = str(med.get("name") or "").strip() or "Medication"
                st.markdown(f"**{name}**")
                _render_medication_points(med)

                if idx < len(meds) - 1:
                    st.markdown("---")
