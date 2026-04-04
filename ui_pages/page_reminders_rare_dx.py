import streamlit as st


def render() -> None:
    st.title("\U0001f9e9 Rare Dx")
    st.caption(
        "Illness scripts for rare diagnoses frequently missed or associated "
        "with delayed / recurrent presentations."
    )

    # ── Neurologic ──────────────────────────────────────────────────────
    with st.expander("Neurologic", expanded=False):
        st.markdown(
            """
| Diagnosis | Classic Presentation | Why It's Missed | Simple Lab to Consider |
|---|---|---|---|
| **Anti-NMDA receptor encephalitis** | Young person with new-onset psychiatric symptoms → seizures → dyskinesias → autonomic instability; often preceded by ovarian teratoma | Attributed to primary psychiatric illness early on; teratoma not yet found | **CSF anti-NMDA receptor antibodies**; LP with lymphocytic pleocytosis |
| **Neurosarcoidosis** | Cranial neuropathies (especially CN VII), hypothalamic dysfunction, aseptic meningitis, myelopathy; may lack pulmonary involvement | No systemic sarcoid in ~5–10%; MRI mimics MS or lymphoma | **ACE level** (serum); chest CT for hilar adenopathy; CSF protein/glucose |
| **CNS vasculitis** | Recurrent headaches, strokes in multiple vascular territories, cognitive decline in young/middle-aged patient; may be primary or secondary | MRI/angiography findings overlap with atherosclerosis, reversible vasoconstriction syndrome, or infection | **ESR / CRP**; LP (lymphocytic pleocytosis, elevated protein); consider brain biopsy |
| **Neurosyphilis** | Protean — asymptomatic CSF changes, meningitis, stroke (meningovascular), tabes dorsalis, general paresis, Argyll Robertson pupils | Low clinical suspicion in modern era; not tested in standard STI panels | **RPR/VDRL** (serum); if positive, CSF VDRL |
| **Leptomeningeal carcinomatosis** | Progressive cranial neuropathies, radiculopathies, headache, and cognitive changes in a patient with known or occult malignancy | CSF cytology is only ~50% sensitive on first LP; MRI enhancement can be subtle | **CSF cytology** (repeat if initially negative); CSF protein and glucose |
| **Susac syndrome** | Triad: encephalopathy, branch retinal artery occlusions, sensorineural hearing loss; young adults; "snowball" lesions in corpus callosum on MRI | Incomplete triad at onset; confused with MS or ADEM | **Fluorescein angiography** (branch retinal artery occlusions); audiometry; MRI brain |
| **Cerebral amyloid angiopathy (CAA)** | Recurrent lobar hemorrhages or transient focal neurological episodes in elderly; cortical superficial siderosis on MRI | Attributed to hypertensive hemorrhage; siderosis overlooked | **MRI with gradient echo / SWI** (cortical microbleeds, superficial siderosis); no specific blood test — diagnosis is imaging-based |
"""
        )

    # ── Endocrine / Metabolic ───────────────────────────────────────────
    with st.expander("Endocrine / Metabolic", expanded=False):
        st.markdown(
            """
| Diagnosis | Classic Presentation | Why It's Missed | Simple Lab to Consider |
|---|---|---|---|
| **Addisonian crisis** | Hypotension refractory to fluids, hyponatremia, hyperkalemia, hypoglycemia; hyperpigmentation (primary); precipitated by illness/stress/surgery | Attributed to sepsis or volume depletion; cortisol not checked in the acute setting | **Random cortisol** (< 3 µg/dL virtually diagnostic in acute illness); ACTH level |
| **Hyperaldosteronism** | Resistant hypertension, hypokalemia (though normokalemic in ~50%), metabolic alkalosis; fatigue, muscle weakness | Hypokalemia attributed to diuretics; under-screened in resistant HTN | **Aldosterone-to-renin ratio (ARR)** (must hold interfering meds) |
| **Wilson's disease** | Young patient with liver disease (hepatitis to fulminant failure) + neuropsychiatric symptoms (tremor, dysarthria, personality changes); Kayser-Fleischer rings | Rare; liver disease attributed to viral/autoimmune/NAFLD; neuropsych attributed to primary psych | **Ceruloplasmin** (low); 24-hour urine copper (elevated); slit-lamp exam for KF rings |
| **Familial Mediterranean fever** | Recurrent, self-limited episodes of fever + serositis (peritonitis, pleuritis, arthritis) lasting 1–3 days; Mediterranean/Middle Eastern ancestry | Recurrent abdominal pain → repeated ER visits and unnecessary surgeries | **CRP / ESR** (markedly elevated during attacks, normalize between); genetic testing (MEFV) |
"""
        )

    # ── Hematologic ─────────────────────────────────────────────────────
    with st.expander("Hematologic", expanded=False):
        st.markdown(
            """
| Diagnosis | Classic Presentation | Why It's Missed | Simple Lab to Consider |
|---|---|---|---|
| **Thrombotic thrombocytopenic purpura (TTP)** | Pentad rarely complete — microangiopathic hemolytic anemia (MAHA) + thrombocytopenia is sufficient; fever, renal dysfunction, neuro changes | Attributed to DIC or ITP; schistocytes overlooked on smear; delay kills | **Peripheral smear** (schistocytes); LDH, haptoglobin, indirect bilirubin; **ADAMTS13 activity** |
| **Hemophagocytic lymphohistiocytosis (HLH)** | High fevers, cytopenias, hepatosplenomegaly, hyperferritinemia, hypertriglyceridemia, elevated soluble IL-2R; triggered by infection, malignancy, or autoimmune disease | Looks like sepsis or multiorgan failure; ferritin > 10,000 is a red flag | **Ferritin** (markedly elevated, often > 10,000); triglycerides; fibrinogen (low); soluble IL-2R |
| **Paroxysmal nocturnal hemoglobinuria (PNH)** | Episodic hemolysis, dark morning urine, cytopenias, venous thrombosis in unusual sites (hepatic, cerebral, abdominal); may overlap with aplastic anemia | Hemolysis attributed to other causes; Budd-Chiari or cerebral venous thrombosis not linked to PNH | **Flow cytometry for CD55/CD59** (GPI-anchored proteins); LDH, reticulocyte count, haptoglobin |
| **Mast cell disease (systemic mastocytosis)** | Recurrent anaphylaxis/flushing without clear trigger, GI symptoms (diarrhea, cramping), osteoporosis; urticaria pigmentosa skin lesions | Attributed to idiopathic anaphylaxis, IBS, or functional GI disease | **Serum tryptase** (persistently elevated > 20 ng/mL); bone marrow biopsy if high clinical suspicion |
| **VEXAS syndrome** | Middle-aged to elderly adults with recurrent fevers, cytopenias (especially macrocytic anemia + MDS), venous thrombosis, chondritis, pulmonary infiltrates, skin lesions; refractory to standard immunosuppression | Diagnosed as relapsing polychondritis, MDS, Sweet syndrome, or PAN individually without unifying diagnosis | **CBC with MCV** (macrocytosis); peripheral smear (cytoplasmic vacuoles in myeloid/erythroid precursors); **UBA1 mutation** (somatic, on genetic testing) |
"""
        )

    # ── Rheumatologic / Autoimmune ──────────────────────────────────────
    with st.expander("Rheumatologic / Autoimmune", expanded=False):
        st.markdown(
            """
| Diagnosis | Classic Presentation | Why It's Missed | Simple Lab to Consider |
|---|---|---|---|
| **Catastrophic antiphospholipid syndrome (CAPS)** | Rapid-onset multiorgan thrombosis (≥ 3 organs in < 1 week) — renal, pulmonary, CNS, cardiac; often triggered by infection, surgery, or anticoagulation withdrawal | Looks like DIC, TTP, or sepsis with multiorgan failure; aPL antibodies not sent acutely | **Antiphospholipid antibodies** (lupus anticoagulant, anti-cardiolipin, anti-β2-glycoprotein I); peripheral smear for MAHA |
| **Eosinophilic granulomatosis with polyangiitis (EGPA)** | Asthma (adult-onset, severe) → peripheral eosinophilia → vasculitis (neuropathy, cardiac, skin, GI); may have sinusitis | Eosinophilia attributed to allergy; neuropathy to other causes; cardiac involvement can be fatal | **CBC with differential** (eosinophilia, often > 1500); ANCA (p-ANCA/MPO in ~40%); troponin and echo (cardiac) |
| **Adult-onset Still's disease** | Quotidian (daily) spiking fevers, evanescent salmon-colored rash, arthritis, sore throat, hepatosplenomegaly, leukocytosis, hyperferritinemia | Extensive infectious and malignancy workup is negative; ferritin-to-glycosylated-ferritin ratio not checked | **Ferritin** (markedly elevated); **glycosylated ferritin** (< 20% suggests Still's); CRP/ESR |
| **Reactive arthritis** | Asymmetric oligoarthritis (large joints, lower extremity) weeks after GI or GU infection; conjunctivitis, urethritis; enthesitis, dactylitis; HLA-B27 associated | Preceding infection may be mild/forgotten; joint symptoms attributed to septic arthritis or gout | **HLA-B27**; ESR/CRP; synovial fluid analysis (inflammatory, culture negative); urine NAAT for Chlamydia |
| **Anti-synthetase syndrome** | Interstitial lung disease + inflammatory myopathy + mechanic's hands (cracked, fissured skin on fingers); Raynaud's, arthritis, fever | ILD attributed to idiopathic pulmonary fibrosis; myopathy may be subtle; mechanic's hands overlooked | **Anti-Jo-1 antibody** (most common; broader myositis panel for others); CK; HRCT chest |
"""
        )

    # ── Oncologic / Hematologic-Oncologic ───────────────────────────────
    with st.expander("Oncologic / Hematologic-Oncologic", expanded=False):
        st.markdown(
            """
| Diagnosis | Classic Presentation | Why It's Missed | Simple Lab to Consider |
|---|---|---|---|
| **Amyloidosis (AL / systemic)** | Nephrotic syndrome, restrictive cardiomyopathy (low voltage on ECG), hepatomegaly, macroglossia, periorbital purpura, neuropathy; underlying plasma cell dyscrasia | Protean manifestations; cardiac amyloid mistaken for HFpEF; renal for other glomerulopathies | **SPEP/UPEP with immunofixation** + serum free light chains; NT-proBNP and troponin (cardiac staging) |
| **Cardiac amyloidosis** | HFpEF with low-voltage ECG (voltage-mass mismatch), increased wall thickness, diastolic dysfunction; apical sparing on strain imaging; ATTR (wild-type in elderly) or AL | Labeled as HFpEF or hypertensive cardiomyopathy; echocardiographic LVH is not true hypertrophy | **NT-proBNP** and troponin (often disproportionately elevated); **technetium pyrophosphate scan** (ATTR); SPEP/free light chains (AL) |
| **POEMS syndrome** | Polyneuropathy, organomegaly, endocrinopathy, monoclonal protein (usually lambda), skin changes; sclerotic bone lesions; elevated VEGF | Neuropathy attributed to CIDP; monoclonal protein on SPEP is small and overlooked | **SPEP with immunofixation** (lambda-restricted M-protein); **VEGF level** (markedly elevated); skeletal survey for sclerotic lesions |
| **Castleman disease** | Unicentric: asymptomatic lymphadenopathy; Multicentric: systemic inflammation, cytopenias, organomegaly, effusions, skin findings; elevated IL-6 | Multicentric mimics lymphoma, autoimmune disease, or infection; idiopathic MCD is a diagnosis of exclusion | **IL-6** (elevated); CRP; HIV and HHV-8 serology (HHV-8-associated MCD); lymph node biopsy |
| **Carcinoid crisis** | Severe flushing, bronchospasm, tachycardia, hemodynamic instability; precipitated by anesthesia, biopsy, or manipulation of carcinoid tumor | May be first presentation of occult carcinoid; mistaken for anaphylaxis | **24-hour urine 5-HIAA**; serum chromogranin A; CT abdomen (liver mets, small bowel mass) |
"""
        )

    # ── Pulmonary ───────────────────────────────────────────────────────
    with st.expander("Pulmonary", expanded=False):
        st.markdown(
            """
| Diagnosis | Classic Presentation | Why It's Missed | Simple Lab to Consider |
|---|---|---|---|
| **Pulmonary alveolar proteinosis (PAP)** | Progressive dyspnea, nonproductive cough; "crazy paving" pattern on CT; milky BAL fluid; often autoimmune (anti-GM-CSF antibodies) | Rare; CT pattern overlaps with PCP, pulmonary edema, and hemorrhage | **Anti-GM-CSF antibodies** (serum); LDH (elevated); PFTs (restrictive pattern, decreased DLCO); BAL (milky, PAS-positive) |
| **PJP (Pneumocystis jirovecii pneumonia)** | Subacute dyspnea, dry cough, hypoxia out of proportion to imaging; bilateral ground-glass opacities; in immunocompromised (HIV, transplant, chronic steroids) | Ground-glass attributed to viral pneumonia or fluid overload; not suspected in non-HIV immunosuppressed patients on chronic steroids | **LDH** (elevated, often > 500); **beta-D-glucan** (1,3-BDG, elevated); induced sputum or BAL for silver stain / PCR |
"""
        )

    # ── GI / Hepatobiliary ──────────────────────────────────────────────
    with st.expander("GI / Hepatobiliary", expanded=False):
        st.markdown(
            """
| Diagnosis | Classic Presentation | Why It's Missed | Simple Lab to Consider |
|---|---|---|---|
| **Mesenteric ischemia** | Acute: severe abdominal pain out of proportion to exam, often in patient with AF or vascular disease; Chronic: postprandial pain, food fear, weight loss | Acute: normal labs early; CT without contrast misses it; Chronic: attributed to functional GI disease or malignancy | **Lactate** (elevated late, not sensitive early); **CT angiography** (arterial and venous phase); D-dimer |
| **Primary sclerosing cholangitis (without obvious IBD)** | Cholestatic liver enzymes (elevated ALP), pruritus, fatigue; beaded bile ducts on MRCP; ~30% may not have overt IBD at diagnosis | Elevated ALP attributed to medications, fatty liver, or other cholestatic disease; IBD absence lowers suspicion | **ALP** (elevated, cholestatic pattern); **p-ANCA** (positive in ~80%); MRCP (beading/strictures); consider colonoscopy for subclinical IBD |
| **Whipple disease** | Classic tetrad: diarrhea, weight loss, arthralgias, and abdominal pain; may include CNS involvement (cognitive changes, oculomasticatory myorhythmia) and cardiac valve disease | Very rare; arthralgias precede GI symptoms by years; treated as seronegative RA | **Small bowel biopsy** with PAS staining (foamy macrophages); **Tropheryma whipplei PCR** (stool, saliva, or tissue) |
"""
        )

