import streamlit as st


def render() -> None:
    st.title("📝 Cardiology")

    # ── Arterial Waveform ────────────────────────────────────────────
    with st.expander("Arterial Waveform", expanded=False):
        st.markdown("""
**Components of the Arterial Pressure Waveform**

| Component | Description |
|-----------|-------------|
| **Systolic upstroke (anacrotic limb)** | Rapid rise in pressure as the LV ejects blood into the aorta. Steepness reflects LV contractility and SVR. |
| **Systolic peak** | Maximum arterial pressure during ventricular ejection. |
| **Systolic decline** | Pressure falls as the rate of ventricular ejection slows. |
| **Dicrotic notch** | Brief upward deflection caused by aortic valve closure and elastic recoil of the aorta. Marks the end of systole and start of diastole. |
| **Diastolic runoff** | Gradual decline in pressure as blood flows to the periphery during diastole. |
| **End-diastolic pressure** | Lowest pressure before the next systolic upstroke. |

**Waveform Variations & Clinical Significance**

| Morphology | Condition |
|------------|-----------|
| *Pulsus parvus et tardus* (slow upstroke, low amplitude) | Aortic stenosis |
| *Water-hammer / Corrigan pulse* (wide pulse pressure, rapid rise and fall) | Aortic regurgitation, high-output states |
| *Pulsus bisferiens* (two systolic peaks) | Combined aortic stenosis + regurgitation, HOCM |
| *Pulsus alternans* (alternating strong and weak beats) | Severe LV systolic dysfunction |
| *Pulsus paradoxus* (> 10 mmHg drop in SBP with inspiration) | Cardiac tamponade, severe asthma, constrictive pericarditis |
| *Dampened waveform* (blunted upstroke, loss of dicrotic notch) | Catheter kink, thrombus, air bubble, or distal positioning |
| *Spike and dome* | HOCM (rapid initial ejection, then obstruction) |
""")

    # ── JVP Waveform ─────────────────────────────────────────────────
    with st.expander("JVP Waveform", expanded=False):
        st.markdown("""
**JVP Waveform Components**

| Wave / Descent | Timing | Mechanism | Abnormalities |
|----------------|--------|-----------|---------------|
| **a wave** | End of diastole (presystolic) | Right atrial contraction | **Giant a wave**: tricuspid stenosis, pulmonary HTN, pulmonary stenosis. **Cannon a wave**: AV dissociation (complete heart block, VT), atrium contracts against a closed tricuspid valve. **Absent a wave**: atrial fibrillation. |
| **c wave** | Early systole | Tricuspid valve bulges toward RA during isovolumetric contraction; carotid artery pulsation artifact | Rarely clinically significant. |
| **x descent** | Systole | RA relaxation + downward displacement of tricuspid annulus during RV contraction | **Attenuated**: tricuspid regurgitation (replaced by a systolic **cv wave**). |
| **v wave** | Late systole | Passive filling of RA against a closed tricuspid valve | **Giant v wave**: tricuspid regurgitation, ASD (increased RA volume loading). |
| **y descent** | Early diastole | Tricuspid valve opens → rapid RA emptying into RV | **Steep y descent**: constrictive pericarditis, severe TR. **Blunted y descent**: tricuspid stenosis, RA myxoma. |

**Key Clinical Patterns**

- **Kussmaul sign**: Paradoxical rise in JVP with inspiration → constrictive pericarditis, restrictive cardiomyopathy, RV infarction, severe RV failure.
- **Friedreich sign**: Prominent and rapid y descent → constrictive pericarditis.
- **Lancisi sign**: Prominent systolic (cv) wave replacing the x descent → severe tricuspid regurgitation.
- **Elevated JVP with absent pulsations**: SVC obstruction.
""")

    # ── Right Heart Catheterization ──────────────────────────────────
    with st.expander("Right Heart Catheterization Numbers", expanded=False):
        st.markdown("""
**Normal Hemodynamic Values**

| Parameter | Normal Range |
|-----------|-------------|
| **Right atrial pressure (RAP)** | 0 – 8 mmHg (mean) |
| **RV systolic pressure** | 15 – 30 mmHg |
| **RV diastolic pressure** | 0 – 8 mmHg |
| **PA systolic pressure** | 15 – 30 mmHg |
| **PA diastolic pressure** | 4 – 12 mmHg |
| **PA mean pressure (mPAP)** | 9 – 18 mmHg |
| **Pulmonary capillary wedge pressure (PCWP)** | 4 – 12 mmHg |
| **Cardiac output (CO)** | 4 – 8 L/min |
| **Cardiac index (CI)** | 2.5 – 4.0 L/min/m² |
| **Systemic vascular resistance (SVR)** | 800 – 1200 dynes·s/cm⁵ |
| **Pulmonary vascular resistance (PVR)** | 20 – 120 dynes·s/cm⁵ (< 3 Wood units) |
| **Mixed venous O₂ saturation (SvO₂)** | 60 – 80% |

**Key Formulas**

- **CO** = HR × SV
- **CI** = CO / BSA
- **SVR** = (MAP − RAP) / CO × 80
- **PVR** = (mPAP − PCWP) / CO × 80
- **Transpulmonary gradient (TPG)** = mPAP − PCWP (normal < 12 mmHg)
- **Diastolic pulmonary gradient (DPG)** = PA diastolic − PCWP (normal < 7 mmHg)

**Hemodynamic Profiles**

| Condition | RAP | PCWP | CO/CI | mPAP | PVR |
|-----------|-----|------|-------|------|-----|
| **Cardiogenic shock** | ↑ | ↑↑ | ↓↓ | ↑ | ↑ |
| **Hypovolemic shock** | ↓ | ↓ | ↓↓ | ↓ | Normal |
| **Distributive shock (sepsis)** | ↓/Normal | ↓/Normal | ↑ (early) or ↓ (late) | ↓/Normal | ↓ |
| **Obstructive shock (PE)** | ↑ | ↓/Normal | ↓↓ | ↑↑ | ↑↑ |
| **RV infarction** | ↑ (≥ 10, RAP/PCWP > 0.8) | Normal/↓ | ↓ | Normal/↓ | Normal |
| **Cardiac tamponade** | ↑ | ↑ (equalization: RAP ≈ PCWP ≈ RVDP) | ↓ | Normal/↑ | Normal |
| **Constrictive pericarditis** | ↑ | ↑ (equalization + dip-and-plateau / square root sign) | ↓ | Normal/↑ | Normal |
| **Precapillary PH (PAH)** | Normal/↑ | Normal (≤ 15) | ↓ | ↑ (> 20) | ↑ (> 2 WU) |
| **Postcapillary PH (LHD)** | ↑ | ↑ (> 15) | ↓ | ↑ | Normal |
| **Combined pre- & postcapillary PH** | ↑ | ↑ (> 15) | ↓ | ↑ | ↑ (PVR > 2 WU) |

**Pulmonary Hypertension Classification (per 2022 ESC/ERS)**

- **PH**: mPAP > 20 mmHg
- **Precapillary PH**: mPAP > 20, PCWP ≤ 15, PVR > 2 WU
- **Postcapillary PH**: mPAP > 20, PCWP > 15
  - *Isolated postcapillary*: PVR ≤ 2 WU
  - *Combined pre- & postcapillary*: PVR > 2 WU
""")

    # ── Echocardiography Acronyms & Measurements ───────────────────
    with st.expander("Echo Acronyms & Measurements", expanded=False):
        st.markdown(
            "### LV Systolic Function\n\n"
            "| Acronym / Term | Full Name | What It Measures | Normal Values | Clinical Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| **LVEF** | Left ventricular ejection fraction | % of LV end-diastolic volume ejected per beat | 52–72% (M), 54–74% (F) | Most widely used measure of systolic function. Load-dependent. Calculated by Simpson's biplane method. |\n"
            "| **GLS** | Global longitudinal strain | Peak longitudinal myocardial deformation (shortening) tracked by speckle-tracking echo | −18% to −22% (more negative = better; abnormal if less negative than −16%) | Detects subclinical systolic dysfunction when EF is still \"normal\" — invaluable in cardio-oncology (chemotherapy surveillance), HFpEF, amyloidosis, and early cardiomyopathy. Less load-dependent than EF. \"Apical sparing\" pattern (preserved apical strain with reduced basal/mid strain) is classic for cardiac amyloidosis. |\n"
            "| **FS** | Fractional shortening | % change in LV internal diameter (systole vs diastole) | 25–45% | M-mode measurement. Quick estimate of systolic function but assumes symmetric contraction. |\n"
            "| **MAPSE** | Mitral annular plane systolic excursion | Longitudinal descent of the mitral annulus toward the apex in systole | ≥ 10 mm | Simple M-mode measure of longitudinal LV function. < 10 mm suggests reduced systolic function. |\n"
            "| **S'** (s-prime) | Tissue Doppler systolic velocity | Peak systolic velocity of the mitral annulus | ≥ 6 cm/s (septal), ≥ 8 cm/s (lateral) | Reduced S' indicates impaired longitudinal systolic function even with preserved EF. |\n"
            "| **LVOT VTI** | LV outflow tract velocity-time integral | Distance blood travels through the LVOT per beat — a surrogate for stroke volume | 18–22 cm | VTI < 18 cm suggests low stroke volume. Used to calculate SV = LVOT area × VTI. Tracks hemodynamic response to fluids or inotropes. |\n"
            "| **SV** | Stroke volume | Volume ejected per beat | 60–100 mL | SV = LVOT area × LVOT VTI. |\n"
            "| **CO** | Cardiac output | Total volume ejected per minute | 4–8 L/min | CO = SV × HR. |\n"
            "\n---\n\n"
            "### LV Diastolic Function\n\n"
            "| Acronym / Term | Full Name | What It Measures | Normal Values | Clinical Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| **E wave** | Early mitral inflow velocity | Passive early diastolic filling across the mitral valve | Variable | Reflects LA-LV pressure gradient in early diastole. |\n"
            "| **A wave** | Atrial (late) mitral inflow velocity | Active filling from atrial contraction | Variable | Lost in atrial fibrillation. |\n"
            "| **E/A ratio** | E-to-A ratio | Relative contribution of passive vs active filling | 0.8–2.0 (age-dependent) | < 0.8 = impaired relaxation (Grade I). > 2.0 with short DT = restrictive filling (Grade III). |\n"
            "| **e'** (e-prime) | Early diastolic mitral annular velocity | Rate of myocardial relaxation (tissue Doppler) | ≥ 10 cm/s (septal), ≥ 12 cm/s (lateral) | Reduced e' indicates impaired relaxation. Relatively preload-independent. |\n"
            "| **E/e'** | E to e-prime ratio | Estimate of LV filling pressures | < 8 normal; > 14 elevated; 8–14 indeterminate | Best non-invasive surrogate for PCWP. E/e' > 14 suggests elevated filling pressures. |\n"
            "| **DT** | Deceleration time | Time from E-wave peak to baseline | 150–240 ms | < 150 ms = restrictive physiology (elevated LA pressure). > 240 ms = impaired relaxation. |\n"
            "| **IVRT** | Isovolumetric relaxation time | Time from aortic valve closure to mitral valve opening | 70–90 ms | Shortened in elevated LA pressure; prolonged in impaired relaxation. |\n"
            "| **TR Vmax** | Tricuspid regurgitation peak velocity | Peak velocity of the TR jet | < 2.8 m/s | Used to estimate RVSP = 4(TR Vmax)² + RAP. TR Vmax > 2.8 m/s suggests elevated filling pressures. |\n"
            "| **LAVI** | Left atrial volume index | LA volume indexed to BSA | < 34 mL/m² | Elevated LAVI reflects chronic diastolic burden (\"HbA1c of diastolic function\"). |\n"
            "\n"
            "**Diastolic Dysfunction Grading (2016 ASE/EACVI)**\n\n"
            "| Grade | Pattern | Key Features |\n"
            "| --- | --- | --- |\n"
            "| **I** | Impaired relaxation | E/A < 0.8, e' reduced, E/e' < 10, normal LA pressure |\n"
            "| **II** | Pseudonormal | E/A 0.8–2.0 with elevated E/e' (> 14), elevated LAVI, elevated TR Vmax |\n"
            "| **III** | Restrictive | E/A > 2.0, DT < 150 ms, elevated E/e'. May be reversible (IIIa) or fixed (IIIb) |\n"
            "\n---\n\n"
            "### RV Function\n\n"
            "| Acronym / Term | Full Name | What It Measures | Normal Values | Clinical Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| **TAPSE** | Tricuspid annular plane systolic excursion | Longitudinal descent of tricuspid annulus in systole | ≥ 17 mm | Most commonly used simple measure of RV systolic function. < 17 mm = RV dysfunction. |\n"
            "| **RV S'** | RV tissue Doppler systolic velocity | Peak systolic velocity of the tricuspid annulus | ≥ 10 cm/s | Complements TAPSE; < 10 cm/s suggests RV dysfunction. |\n"
            "| **RVFAC** | RV fractional area change | % change in RV area (end-diastole to end-systole) | ≥ 35% | 2D planimetric measure of RV function. < 35% = RV dysfunction. |\n"
            "| **RVSP** | RV systolic pressure | Estimated RV/PA systolic pressure | < 35 mmHg | RVSP = 4(TR Vmax)² + RAP. Elevated in pulmonary hypertension, PE, and RV failure. |\n"
            "| **RV GLS** | RV global longitudinal strain | RV free wall longitudinal deformation | > −20% (more negative = better) | Emerging measure; detects subclinical RV dysfunction. |\n"
            "\n---\n\n"
            "### Valvular Assessment\n\n"
            "| Acronym / Term | Full Name | What It Measures | Clinical Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| **AVA** | Aortic valve area | Planimetered or calculated (continuity equation) valve orifice area | Severe AS: AVA < 1.0 cm² (indexed < 0.6 cm²/m²). |\n"
            "| **Vmax** | Peak aortic jet velocity | Maximum velocity across the aortic valve | Severe AS: Vmax ≥ 4.0 m/s. |\n"
            "| **Mean PG** | Mean pressure gradient | Average transvalvular gradient across the valve | Severe AS: mean PG ≥ 40 mmHg. Low-flow low-gradient AS: mean PG < 40 with reduced AVA — dobutamine stress echo to differentiate true vs pseudo-severe. |\n"
            "| **DVI** | Dimensionless velocity index | LVOT Vmax / AV Vmax (ratio of velocities) | < 0.25 suggests severe AS. Useful when LVOT diameter is difficult to measure. |\n"
            "| **MVA** | Mitral valve area | Mitral valve orifice area by planimetry or PHT method | Severe MS: MVA < 1.0 cm². |\n"
            "| **PHT** | Pressure half-time | Time for the transmitral gradient to halve | MVA = 220 / PHT. Used for MS severity and prosthetic MV assessment. |\n"
            "| **EROA** | Effective regurgitant orifice area | Orifice area of regurgitant flow (by PISA method) | Severe MR: EROA ≥ 0.4 cm² (primary) or ≥ 0.2 cm² (secondary). Severe AR: EROA ≥ 0.3 cm². |\n"
            "| **RVol** | Regurgitant volume | Volume of regurgitant flow per beat | Severe MR: RVol ≥ 60 mL. Severe AR: RVol ≥ 60 mL. |\n"
            "| **RF** | Regurgitant fraction | % of stroke volume that regurgitates | Severe: RF ≥ 50%. |\n"
            "| **PISA** | Proximal isovelocity surface area | Hemispheric flow convergence zone proximal to the regurgitant orifice | Used to calculate EROA and RVol. PISA radius ≥ 9 mm (at Nyquist 40 cm/s) suggests severe MR. |\n"
            "| **Vena contracta** | Narrowest width of the regurgitant jet | Width of the jet at or just downstream of the orifice | Severe MR: ≥ 7 mm. Severe AR: ≥ 6 mm. Severe TR: ≥ 7 mm. |\n"
            "\n---\n\n"
            "### Other Common Echo Acronyms\n\n"
            "| Acronym | Full Name | Notes |\n"
            "| --- | --- | --- |\n"
            "| **TTE** | Transthoracic echocardiogram | Standard non-invasive echo. |\n"
            "| **TEE** | Transesophageal echocardiogram | Superior for posterior structures (LA, LAA, mitral valve, aorta). Required for endocarditis vegetations, LAA thrombus, prosthetic valve assessment. |\n"
            "| **IVSd** | Interventricular septum thickness in diastole | Normal < 11 mm. Increased in LVH, HCM, infiltrative cardiomyopathy. |\n"
            "| **LVIDd / LVIDs** | LV internal diameter in diastole / systole | LVIDd normal: 3.5–5.7 cm (M), 3.5–5.2 cm (F). Dilated LV suggests volume overload or DCM. |\n"
            "| **LVPWd** | LV posterior wall thickness in diastole | Normal < 11 mm. Increased in LVH. |\n"
            "| **RWT** | Relative wall thickness | (2 × LVPWd) / LVIDd. > 0.42 = concentric geometry; ≤ 0.42 = eccentric geometry. |\n"
            "| **LV mass index** | LV mass indexed to BSA | Normal: < 95 g/m² (F), < 115 g/m² (M). Elevated = LVH. |\n"
            "| **IVC** | Inferior vena cava diameter & collapsibility | IVC < 2.1 cm with > 50% collapse → RAP ~3 mmHg. IVC > 2.1 cm with < 50% collapse → RAP ~15 mmHg. |\n"
            "| **EPSS** | E-point septal separation | Distance from the anterior mitral leaflet E-point to the septum | > 7 mm suggests reduced EF (quick screening measure). |\n"
            "| **SAM** | Systolic anterior motion (of the mitral valve) | Anterior mitral leaflet moves toward the septum in systole | Hallmark of HOCM causing dynamic LVOT obstruction and often MR. |\n"
            "| **dP/dt** | Rate of LV pressure rise | Measured from the MR CW Doppler signal (time from 1 to 3 m/s) | < 1200 mmHg/s suggests severely reduced contractility. |"
        )

    # ── Cardiac Localization ────────────────────────────────────────
    with st.expander("Localization (ECG → Artery → Wall → Echo View)", expanded=False):
        st.subheader("ECG Leads → Coronary Artery → Ventricular Wall → Echo View")
        st.markdown(
            "| ECG Leads | Territory | Coronary Artery | Ventricular Wall | Echo / POCUS View |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| **V1–V2** | Septal | LAD (septal perforators) | Interventricular septum (basal & mid) | PLAX (septum is anterior structure), PSAX (anterior septum at all levels), A4C (septal wall) |\n"
            "| **V3–V4** | Anterior | LAD (mid-to-distal) | Anterior wall (mid & apical) | PLAX (anterior/posterior orientation), PSAX mid-level (anterior wall), A2C (anterior wall), A4C (apex) |\n"
            "| **V5–V6, I, aVL** | Lateral | LCx (or diagonal branches of LAD) | Lateral wall | A4C (lateral wall), PSAX (posterolateral wall), A2C (sometimes lateral segments) |\n"
            "| **II, III, aVF** | Inferior | RCA (85%, right-dominant) or LCx (15%, left-dominant) | Inferior wall | A2C (inferior wall), PSAX (inferior wall), Subcostal 4-chamber (inferior wall faces transducer) |\n"
            "| **V1–V4 (ST depression = posterior reciprocal)** | Posterior | RCA (posterior descending) or LCx | Posterior (inferobasal) wall | PLAX (posterior wall), PSAX basal level (posterior/inferior segments) |\n"
            "| **V1–V2 (tall R, ST depression) ± posterior leads V7–V9 (ST elevation)** | Posterior (true posterior MI) | RCA or LCx | Posterior (inferobasal) wall | PLAX (posterior wall — look for new WMA), PSAX basal level |\n"
            "| **V3R–V4R (ST elevation)** | Right ventricle | Proximal RCA | RV free wall | RV-focused A4C (RV dilation, reduced TAPSE), Subcostal 4-chamber, PSAX (RV dilation/septal bowing) |\n"
            "| **aVR (ST elevation)** | Left main / diffuse subendocardial | Left main or severe multi-vessel disease | Global (circumferential subendocardial ischemia) | Diffuse hypokinesis on all views; often global LV dysfunction |\n"
        )

        st.divider()
        st.subheader("Coronary Artery Territories — Detailed Mapping")
        st.markdown(
            "| Coronary Artery | Branches | Walls Supplied | Key Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| **LAD** | Septal perforators, diagonals | Anterior wall, anterior septum, apex | Proximal LAD occlusion → extensive anterior STEMI (\"widow-maker\"). Wraps around apex in many patients, so apical inferior segments may also be LAD territory. |\n"
            "| **LCx** | Obtuse marginals (OM1, OM2) | Lateral wall, posterolateral wall, inferior wall (if left-dominant) | LCx MI often electrically \"silent\" — lateral ST changes may be subtle. Posterior/lateral WMA on echo may be the first clue. |\n"
            "| **RCA** | Acute marginal, PDA (right-dominant), posterolateral branch | Inferior wall, posterior wall, RV, AV node (in right-dominant) | Inferior STEMI + complete heart block → proximal RCA. Inferior STEMI + RV involvement (V3R–V4R elevation) → proximal RCA. Avoid nitrates and volume depletion in RV infarct. |\n"
            "| **Ramus intermedius** | — | Anterolateral wall | Present in ~15–20% of patients (trifurcation anatomy). Behaves like a diagonal or OM functionally. |\n"
        )

        st.divider()
        st.subheader("POCUS / Echo Views — What You See")
        st.markdown(
            "| View | Abbreviation | Walls Visualized | Best For |\n"
            "| --- | --- | --- | --- |\n"
            "| **Parasternal long axis** | PLAX | Anterior septum (basal–mid), posterior (inferolateral) wall | LAD & LCx territory WMA. Pericardial effusion. Aortic root. LV dimensions. |\n"
            "| **Parasternal short axis (basal)** | PSAX-base | All basal segments in cross-section (anterior, anteroseptal, inferoseptal, inferior, inferolateral, anterolateral) | Localizing WMA to a specific territory. RV size relative to LV. |\n"
            "| **Parasternal short axis (mid/papillary)** | PSAX-mid | All mid-level segments | Best single view for territory localization — all 3 coronary territories represented. |\n"
            "| **Parasternal short axis (apical)** | PSAX-apex | Apical segments (usually LAD territory) | Apical WMA, LV apical thrombus (limited). |\n"
            "| **Apical 4-chamber** | A4C | Septum (LAD), lateral wall (LCx), apex (LAD), RV free wall (RCA) | Comparing LV vs RV size, TAPSE, global LV function, apical WMA, pericardial effusion. |\n"
            "| **Apical 2-chamber** | A2C | Anterior wall (LAD), inferior wall (RCA/LCx) | Inferior and anterior WMA — directly compares LAD vs RCA/LCx territories. |\n"
            "| **Apical 3-chamber (apical long axis)** | A3C / ALAx | Anteroseptal wall (LAD), posterolateral wall (LCx) | Similar orientation to PLAX but from the apex; better Doppler alignment for aortic valve. |\n"
            "| **Subcostal 4-chamber** | SC4C | Inferior wall (faces transducer), septum, RV free wall | Best view when parasternal/apical windows are poor (COPD, ventilated). Inferior wall WMA. RV assessment. Pericardial effusion. |\n"
            "| **Subcostal IVC** | SC-IVC | IVC diameter & collapsibility | RAP estimation. Volume status. |\n"
        )

        st.divider()
        st.subheader("Quick Localization Reference")
        st.markdown(
            "| Wall Motion Abnormality On Echo | Think This Artery | Confirm With These ECG Leads |\n"
            "| --- | --- | --- |\n"
            "| Septal hypokinesis / akinesis | LAD (septal perforators) | V1–V2 |\n"
            "| Anterior wall akinesis | LAD (mid/distal) | V3–V4 |\n"
            "| Apical akinesis / aneurysm | LAD (distal, wrap-around) | V3–V6 (often with persistent ST elevation if aneurysm) |\n"
            "| Lateral wall hypokinesis | LCx (obtuse marginals) | I, aVL, V5–V6 |\n"
            "| Inferior wall akinesis | RCA (85%) or LCx (15%) | II, III, aVF |\n"
            "| Posterior wall akinesis (seen in PLAX/PSAX) | RCA (PDA) or LCx | Reciprocal ST depression V1–V3; ST elevation in V7–V9 |\n"
            "| RV dilation + free wall hypokinesis (McConnell sign) | Proximal RCA | V3R–V4R ST elevation; often with inferior ST elevation |\n"
            "| Global hypokinesis (all walls) | Left main or multi-vessel disease | aVR ST elevation with diffuse ST depression |"
        )
