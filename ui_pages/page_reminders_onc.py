import streamlit as st


def render() -> None:
    st.title("\U0001f4dd Oncology")

    with st.expander("Famous Side Effects of Chemotherapeutic Agents", expanded=True):
        st.markdown(
            """
| Agent | Side Effect 1 | Side Effect 2 | Side Effect 3 |
|---|---|---|---|
| **Bleomycin** | Pulmonary fibrosis | Skin hyperpigmentation | Raynaud phenomenon |
| **Doxorubicin (Adriamycin)** | Dilated cardiomyopathy (dose-dependent) | Myelosuppression | Radiation recall dermatitis |
| **Trastuzumab (Herceptin)** | Cardiomyopathy (reversible) | Infusion reactions | Pulmonary toxicity |
| **Cyclophosphamide** | Hemorrhagic cystitis | Myelosuppression | SIADH |
| **Ifosfamide** | Hemorrhagic cystitis | Encephalopathy | Nephrotoxicity (Fanconi syndrome) |
| **Cisplatin** | Nephrotoxicity | Ototoxicity | Peripheral neuropathy |
| **Vincristine** | Peripheral neuropathy (dose-limiting) | Constipation / ileus | SIADH |
| **Methotrexate** | Mucositis | Hepatotoxicity / fibrosis | Pneumonitis |
| **5-Fluorouracil (5-FU)** | Hand-foot syndrome | Mucositis / diarrhea | Coronary vasospasm |
| **Capecitabine** | Hand-foot syndrome | Diarrhea | Myelosuppression |
| **Oxaliplatin** | Cold-triggered peripheral neuropathy | Myelosuppression | Hepatic sinusoidal injury |
| **Irinotecan** | Early & late diarrhea | Cholinergic syndrome | Myelosuppression |
| **Busulfan** | Pulmonary fibrosis ("busulfan lung") | Hyperpigmentation | Seizures (high-dose) |
| **Anthracyclines (class)** | Cardiotoxicity (cumulative) | Myelosuppression | Secondary leukemia |
| **Taxanes (paclitaxel, docetaxel)** | Peripheral neuropathy | Hypersensitivity reactions | Myelosuppression |
| **Bevacizumab (Avastin)** | GI perforation | Wound-healing impairment | Hypertension |
| **Rituximab** | Infusion reactions | Hepatitis B reactivation | PML |
| **Immune checkpoint inhibitors** | Colitis / diarrhea | Pneumonitis | Thyroiditis / hypophysitis |
| **Ipilimumab (anti-CTLA-4)** | Colitis (more common than anti-PD-1) | Hepatitis | Hypophysitis |
| **Gemcitabine** | Myelosuppression | Pulmonary toxicity | HUS / TTP (rare) |
| **Bortezomib** | Peripheral neuropathy | Thrombocytopenia | Herpes zoster reactivation |
| **Thalidomide / Lenalidomide** | Teratogenicity | VTE | Peripheral neuropathy |
| **All-trans retinoic acid (ATRA)** | Differentiation syndrome | Pseudotumor cerebri | Hypertriglyceridemia |
| **Asparaginase** | Pancreatitis | Hypersensitivity / anaphylaxis | Thrombosis |
| **Cytarabine (Ara-C, high-dose)** | Cerebellar toxicity | Myelosuppression | Keratoconjunctivitis |
| **Etoposide** | Secondary AML / MDS | Myelosuppression | Hypotension (with rapid infusion) |
| **Carmustine (BCNU)** | Pulmonary fibrosis | Myelosuppression (delayed) | Hepatotoxicity |
| **Mitomycin C** | Hemolytic uremic syndrome (HUS) | Myelosuppression (delayed) | Pulmonary toxicity |
"""
        )
