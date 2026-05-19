import streamlit as st

from ui_pages.rrt_meds_data import MED_POINT_FIELDS, RRT_GUIDE

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
    st.title("🚨 RRT")
    st.caption(
        "Rapid response team — high-acuity emergency reference. Use institutional protocols, pharmacy guidance, and clinical judgment."
    )
    with st.expander("Extensions", expanded=False):
        st.markdown("- Telemetry: `8944`")
        st.markdown("- Radiology: `5244`")

    for rrt_name, rrt_data in RRT_GUIDE.items():
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

    # ── Massive Transfusion Protocol ────────────────────────────────
    with st.expander("Massive Transfusion Protocol (MTP)", expanded=False):
        st.subheader("When to Activate MTP")
        st.markdown(
            "- Anticipated or actual transfusion of **≥ 10 units pRBC in 24 hours**, or **≥ 4 units pRBC in 1 hour** with ongoing bleeding\n"
            "- **ABC Score ≥ 2** (Assessment of Blood Consumption) — quick bedside screen:\n\n"
            "| Parameter | Criterion | Points |\n"
            "| --- | --- | --- |\n"
            "| Penetrating mechanism | Yes | 1 |\n"
            "| SBP ≤ 90 mmHg (ED arrival) | Yes | 1 |\n"
            "| HR ≥ 120 bpm (ED arrival) | Yes | 1 |\n"
            "| Positive FAST | Yes | 1 |\n"
            "\n"
            "- **Other triggers:** unstable hemorrhagic shock, ongoing massive GI bleed, postpartum hemorrhage, intraoperative hemorrhage unresponsive to surgical control, ruptured AAA\n"
            "- **Activation:** Call blood bank directly — state **\"Activate MTP for [patient name/MRN].\"** Blood bank begins issuing coolers."
        )

        st.divider()
        st.subheader("Transfusion Ratios & Product Delivery")
        st.markdown(
            "**Target ratio: 1:1:1** (pRBC : FFP : Platelets)\n\n"
            "| Product | Typical MTP Cooler (Round 1) | Goal | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| **pRBC** | 6 units | Hgb > 7 g/dL (consider > 9 in active hemorrhage) | Use O-negative (or O-positive for males/post-menopausal females) until type-specific or crossmatched blood available. Switch to type-specific ASAP to conserve O-neg supply. |\n"
            "| **FFP** | 6 units | INR < 1.5 | Thaw takes ~20 min. **Liquid plasma** or **thawed plasma** (pre-thawed, stored at 1–6°C up to 5 days) available immediately at some centers. |\n"
            "| **Platelets** | 1 apheresis unit (= ~6 pooled units) | Plt > 50,000 (> 100,000 if TBI or ongoing CNS bleed) | Each apheresis unit raises platelets ~30,000–50,000. |\n"
            "\n"
            "**Subsequent coolers** are issued until MTP is deactivated — typically same composition. Request ongoing coolers before the current one runs out."
        )

        st.divider()
        st.subheader("Adjuncts")
        st.markdown(
            "| Agent | Dose | Indication | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| **Tranexamic acid (TXA)** | **1 g IV over 10 min**, then **1 g IV over 8 hours** | Trauma: give within **3 hours** of injury (CRASH-2). GI bleed: evidence is weaker (HALT-IT was negative), but often given empirically in massive hemorrhage. Postpartum hemorrhage: 1 g IV (WOMAN trial). | Do NOT give bolus faster than 10 min (seizure risk). No benefit if > 3 hours post-injury in trauma. |\n"
            "| **Cryoprecipitate** | 10 units (1 pool) | Fibrinogen < 150–200 mg/dL | Each pool raises fibrinogen ~50–70 mg/dL. Check fibrinogen early and frequently. |\n"
            "| **Fibrinogen concentrate** | 2–4 g IV | Alternative to cryo if available | Faster to prepare, no thawing needed, lower volume. |\n"
            "| **Calcium (CaCl₂ or Ca gluconate)** | CaCl₂ 1 g IV per 4 units pRBC (or Ca gluconate 3 g) | Prevent / treat **hypocalcemia from citrate toxicity** | Citrate in banked blood chelates ionized calcium. **Hypocalcemia is the #1 metabolic complication of massive transfusion** — causes coagulopathy, cardiac dysfunction, and refractory hypotension. Check iCa frequently; keep iCa > 1.1 mmol/L. Give through a **central line** if using CaCl₂ (vesicant). |\n"
            "| **Vitamin K** | 10 mg IV (slow infusion) | If warfarin-associated or suspected vitamin K deficiency | Takes hours for full effect — FFP or PCC for immediate reversal. |\n"
            "| **4-Factor PCC (Kcentra)** | 25–50 units/kg | Warfarin reversal with life-threatening bleeding | Faster and lower volume than FFP for warfarin reversal. |\n"
            "| **Desmopressin (DDAVP)** | 0.3 μg/kg IV | Uremic platelet dysfunction, von Willebrand disease, or as adjunct in refractory coagulopathic bleeding | Enhances platelet adhesion. Effect lasts ~6–8 hours. Tachyphylaxis with repeated doses. |"
        )

        st.divider()
        st.subheader("Lab Monitoring During MTP")
        st.markdown(
            "| Lab | Frequency | Target | Action If Abnormal |\n"
            "| --- | --- | --- | --- |\n"
            "| **CBC** | Every 30–60 min | Hgb > 7, Plt > 50K (> 100K if TBI) | Transfuse pRBC or platelets |\n"
            "| **PT / INR** | Every 30–60 min | INR < 1.5 | FFP or PCC |\n"
            "| **Fibrinogen** | Every 30–60 min | > 150–200 mg/dL | Cryoprecipitate (10 units) or fibrinogen concentrate |\n"
            "| **Ionized calcium (iCa)** | Every 30 min or per 4 units pRBC | > 1.1 mmol/L | CaCl₂ 1 g IV or Ca gluconate 3 g IV |\n"
            "| **ABG / VBG** | Every 30–60 min | pH > 7.2, lactate trending down | Guides resuscitation adequacy; acidosis worsens coagulopathy |\n"
            "| **TEG / ROTEM** (if available) | Point-of-care, serial | Viscoelastic assay guides targeted component therapy | Useful in OR / trauma bay for real-time coagulation assessment |\n"
            "| **Potassium** | Every 30–60 min | 3.5–5.0 mEq/L | Banked blood is high in K⁺ — hyperkalemia can develop rapidly with massive transfusion |\n"
            "| **Temperature** | Continuous | > 36°C | Hypothermia worsens coagulopathy (see lethal triad below) |"
        )

        st.divider()
        st.subheader("The Lethal Triad of Trauma")
        st.markdown(
            "| Component | Why It Matters | How to Address |\n"
            "| --- | --- | --- |\n"
            "| **Hypothermia** | Impairs clotting factor enzyme function and platelet adhesion | **Use a rapid infuser / blood warmer for ALL products.** Warm blankets, raise room temperature, warm IV fluids. Target temp > 36°C. |\n"
            "| **Acidosis** | Inhibits clotting cascade, reduces efficacy of clotting factors | Treat the cause (hemorrhage control, volume resuscitation). Bicarb is a temporizing measure — restore perfusion. |\n"
            "| **Coagulopathy** | Dilutional (from crystalloid/colloid), consumptive (DIC), and dysfunction (hypothermia + acidosis) | 1:1:1 ratio, cryoprecipitate for low fibrinogen, TXA, calcium repletion, avoid excessive crystalloid. |\n"
            "\n"
            "These three components form a **self-reinforcing cycle** — each worsens the others. **Damage control resuscitation** prioritizes breaking this cycle: "
            "minimize crystalloid, use balanced blood product ratios, achieve surgical hemostasis early (damage control surgery), and actively rewarm."
        )

        st.divider()
        st.subheader("MTP Deactivation")
        st.markdown(
            "- Surgical/procedural hemostasis achieved\n"
            "- Hemodynamically stable without ongoing transfusion requirement\n"
            "- **Notify blood bank** to deactivate MTP and return unused products\n"
            "- Continue monitoring labs for 6–12 hours post-MTP — rebound coagulopathy and delayed bleeding can occur"
        )
