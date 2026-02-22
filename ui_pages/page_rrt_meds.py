from typing import Dict, List

import streamlit as st

RRT_MED_GUIDE: Dict[str, Dict[str, object]] = {
    "Bradycardia (symptomatic)": {
        "when_to_use": "For unstable/symptomatic bradycardia (hypotension, shock, altered mental status, chest pain).",
        "medications": [
            {
                "name": "Atropine",
                "dose": "1 mg IV bolus every 3-5 minutes; max total 3 mg.",
                "contra": "Use caution in acute coronary ischemia and glaucoma; often ineffective in high-grade AV block or transplanted hearts.",
            },
            {
                "name": "Epinephrine infusion",
                "dose": "2-10 mcg/min IV infusion, titrate to perfusion and blood pressure.",
                "contra": "Avoid or use caution with active tachyarrhythmias, severe hypertension, or significant myocardial ischemia.",
            },
            {
                "name": "Dopamine infusion",
                "dose": "5-20 mcg/kg/min IV infusion, titrate to response.",
                "contra": "Avoid in uncorrected tachyarrhythmias or pheochromocytoma; caution for peripheral ischemia/extravasation.",
            },
        ],
    },
    "Hypoxia / severe bronchospasm": {
        "when_to_use": "For RRTs with respiratory distress and hypoxemia, including severe asthma/COPD exacerbation patterns.",
        "medications": [
            {
                "name": "Albuterol (nebulized)",
                "dose": "2.5 mg nebulized every 20 minutes for 3 doses, or continuous 10-15 mg/hour.",
                "contra": "Use caution with severe tachyarrhythmias, significant hypokalemia, or active myocardial ischemia.",
            },
            {
                "name": "Ipratropium (nebulized)",
                "dose": "0.5 mg nebulized every 20 minutes for 3 doses (often paired with albuterol).",
                "contra": "Avoid with known hypersensitivity to ipratropium/atropine derivatives.",
            },
            {
                "name": "Methylprednisolone",
                "dose": "125 mg IV once (or equivalent systemic steroid).",
                "contra": "No absolute contraindication in life-threatening bronchospasm; caution with severe hyperglycemia, active infection, or GI bleeding risk.",
            },
            {
                "name": "Magnesium sulfate",
                "dose": "2 g IV over 15-20 minutes in severe bronchospasm.",
                "contra": "Use caution with myasthenia gravis, high-grade heart block, severe renal failure, or hypotension.",
            },
        ],
    },
    "Seizure / status epilepticus": {
        "when_to_use": "For ongoing seizure activity or recurrent seizures without return to baseline.",
        "medications": [
            {
                "name": "Lorazepam",
                "dose": "4 mg IV over 2 minutes; may repeat once after 5-10 minutes.",
                "contra": "Use caution in severe respiratory depression, hypotension, or known benzodiazepine hypersensitivity.",
            },
            {
                "name": "Midazolam (if no IV access)",
                "dose": "10 mg IM once (or 5 mg IV/IN depending route and protocol).",
                "contra": "Use caution with respiratory depression and hemodynamic instability.",
            },
            {
                "name": "Levetiracetam",
                "dose": "60 mg/kg IV loading dose (max 4,500 mg), typically over 10-15 minutes.",
                "contra": "Dose-adjust in renal impairment; monitor for sedation/behavioral effects.",
            },
            {
                "name": "Fosphenytoin",
                "dose": "20 mg PE/kg IV loading dose (max infusion rate 150 mg PE/min).",
                "contra": "Avoid in sinus bradycardia, 2nd/3rd-degree AV block, or Adams-Stokes syndrome.",
            },
        ],
    },
    "Hypotension / shock": {
        "when_to_use": "For undifferentiated shock after immediate airway/oxygen support and rapid bedside evaluation.",
        "medications": [
            {
                "name": "Isotonic crystalloid",
                "dose": "500-1,000 mL IV bolus, reassess frequently for fluid responsiveness.",
                "contra": "Use caution in pulmonary edema, severe heart failure, or ESRD with volume overload.",
            },
            {
                "name": "Norepinephrine infusion",
                "dose": "0.05-1 mcg/kg/min IV infusion, titrate to MAP/perfusion goals.",
                "contra": "Correct severe hypovolemia first when possible; caution for digital/mesenteric ischemia.",
            },
            {
                "name": "Vasopressin",
                "dose": "0.03 units/min IV infusion (fixed dose) as adjunct in refractory vasodilatory shock.",
                "contra": "Use caution in coronary/peripheral ischemia and hyponatremia risk.",
            },
            {
                "name": "Epinephrine infusion",
                "dose": "0.02-0.5 mcg/kg/min IV infusion when additional inotropy/vasopressor support is needed.",
                "contra": "Use caution with tachyarrhythmias and myocardial ischemia.",
            },
        ],
    },
    "Anaphylaxis": {
        "when_to_use": "For suspected anaphylaxis with airway compromise, hypotension, bronchospasm, or multi-system allergic reaction.",
        "medications": [
            {
                "name": "Epinephrine IM (1 mg/mL)",
                "dose": "0.3-0.5 mg IM into lateral thigh; repeat every 5-15 minutes as needed.",
                "contra": "No absolute contraindication in true anaphylaxis.",
            },
            {
                "name": "Diphenhydramine",
                "dose": "25-50 mg IV/IM adjunctive therapy.",
                "contra": "Use caution in older adults, glaucoma, urinary retention, and delirium risk.",
            },
            {
                "name": "Famotidine",
                "dose": "20 mg IV adjunctive therapy.",
                "contra": "Dose-adjust in renal dysfunction.",
            },
            {
                "name": "Methylprednisolone",
                "dose": "125 mg IV adjunctive therapy (does not replace epinephrine).",
                "contra": "No immediate absolute contraindication in severe reaction; caution with hyperglycemia/infection risk.",
            },
        ],
    },
}


def render() -> None:
    st.title("🚨 RRT meds")
    st.caption(
        "Adult emergency quick reference only. Use institutional protocols, pharmacy guidance, and clinical judgment."
    )

    rrt_options: List[str] = list(RRT_MED_GUIDE.keys())
    for rrt_name in rrt_options:
        scenario = RRT_MED_GUIDE[rrt_name]
        with st.expander(rrt_name, expanded=False):
            st.markdown(f"**When to use:** {scenario.get('when_to_use', '')}")
            st.markdown("---")

            meds = scenario.get("medications") or []
            for idx, med in enumerate(meds):
                name = str(med.get("name") or "").strip()
                dose = str(med.get("dose") or "").strip()
                contra = str(med.get("contra") or "").strip()

                st.markdown(f"**{name}**")
                st.markdown(f"- **Dose:** {dose}")
                st.markdown(f"- **Contraindications / cautions:** {contra}")

                if idx < len(meds) - 1:
                    st.markdown("---")
