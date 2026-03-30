import streamlit as st


def render() -> None:
    st.title("📝 Pulm / Critical Care")

    # ── Ventilator Diagnosis & Troubleshooting ───────────────────────
    with st.expander("Ventilator Diagnosis & Troubleshooting", expanded=False):

        st.subheader("Air Trapping (Auto-PEEP / Intrinsic PEEP)")
        st.markdown("""
**What it is**: Incomplete exhalation before the next breath begins, causing progressive gas trapping and rising alveolar pressure above set PEEP.

**How to detect**
- Expiratory flow on the flow-time waveform **does not return to zero** before the next inspiration.
- Perform an **end-expiratory hold** — measured plateau (total PEEP) exceeds set PEEP. The difference is auto-PEEP.
- Rising peak and plateau pressures with decreasing tidal volumes (in pressure modes) or increasing pressures (in volume modes).

**Common causes**: Obstructive lung disease (COPD, asthma), high minute ventilation (high RR or high V_T), insufficient expiratory time, narrow / kinked ETT.

**Management**
- ↓ Respiratory rate → lengthen expiratory time.
- ↓ Tidal volume.
- ↑ Inspiratory flow rate (in volume control) → shortens I-time, lengthens E-time.
- ↓ I:E ratio.
- Bronchodilators if bronchospasm.
- Add extrinsic PEEP (up to ~80% of auto-PEEP) to reduce triggering work in spontaneously breathing patients.
""")

        st.divider()

        st.subheader("Breath Stacking (Double Triggering)")
        st.markdown("""
**What it is**: Two consecutive ventilator breaths delivered without a full exhalation in between, effectively doubling the delivered tidal volume.

**How to detect**
- Flow-time waveform shows two inspiratory efforts in rapid succession — the second breath fires before expiratory flow reaches zero.
- Pressure-time waveform shows two stacked pressure humps.
- V_T on the ventilator may read roughly double the set tidal volume.

**Common causes**
- Set inspiratory time is **too short** relative to the patient's neural inspiratory time → patient is still "pulling" when the vent cycles off, immediately triggering a second breath.
- High respiratory drive (pain, anxiety, metabolic acidosis).
- Reverse triggering (ventilator breath triggers a reflexive diaphragmatic contraction).

**Management**
- ↑ Set inspiratory time or ↓ flow rate (volume control) to better match patient demand.
- Switch to pressure support — patient controls cycle-off, reducing mismatch.
- Adjust trigger sensitivity (avoid over-sensitive triggers).
- Treat underlying drive (sedation, analgesia, correct acidosis).
- If reverse triggering: reduce sedation (to restore spontaneous breathing) or increase sedation (to suppress reflexive efforts), depending on clinical context.
""")

        st.divider()

        st.subheader("Air Leak")
        st.markdown("""
**What it is**: Loss of delivered gas volume from the circuit, resulting in a difference between inspiratory and expiratory tidal volumes.

**How to detect**
- **Expired V_T < Inspired V_T** — the vent displays a volume discrepancy.
- Flow-time waveform: expiratory flow does not return to baseline (trails off rather than reaching zero), similar in appearance to auto-PEEP but with **low** (not high) plateau pressures.
- Volume-time waveform: inspiratory and expiratory limbs do not meet — the expiratory limb falls short.
- Low-pressure or low-volume alarms.
- Audible cuff leak.

**Common causes**: ETT cuff deflation or rupture, circuit disconnection, loose connections, chest tube with bronchopleural fistula.

**Management**
- Check and inflate ETT cuff; measure cuff pressure (target 20–30 cmH₂O).
- Inspect all circuit connections.
- If persistent despite circuit check → consider cuff rupture (reintubate) or bronchopleural fistula.
- For bronchopleural fistula: minimize PEEP, consider independent lung ventilation.
""")

        st.divider()

        st.subheader("Flow Hunger (Inadequate Flow Delivery)")
        st.markdown("""
**What it is**: Patient inspiratory demand exceeds the flow delivered by the ventilator, causing patient distress and increased work of breathing.

**How to detect**
- **Pressure-time waveform (volume control)**: characteristic **"scooping" or concavity** during inspiration — the pressure dips below the expected linear or convex trajectory because the patient is pulling harder than the vent delivers.
- Patient appears to be "fighting" the vent: accessory muscle use, tachypnea, diaphoresis.
- Airway pressure may drop during inspiration rather than rising smoothly.

**Common causes**: Set inspiratory flow rate too low (volume control), high patient demand (pain, fever, acidosis, anxiety), inappropriate mode selection.

**Management**
- ↑ Peak inspiratory flow rate (in volume control) — start at 60 L/min, may need up to 80–100 L/min.
- Switch flow pattern from decelerating to square (delivers more flow early).
- Switch to a pressure-targeted mode (pressure control, pressure support) — these deliver variable flow to meet demand.
- Treat underlying cause of high demand.
""")

        st.divider()

        st.subheader("Flow-Volume Loops")
        st.markdown("""
Flow-volume loops plot **flow (Y-axis)** vs. **volume (X-axis)** in real time during a breath. Inspiration is typically above the X-axis, expiration below.

| Pattern | Appearance | Interpretation |
|---------|------------|----------------|
| **Normal** | Smooth oval loop; expiratory peak flow followed by gradual decline | Normal airway resistance and compliance |
| **Obstructive (air trapping)** | Expiratory limb is **concave / scooped** — flow drops off rapidly then tails | Airflow obstruction (COPD, asthma, secretions). Expiratory flow is effort-independent and limited by dynamic airway collapse. |
| **Fixed upper airway obstruction** | Both inspiratory and expiratory limbs are **flattened / truncated** at the same flow | Fixed obstruction (tracheal stenosis, tracheal tumor). Flow is capped in both directions. |
| **Variable extrathoracic obstruction** | **Inspiratory limb flattened**, expiratory limb normal | Vocal cord paralysis, extrathoracic mass. Negative intrathoracic pressure during inspiration collapses the lesion. |
| **Variable intrathoracic obstruction** | **Expiratory limb flattened**, inspiratory limb normal | Intrathoracic tracheal mass. Positive intrathoracic pressure during expiration compresses the lesion. |
| **Air leak** | Loop does not close — expiratory limb falls short of returning to origin | Volume lost through cuff leak or circuit disconnect |
| **Secretions / water in circuit** | **Sawtooth pattern** on expiratory limb | Secretions vibrating in airway or water in the circuit |
""")

        st.divider()

        st.subheader("Pressure-Volume Loops")
        st.markdown("""
Pressure-volume loops plot **volume (Y-axis)** vs. **pressure (X-axis)** during a breath. The loop rotates counterclockwise in positive-pressure ventilation.

| Feature | Description | Clinical Use |
|---------|-------------|--------------|
| **Lower inflection point (LIP)** | Pressure at which compliance sharply improves (alveolar recruitment begins) | Historically used to guide PEEP setting — set PEEP above LIP to keep alveoli open. |
| **Upper inflection point (UIP)** | Pressure at which compliance flattens (overdistension begins) | Keep plateau pressure below UIP to avoid volutrauma. |
| **Compliance (slope)** | Steeper slope = better compliance; flatter slope = stiffer lungs | ↓ Compliance: ARDS, pulmonary fibrosis, pulmonary edema, abdominal compartment syndrome. ↑ Compliance: emphysema. |
| **Hysteresis (loop width)** | Difference between inspiratory and expiratory limbs — wider = more energy lost to airway resistance | Increased hysteresis with high airway resistance (bronchospasm, secretions, narrow ETT). |
| **"Beaking" at top of loop** | Volume flattens while pressure keeps rising — the loop develops a rightward beak/tail at the top | **Overdistension** — V_T is too high. Reduce tidal volume. |
| **Clockwise loop at bottom** | Small clockwise component at the start of inspiration | Increased triggering work — patient effort to trigger the breath. May indicate inadequate trigger sensitivity or auto-PEEP. |

**Quick Reference: Loop Shape → Diagnosis**

| Loop Shape | Diagnosis |
|------------|-----------|
| Narrow, steep loop | Normal compliance, low resistance |
| Wide loop | High airway resistance |
| Flat, rightward-shifted loop | Low compliance (stiff lungs) |
| Beak / tail at top-right | Overdistension |
| Loop does not close | Air leak |
| Figure-of-eight crossing | Spontaneous breathing efforts during mandatory breaths (asynchrony) |
""")

