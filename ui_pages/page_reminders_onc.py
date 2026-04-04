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

    with st.expander("Famous Side Effects of Immunotherapy", expanded=True):
        st.markdown("### Immune-Related Adverse Events (irAEs) — Class Effects")
        st.markdown(
            """
All checkpoint inhibitors (anti-PD-1, anti-PD-L1, anti-CTLA-4) can cause immune-related
adverse events (irAEs) via unchecked T-cell activation against self-antigens.

| Organ System | irAE | Notes |
|---|---|---|
| **GI** | Colitis / diarrhea | More common with anti-CTLA-4; can perforate |
| **Liver** | Hepatitis (transaminitis) | Usually asymptomatic; monitor LFTs |
| **Lung** | Pneumonitis | Can be fatal; dyspnea + ground-glass opacities |
| **Endocrine** | Thyroiditis → hypothyroidism | Often permanent; painless thyroiditis then burnout |
| **Endocrine** | Hypophysitis | Headache, fatigue, panhypopituitarism; more with anti-CTLA-4 |
| **Endocrine** | Adrenal insufficiency | Primary (adrenalitis) or secondary (hypophysitis) |
| **Endocrine** | Type 1 diabetes (fulminant) | Rare; can present as DKA |
| **Skin** | Rash / pruritus / vitiligo | Most common irAE overall; vitiligo = good prognostic sign in melanoma |
| **MSK** | Inflammatory arthritis | Can mimic RA; may become chronic |
| **Renal** | Interstitial nephritis | Rising creatinine; usually responds to steroids |
| **Neuro** | Myasthenia gravis / Guillain-Barré / encephalitis | Rare but can be life-threatening |
| **Cardiac** | Myocarditis | Rare but high mortality; check troponin if suspected |
| **Heme** | Hemolytic anemia / ITP / aplastic anemia | Rare; Coombs testing helpful |
"""
        )

        st.markdown("### Timing of irAEs")
        st.markdown(
            """
irAEs are **not** cumulative-dose toxicities (unlike anthracycline cardiotoxicity). They are
**immune-mediated** and can occur at any point — but follow a general temporal pattern:

| Timing | irAE | Details |
|---|---|---|
| **Early (weeks 2–6)** | Skin (rash, pruritus) | Most common first irAE; often appears after 1st–2nd cycle |
| **Early (weeks 3–6)** | Colitis / diarrhea | Earlier and more frequent with anti-CTLA-4 |
| **Early-mid (weeks 6–12)** | Hepatitis | Often detected on routine LFT monitoring before symptoms |
| **Mid (weeks 6–14)** | Pneumonitis | Median onset ~10 weeks for anti-PD-1; later than skin/GI |
| **Mid (weeks 6–14)** | Hypophysitis | More with ipilimumab; can be subtle (fatigue, headache) |
| **Mid-late (weeks 8–16)** | Thyroiditis → hypothyroidism | Thyrotoxicosis phase may be brief/missed; hypothyroid phase often permanent |
| **Late (weeks 12+)** | Nephritis | Median onset ~3–6 months |
| **Any time** | Myocarditis | Rare; most cases within first 3 months but can occur at any cycle |
| **Any time** | Neurologic (MG, GBS, encephalitis) | Rare; no predictable window |
| **Any time** | Type 1 diabetes (fulminant) | Rare; can present abruptly as DKA at any point |
| **Delayed (months–years after stopping)** | Late-onset / flare irAEs | irAEs can first appear or recur **months after discontinuation** |

**Key clinical points:**
- **Not dose-dependent**: irAEs relate to immune activation, not cumulative drug exposure — a patient can develop colitis on cycle 1 or cycle 20
- **Dose-escalation / combo effect**: Combination ipilimumab + nivolumab causes earlier onset and higher frequency of irAEs vs monotherapy, due to more potent immune disinhibition (not dose accumulation)
- **Anti-CTLA-4 vs anti-PD-1 timing**: Ipilimumab irAEs tend to cluster earlier (weeks 2–8) while anti-PD-1 irAEs spread over a wider window
- **Rechallenge risk**: irAEs can recur on rechallenge (~30% of cases), often the same organ system; does not require dose escalation
- **Persistent / late irAEs**: Endocrinopathies (hypothyroidism, adrenal insufficiency, hypophysitis) are usually **permanent** even after stopping therapy; other irAEs can flare months later
- **Contrast with chemotherapy**: Chemotherapy toxicities are generally dose-dependent and temporally linked to administration; immunotherapy irAEs are immune-mediated and temporally unpredictable
"""
        )

        st.markdown("### Medication-Specific Side Effects")
        st.markdown(
            """
| Agent | Mechanism | Key / Distinguishing Side Effects |
|---|---|---|
| **Ipilimumab** (anti-CTLA-4) | Blocks CTLA-4 on T cells | Colitis (up to 30%), hypophysitis (up to 13%), hepatitis — irAEs more frequent and severe than PD-1 agents |
| **Nivolumab** (anti-PD-1) | Blocks PD-1 on T cells | Pneumonitis, thyroiditis, fatigue — irAEs generally milder than ipilimumab |
| **Pembrolizumab** (anti-PD-1) | Blocks PD-1 on T cells | Pneumonitis, thyroiditis, nephritis — similar profile to nivolumab |
| **Atezolizumab** (anti-PD-L1) | Blocks PD-L1 on tumor/APC | Pneumonitis, hepatitis, rash — slightly lower pneumonitis rate vs anti-PD-1 |
| **Durvalumab** (anti-PD-L1) | Blocks PD-L1 on tumor/APC | Pneumonitis (esp. post-chemoRT), thyroiditis, hepatitis |
| **Avelumab** (anti-PD-L1) | Blocks PD-L1 on tumor/APC | Infusion-related reactions (more common than other PD-L1 agents), fatigue |
| **Ipilimumab + Nivolumab** (combo) | Dual checkpoint blockade | irAEs in ~60% (grade 3-4 in ~30%); colitis, hepatitis, and endocrinopathies significantly more frequent |
| **Cemiplimab** (anti-PD-1) | Blocks PD-1 on T cells | Pneumonitis, hypothyroidism — used mainly in cutaneous SCC |
| **Dostarlimab** (anti-PD-1) | Blocks PD-1 on T cells | Thyroiditis, anemia — notable for dMMR/MSI-H rectal cancer responses |
| **Tremelimumab** (anti-CTLA-4) | Blocks CTLA-4 on T cells | Colitis, rash, hepatitis — similar profile to ipilimumab; used with durvalumab |

**Management principles:**
- **Grade 1**: Continue immunotherapy, monitor closely
- **Grade 2**: Hold immunotherapy, consider steroids (prednisone 0.5–1 mg/kg)
- **Grade 3**: Hold immunotherapy, high-dose steroids (prednisone 1–2 mg/kg)
- **Grade 4**: Permanently discontinue, high-dose IV steroids; consider infliximab (colitis) or mycophenolate (hepatitis) if steroid-refractory
- **Endocrinopathies**: Hormone replacement rather than immunosuppression (thyroid hormone, hydrocortisone)
"""
        )
