import streamlit as st

from ui_pages.rrt_meds_data import MED_POINT_FIELDS, PHYSICAL_EXAM_GUIDE

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
    st.title("🩺 Bedside")
    st.caption(
        "Bedside examination references. Use clinical judgment and institutional guidelines."
    )

    for section_name, section_data in PHYSICAL_EXAM_GUIDE.items():
        with st.expander(section_name, expanded=False):
            blocks = []
            items = section_data.get("medications") or []
            for item in items:
                name = str(item.get("name") or "").strip() or "Item"
                if str(item.get("item_type") or "").strip().lower() == "procedure":
                    blocks.append(_build_procedure_block(name, item))
                else:
                    blocks.append(_build_medication_block(name, item))
            if blocks:
                st.markdown("\n\n".join(blocks))

            # --- Spinal levels reference (Neuro Exams only) ---
            if section_name == "Neuro Exams":
                st.markdown("---")
                st.markdown(
                    "### Spinal Levels\n\n"
                    "| Root | Motor | Sensory | Reflex |\n"
                    "| --- | --- | --- | --- |\n"
                    "| **C5** | Deltoid, biceps (shoulder abduction, elbow flexion) | Lateral arm (regimental badge area) | Biceps |\n"
                    "| **C6** | Wrist extensors, brachioradialis | Lateral forearm, thumb & index finger | Brachioradialis |\n"
                    "| **C7** | Triceps, wrist flexors, finger extensors | Middle finger | Triceps |\n"
                    "| **C8** | Finger flexors (FDP), hand intrinsics | Medial forearm, ring & little finger | — |\n"
                    "| **T1** | Hand intrinsics (interossei, lumbricals) | Medial arm | — |\n"
                    "| **T4** | — | Nipple line | — |\n"
                    "| **T10** | — | Umbilicus | — |\n"
                    "| **L2** | Hip flexion (iliopsoas) | Anterior thigh | — |\n"
                    "| **L3** | Knee extension (quadriceps) | Medial knee | — |\n"
                    "| **L4** | Ankle dorsiflexion (tibialis anterior) | Medial malleolus | Patellar |\n"
                    "| **L5** | Great toe extension (EHL), hip abduction | Dorsum of foot, first web space | — |\n"
                    "| **S1** | Ankle plantarflexion (gastrocnemius), hip extension | Lateral foot, sole | Achilles |\n"
                    "| **S2–S4** | Anal sphincter tone | Perianal saddle area | Bulbocavernosus, anal wink |"
                )
                st.markdown("---")
                st.markdown(
                    "### ASIA Impairment Scale (AIS)\n\n"
                    "| Grade | Classification | Definition |\n"
                    "| --- | --- | --- |\n"
                    "| **A** | Complete | No sensory or motor function preserved in S4–S5 |\n"
                    "| **B** | Sensory incomplete | Sensory but no motor function preserved below the neurological level, includes S4–S5 |\n"
                    "| **C** | Motor incomplete | Motor function preserved below the neurological level; more than half of key muscles below the level have a grade < 3 |\n"
                    "| **D** | Motor incomplete | Motor function preserved below the neurological level; at least half of key muscles below the level have a grade ≥ 3 |\n"
                    "| **E** | Normal | Sensory and motor function are normal |\n"
                    "\n"
                    "**Key points:**\n"
                    "- Neurological level = most caudal level with normal motor and sensory function bilaterally\n"
                    "- Sacral sparing (S4–S5 sensation, deep anal pressure, or voluntary anal contraction) distinguishes incomplete (B/C/D) from complete (A)\n"
                    "- B vs C/D: any voluntary motor function below the level → at least C\n"
                    "- C vs D: test key muscles below the injury — if ≥ half grade 3+, it is D"
                )
                st.markdown("---")
                st.markdown(
                    "### Incomplete Spinal Cord Syndromes\n\n"
                    "| Syndrome | Mechanism | Motor | Sensory | Prognosis |\n"
                    "| --- | --- | --- | --- | --- |\n"
                    "| **Central cord** | Hyperextension (often elderly with stenosis) | Upper extremities worse than lower (\"man in a barrel\"); hands most affected | Variable; pain/temp may be impaired in a cape distribution | Best prognosis of incomplete syndromes; legs recover first, then bladder, then arms; hands recover last |\n"
                    "| **Anterior cord** | Flexion injury, anterior spinal artery occlusion, or aortic surgery | Bilateral motor paralysis below the level | Loss of pain and temperature bilaterally; dorsal columns spared (intact proprioception, vibration, light touch) | Worst prognosis of incomplete syndromes |\n"
                    "| **Brown-Séquard** (cord hemisection) | Penetrating trauma, lateral mass lesion | Ipsilateral motor paralysis below the level | Ipsilateral loss of proprioception/vibration; contralateral loss of pain/temp (1–2 levels below) | Good prognosis; most patients regain ambulatory function |\n"
                    "| **Posterior cord** | Rare; hyperextension, posterior spinal artery occlusion, B12 deficiency, tabes dorsalis | Motor preserved | Loss of proprioception, vibration, and light touch bilaterally; pain/temp preserved | Generally good motor prognosis; ataxia can be disabling |\n"
                    "| **Conus medullaris** (S3–S5 / conus) | Fracture at T12–L1 | Symmetric lower motor neuron pattern; early bladder/bowel/sexual dysfunction | Perianal saddle anesthesia | Recovery variable; bladder dysfunction often permanent |\n"
                    "| **Cauda equina** (nerve roots below conus) | Large central disc herniation, tumor, epidural abscess | Asymmetric, flaccid LMN pattern; areflexic | Asymmetric saddle anesthesia; radicular pain common | Surgical emergency; prognosis depends on speed of decompression |"
                )

    with st.expander("Ventilator Dyssynchrony", expanded=False):
        st.markdown(
            "Ventilator dyssynchrony occurs when the patient's respiratory effort "
            "and the ventilator's delivery of breaths are mismatched in timing, flow, "
            "or volume. It increases work of breathing, causes patient distress, "
            "worsens gas exchange, and can contribute to ventilator-induced lung injury (VILI).\n\n"
            "### Trigger Dyssynchrony\n\n"
            "| Type | What Happens | Waveform Clues | Management |\n"
            "| --- | --- | --- | --- |\n"
            "| **Ineffective triggering (missed triggers)** | Patient effort does not trigger a breath — the ventilator ignores the effort | Negative deflection on pressure waveform or flow deflection toward zero without a delivered breath; airway pressure dip without a corresponding volume delivery | Increase trigger sensitivity (lower pressure trigger or increase flow trigger sensitivity); reduce over-assistance that causes hyperinflation; reduce auto-PEEP by increasing expiratory time |\n"
            "| **Auto-triggering** | Ventilator delivers a breath without patient effort — false trigger | Breaths delivered at regular intervals without preceding patient effort; may correlate with cardiac oscillations, circuit leak, or water in tubing | Decrease trigger sensitivity; check for circuit leaks, water in tubing, or cardiac oscillations; ensure appropriate PEEP |\n"
            "| **Double triggering** | Two ventilator breaths delivered for a single patient effort — the second breath stacks on the first | Two consecutive breaths with very short expiratory time between them; the first breath appears truncated | Increase inspiratory time or tidal volume to match patient demand; consider increasing pressure support; may need to increase set Vt if patient demand exceeds delivery |\n"
            "| **Reverse triggering** | Ventilator breath triggers a reflexive diaphragmatic contraction (entrainment) — passive patient, often deeply sedated | Breath is ventilator-initiated, but a second effort (pressure dip or flow distortion) appears during or at end of the machine breath; can cause breath-stacking | Reduce sedation to allow spontaneous triggering; or deepen sedation to abolish entrainment; consider changing mode |\n\n"
            "### Flow Dyssynchrony\n\n"
            "| Type | What Happens | Waveform Clues | Management |\n"
            "| --- | --- | --- | --- |\n"
            "| **Flow starvation (insufficient flow)** | Patient's inspiratory demand exceeds the set flow rate — the ventilator cannot deliver gas fast enough | Concave (scooped-out) appearance of the pressure-time waveform during inspiration; patient appears to be \"sucking\" against the ventilator | Increase peak inspiratory flow rate; switch from volume-control to pressure-control (flow is variable and demand-matched); consider pressure support mode |\n"
            "| **Excessive flow** | Flow delivered is faster than the patient wants | Pressure overshoot or spike at the beginning of inspiration; convex (bulging) pressure waveform; patient may actively exhale against delivered flow | Decrease peak flow rate; switch to a decelerating flow pattern; consider pressure-targeted mode |\n\n"
            "### Cycle Dyssynchrony\n\n"
            "| Type | What Happens | Waveform Clues | Management |\n"
            "| --- | --- | --- | --- |\n"
            "| **Premature cycling (short inspiration)** | Ventilator terminates inspiration before the patient is done inhaling | Patient effort continues after the ventilator cycles to expiration — seen as a second negative pressure deflection or continued inspiratory flow after the machine cycles off; may cause double triggering | Increase inspiratory time (volume control) or decrease expiratory trigger sensitivity / cycle-off percentage (pressure support) |\n"
            "| **Delayed cycling (prolonged inspiration)** | Ventilator inspiration continues after the patient wants to exhale | Active expiratory effort against ongoing ventilator inspiration — pressure spike at end of inspiration; expiratory flow begins while the ventilator is still delivering | Decrease inspiratory time (volume control) or increase expiratory trigger sensitivity / cycle-off percentage (pressure support); check for circuit leaks that prevent flow from decaying to the cycle threshold |\n\n"
            "### Mode-Related Dyssynchrony\n\n"
            "| Type | What Happens | Waveform Clues | Management |\n"
            "| --- | --- | --- | --- |\n"
            "| **Breath-stacking (auto-PEEP)** | Incomplete exhalation before the next breath — air trapping raises end-expiratory pressure | Expiratory flow does not return to zero before the next breath begins; progressive increase in plateau pressure; perform an expiratory hold to measure auto-PEEP | Decrease respiratory rate; decrease I:E ratio (shorten inspiration, lengthen expiration); reduce tidal volume; bronchodilators if obstructive; apply external PEEP to ~80% of measured auto-PEEP to reduce trigger threshold |\n\n"
            "### Systematic Approach at the Bedside\n\n"
            "1. **Look at the patient**: accessory muscle use, paradoxical breathing, diaphoresis, tachycardia, agitation\n"
            "2. **Look at the waveforms**: pressure-time, flow-time, and volume-time — most dyssynchrony is visible on these\n"
            "3. **Identify the phase**: is the problem in triggering, flow delivery, or cycling?\n"
            "4. **Intervene on the ventilator first**: adjust trigger, flow, inspiratory time, or mode before reaching for sedation\n"
            "5. **Sedation is not the first-line treatment for dyssynchrony** — fix the ventilator-patient mismatch. Sedation masks the problem and may worsen outcomes"
        )

    with st.expander("Medications Incompatible with Lactated Ringer's", expanded=False):
        st.markdown(
            "Lactated Ringer's contains **calcium (Ca²⁺)**, which is the primary "
            "source of incompatibility. Always verify with pharmacy references.\n\n"
            "| Medication | Reason |\n"
            "| --- | --- |\n"
            "| **Ceftriaxone** | Risk of calcium–ceftriaxone precipitate (especially neonates) |\n"
            "| **Phenytoin / Fosphenytoin** | Crystallizes in calcium/dextrose-containing solutions; use NS only |\n"
            "| **Sodium bicarbonate** | Forms calcium carbonate precipitate |\n"
            "| **Blood products (pRBCs, FFP, platelets)** | Ca²⁺ overwhelms citrate anticoagulant → microclots |\n"
            "| **Amphotericin B** | Incompatible with electrolyte-containing solutions |\n"
            "| **Diazepam** | Precipitates in most IV solutions including LR |\n"
            "| **Propofol** | Manufacturer advises against dilution with LR |\n"
            "| **Mannitol** | Can crystallize with electrolyte solutions |\n"
            "| **Aminocaproic acid** | Incompatible with LR |\n"
            "| **Metoclopramide** | Incompatible with calcium-containing solutions |\n"
            "| **Ampicillin / Ampicillin-sulbactam** | Accelerated degradation in LR |\n"
            "| **Nitroglycerin** | Stability issues with LR |\n"
            "| **TPN (total parenteral nutrition)** | Ca²⁺ interaction with phosphate → precipitate |"
        )
