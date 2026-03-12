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
