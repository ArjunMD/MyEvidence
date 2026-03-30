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

