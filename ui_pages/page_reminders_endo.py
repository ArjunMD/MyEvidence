import streamlit as st


def render() -> None:
    st.title("📝 Endocrinology")

    with st.expander("Adrenal Insufficiency", expanded=False):
        st.subheader("Overview")
        st.markdown(
            "| Type | Level of Defect | Cortisol | ACTH | Aldosterone | Key Causes |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| **Primary** (Addison disease) | Adrenal gland destruction/dysfunction | ↓ | ↑↑ | ↓ | Autoimmune (most common in developed countries), TB (most common worldwide), adrenal hemorrhage (Waterhouse-Friderichsen), bilateral adrenal metastases, infections (CMV, HIV, fungal), drugs (ketoconazole, etomidate, mitotane), adrenoleukodystrophy |\n"
            "| **Secondary** | Pituitary — decreased ACTH secretion | ↓ | ↓ / inappropriately normal | **Preserved** (aldosterone is RAAS-driven) | **Chronic exogenous glucocorticoid use** (most common overall cause of AI), pituitary tumor/surgery/radiation, Sheehan syndrome, lymphocytic hypophysitis, infiltrative disease |\n"
            "| **Tertiary** | Hypothalamus — decreased CRH | ↓ | ↓ | **Preserved** | Chronic exogenous glucocorticoid use (HPA axis suppression), hypothalamic lesions |\n"
        )

        st.divider()
        st.subheader("Clinical Features")
        st.markdown(
            "| Feature | Primary | Secondary / Tertiary | Why the Difference |\n"
            "| --- | --- | --- | --- |\n"
            "| **Hyperpigmentation** | ✅ Present (skin creases, buccal mucosa, scars) | ❌ Absent | ACTH is elevated in primary AI → ACTH is cleaved from POMC along with MSH (melanocyte-stimulating hormone) |\n"
            "| **Hyperkalemia** | ✅ Present | ❌ Absent | Aldosterone is deficient in primary AI → impaired K⁺ excretion. Aldosterone is preserved in secondary/tertiary. |\n"
            "| **Hyponatremia** | ✅ Present | ✅ Present | Primary: aldosterone deficiency → Na⁺ wasting. Secondary/tertiary: cortisol deficiency → ↑ ADH (cortisol normally suppresses ADH) → dilutional hyponatremia |\n"
            "| **Hypotension / shock** | ✅ Severe | ✅ Present but often less severe | Primary loses both cortisol AND aldosterone; secondary/tertiary lose only cortisol |\n"
            "| **Hypoglycemia** | ✅ | ✅ | Cortisol is a counter-regulatory hormone for glucose |\n"
            "| **Salt craving** | ✅ | ❌ | Aldosterone deficiency in primary AI |\n"
            "| **Eosinophilia / lymphocytosis** | ✅ | ✅ | Cortisol normally suppresses eosinophils and lymphocytes |\n"
        )

        st.divider()
        st.subheader("Diagnostic Testing")
        st.markdown(
            "**Step 1: Confirm cortisol deficiency**\n\n"
            "| Test | How to Perform | Interpretation | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| **Morning serum cortisol** (8 AM) | Draw between 6–8 AM (cortisol peaks with circadian rhythm) | **< 3 μg/dL** → AI very likely. **> 15 μg/dL** → AI essentially excluded. **3–15 μg/dL** → indeterminate, proceed to stimulation test. | Quick screening test. Not definitive in the indeterminate range. Values may be unreliable on estrogen/OCP (↑ CBG falsely elevates total cortisol). |\n"
            "| **ACTH stimulation test (Cosyntropin test)** | Give **250 μg IV cosyntropin** (synthetic ACTH). Measure serum cortisol at **baseline, 30 min, and 60 min**. | **Peak cortisol ≥ 18 μg/dL** → normal adrenal response (AI excluded). **Peak cortisol < 18 μg/dL** → adrenal insufficiency confirmed. | **Gold standard initial test.** Diagnoses primary AI reliably. May miss **early or recent-onset secondary AI** — the adrenals haven't had time to atrophy yet, so they can still respond to exogenous ACTH. For suspected recent secondary AI (e.g., post-pituitary surgery), consider insulin tolerance test or use low-dose (1 μg) cosyntropin. |\n"
            "| **Low-dose (1 μg) ACTH stimulation test** | Give **1 μg IV cosyntropin**. Measure cortisol at 30 min. | Same cut-off (≥ 18 μg/dL = normal) | More sensitive for partial / early secondary AI because the low dose doesn't overwhelm partially atrophied adrenals. Not universally standardized. |\n"
            "| **Insulin tolerance test (ITT)** | Administer regular insulin (0.1–0.15 U/kg IV) to induce hypoglycemia (glucose < 40 mg/dL). Measure cortisol at 0, 30, 60, 90 min. | **Peak cortisol ≥ 18 μg/dL** → intact HPA axis. | **Gold standard for secondary/tertiary AI** — tests the entire HPA axis. Contraindicated in seizure disorders, coronary artery disease, and elderly patients. Must be done with physician at bedside. |\n"
        )

        st.markdown(
            "\n**Step 2: Distinguish primary vs secondary/tertiary**\n\n"
            "| Test | Interpretation |\n"
            "| --- | --- |\n"
            "| **Plasma ACTH level** (drawn simultaneously with AM cortisol) | **ACTH > 2× upper limit of normal (often > 100 pg/mL) with low cortisol** → **Primary AI**. **ACTH low or inappropriately normal with low cortisol** → **Secondary or tertiary AI**. |\n"
            "| **Aldosterone & renin** | **Low aldosterone + high renin** → Primary AI (mineralocorticoid deficiency). **Normal aldosterone** → Secondary/tertiary (RAAS axis intact). |\n"
            "| **CRH stimulation test** | Give IV CRH → measure ACTH and cortisol. **ACTH rises but cortisol doesn't** → primary AI. **ACTH doesn't rise** → secondary (pituitary). **Exaggerated, delayed ACTH rise** → tertiary (hypothalamic). |\n"
            "| **DHEA-S** | Low in primary AI (adrenal androgen deficiency). Can be low in secondary AI as well. |\n"
        )

        st.markdown(
            "\n**Step 3: Identify the cause**\n\n"
            "| If Primary AI | Test |\n"
            "| --- | --- |\n"
            "| Autoimmune (most common in developed world) | **21-hydroxylase antibodies** (adrenal cortex antibodies). Positive in ~90% of autoimmune Addison disease. |\n"
            "| Infectious | TB — chest X-ray, PPD/IGRA. CT abdomen may show adrenal calcifications (chronic TB) or enlargement (acute). |\n"
            "| Hemorrhage / infarction | CT abdomen — bilateral adrenal hemorrhage. Think DIC, anticoagulation, HIT, meningococcemia (Waterhouse-Friderichsen). |\n"
            "| Infiltrative / metastatic | CT or MRI abdomen. Common primary sites: lung, breast, melanoma, renal, lymphoma. |\n"
            "| Adrenoleukodystrophy | Very long chain fatty acids (VLCFA). Consider in young males with primary AI + neurological symptoms. |\n"
            "\n"
            "| If Secondary / Tertiary AI | Test |\n"
            "| --- | --- |\n"
            "| Exogenous glucocorticoid use | Medication history — most common cause. Any dose ≥ prednisone 5 mg/day (or equivalent) for > 3 weeks can suppress the HPA axis. |\n"
            "| Pituitary lesion | MRI pituitary with gadolinium. Check other pituitary axes (TSH, FSH/LH, GH, prolactin). |\n"
            "| Sheehan syndrome | History of postpartum hemorrhage + failure to lactate. |\n"
        )

        st.divider()
        st.subheader("Adrenal Crisis")
        st.markdown(
            "| Feature | Details |\n"
            "| --- | --- |\n"
            "| **Triggers** | Physiologic stress (infection, surgery, trauma) in a patient with undiagnosed AI or who did not increase glucocorticoid dose. Abrupt discontinuation of chronic steroids. |\n"
            "| **Presentation** | Severe hypotension/shock refractory to fluids and vasopressors, nausea/vomiting, abdominal pain, altered mental status, fever, hypoglycemia. |\n"
            "| **Immediate management** | **Do NOT wait for test results.** Draw cortisol and ACTH, then give **hydrocortisone 100 mg IV bolus** immediately, followed by **50 mg IV q8h** (or 200 mg/24h continuous infusion). Aggressive IV normal saline resuscitation. Dextrose for hypoglycemia. |\n"
            "| **Why hydrocortisone?** | At stress doses (≥ 50 mg), hydrocortisone provides sufficient mineralocorticoid activity — no need for separate fludrocortisone during acute crisis. |\n"
            "| **Steroid taper** | Once stable, taper to oral maintenance over 1–3 days (typically hydrocortisone 15–25 mg/day in divided doses). Add fludrocortisone (0.05–0.2 mg/day) for primary AI once hydrocortisone dose < 50 mg/day. |\n"
        )

        st.divider()
        st.subheader("Maintenance Therapy")
        st.markdown(
            "| Component | Primary AI | Secondary / Tertiary AI |\n"
            "| --- | --- | --- |\n"
            "| **Glucocorticoid replacement** | Hydrocortisone 15–25 mg/day in 2–3 divided doses (e.g., 10 mg AM, 5 mg afternoon, 5 mg evening) — mimicking the diurnal cortisol rhythm. Alternatively: prednisone 3–5 mg/day or dexamethasone 0.25–0.5 mg/day. | Same |\n"
            "| **Mineralocorticoid replacement** | **Fludrocortisone 0.05–0.2 mg/day** — essential in primary AI. Titrate to normalize BP, K⁺, and renin. | **Not needed** (aldosterone is preserved via intact RAAS). |\n"
            "| **Sick-day rules** | Double or triple glucocorticoid dose during febrile illness, vomiting, procedures. IM/IV hydrocortisone if unable to take PO. | Same |\n"
            "| **Medical alert** | Patients should wear a medical alert bracelet/necklace and carry an emergency hydrocortisone injection kit. | Same |\n"
            "| **Monitoring** | Clinical assessment (energy, weight, BP, electrolytes). **Do not monitor with cortisol levels** — dose by symptoms. Check renin to guide fludrocortisone in primary AI. | Same (minus fludrocortisone monitoring) |"
        )
