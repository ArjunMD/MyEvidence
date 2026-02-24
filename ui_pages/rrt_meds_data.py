from typing import Dict, List, Tuple

MED_POINT_FIELDS: List[Tuple[str, str]] = [
    ("dose", "Dose"),
    ("onset_peak_duration", "Pharmacokinetics"),
    ("mechanism", "Mechanism"),
    ("contra", "Contraindications / cautions"),
    ("side_effects", "Side effects"),
    ("fun_fact", "Fun fact"),
]

RRT_MED_GUIDE: Dict[str, Dict[str, object]] = {
    "Bradycardia": {
        "medications": [
            {
                "name": "Atropine",
                "item_type": "medication",
                "dose": "1 mg IV bolus every 3-5 minutes; max cumulative dose 3 mg.",
                "onset_peak_duration": "Onset 1 minute; peak 2-4 minutes; duration 30-60 minutes.",
                "mechanism": "Antimuscarinic (vagolytic): blocks cardiac muscarinic receptors, which increases SA node firing and AV nodal conduction; minimal direct contractility effect.",
                "contra": "May worsen Mobitz II or CHB with wide QRS. Contraindicated after cardiac transplant (asystole). Use caution in acute coronary syndrome.",
                "fun_fact": "The name comes from Atropa belladonna (Nightshade); Belladonna named because Cleopatra used the eye drops for pupil dilation as a beauty product.",
            },
            {
                "name": "Temporary pacing (transcutaneous/transvenous)",
                "item_type": "procedure",
                "summary": "Start transcutaneous pacing immediately while preparing medications.",
                "steps": [
                    "Set a backup rate (commonly 60-80/min), then increase mA until electrical capture is seen.",
                    "Confirm mechanical capture with pulse/BP or bedside ultrasound, not ECG alone.",
                    "If transcutaneous capture is unreliable or prolonged support is needed, escalate to transvenous pacing.",
                ],
                "cautions": "Pain and muscle contraction are common; provide analgesia/sedation when blood pressure allows. Re-check capture frequently.",
            },
            {
                "name": "Epinephrine infusion",
                "item_type": "medication",
                "dose": "2-10 mcg/min IV infusion; in peri-arrest some teams start at 10 mcg/min and then down-titrate.",
                "onset_peak_duration": "Onset under 1 minute; peak effect within minutes; duration is brief and highly titratable while running.",
                "mechanism": "Alpha and beta agonist: acts on the whole heart, unlike atropine, making it more likely to be successful.",
                "contra": "None.",
                "comments": "If epinephrine not available, put a vial of cardiac epinephrine in 1L NS, mix the bag, and run it at 120 mL/hr - 600 ml/hr to approximate 2-10 mcg/min.",
            },
            {
                "name": "Calcium",
                "item_type": "medication",
                "dose": "1g CaCl (CVC) or 3g CaGluc (PIV). If HyperK can consider redosing. iSTAT might be helpful.",
                "comments": "Calcium-responsive bradycardias: HyperK, HypoCa, HyperMg, CCB, BB",
            },
        ],
    },
    "Active Ongoing Seizure": {
        "medications": [
            {
                "name": "Lorazepam",
                "item_type": "medication",
                "dose": "4 mg IV over 2 minutes; may repeat once in 5-10 minutes. 0.1 mg/kg, maximum rate 2 mg/min is also okay.",
                "onset_peak_duration": "Onset 1-3 minutes IV; peak 5-15 minutes; anticonvulsant effect usually several hours.",
            },
            {
                "name": "Midazolam (if no IV)",
                "item_type": "medication",
                "dose": "10 mg IM once (or 10 mg IN/IV).",
                "onset_peak_duration": "IM onset about 5-10 minutes (faster IV/IN).",
            },
            {
                "name": "Levetiracetam",
                "item_type": "medication",
                "dose": "If seizures still present, give 60 mg/kg, max 4500 mg, infuse over 10 minutes.",
                "comments": "Give it whenever it arrives but move on to next steps.",
            },
            {
                "name": "D50",
                "item_type": "medication",
                "comments": "Don't forget to check glucose",
            },
            {
                "name": "Hypertonic sodium bicarbonate",
                "item_type": "medication",
                "dose": "2 ampules (100 mEq) of 1 mEq/ml concentration",
                "comments": "Hyponatremia is an uncommon cause of seizures but needs immediate treatment if present",
            },
            {
                "name": "Thiamine",
                "item_type": "medication",
                "comments": "Known cause of seizures. When in doubt. OK to give.",
            },
            {
                "name": "Ketamine",
                "item_type": "medication",
                "dose": "1 mg/kg slow IV push over 2 minutes",
                "comments": "When you are thinking about ketamine you are in intubation territory. Call for propofol gtt or midazolam bolus + gtt, paralytic, and norepinephrine",
            },
        ],
    },
    "Code Stroke": {
    "medications": [
        {
            "name": "Immediate steps",
            "item_type": "procedure",
            "steps": [
                "Check fingerstick glucose (treat hypoglycemia first before continuing).",
                "Determine Last Known Well (clock time), onset pattern (sudden vs stuttering), wake-up/unknown onset, and any seizure at onset.",
                "Determine baseline functional status and pre-stroke mRS (modified Rankin Scale)",
                "Focused neuro exam + NIHSS + disabling deficits.",
                "Establish IV access. Obtain weight for thrombolytic dosing.",
                "Draw labs (do not delay imaging): CBC, CMP, PT/INR, aPTT; troponin; pregnancy test if applicable.",
                "Baseline ECG and troponin are recommended but should NOT delay IV thrombolysis if otherwise eligible.",
                "Review meds (anticoagulants/antiplatelets), bleeding history, recent stroke/head trauma/surgery, and BP control feasibility.",
            ],
        },
        {
            "name": "LVO patterns (clinical clues)",
            "item_type": "procedure",
            "steps": [
                "Anterior circulation clues: forced gaze deviation, aphasia, neglect, homonymous field cut, dense unilateral weakness.",
                "Posterior circulation clues: depressed consciousness, diplopia, dysarthria, ataxia, 'crossed' deficits; consider basilar occlusion even with modest NIHSS.",
                "If high suspicion for LVO → CTA head/neck early; do not rely on NIHSS alone.",
            ],
        },

        {
            "name": "NIHSS (0–42)",
            "item_type": "procedure",
            "summary": "Perform early (baseline). Recheck with clinical changes.",
            "steps": [
                "1a LOC (0–3): 0 alert; 1 arousable to minor stimulation; 2 needs repeated/strong stimulation; 3 unresponsive/flaccid.",
                "1b Month + Age (0–2): 0 both correct; 1 one correct; 2 neither.",
                "1c 'Blink eyes' + 'Squeeze hands' (0–2): 0 both; 1 one; 2 neither.",
                "2 Horizontal gaze (0–2): 0 normal; 1 partial gaze palsy; 2 forced deviation/complete palsy not overcome by oculocephalic maneuver.",
                "3 Visual fields (0–3): 0 none; 1 partial hemianopia; 2 complete hemianopia; 3 bilaterally blind/hemianopia",
                "4 Facial palsy (can use grimace) (0–3): 0 normal; 1 minor; 2 partial (lower face); 3 complete (no upper/lower movement).",
                "5 Motor arm L/R (each 0–4): 0 no drift; 1 drift; 2 some effort vs gravity; 3 no effort vs gravity; 4 no movement.",
                "6 Motor leg L/R (each 0–4): 0 no drift; 1 drift; 2 some effort vs gravity; 3 no effort vs gravity; 4 no movement.",
                "7 Limb Ataxia (F2N/H2S) (0–2): 0 absent; 1 present in one limb; 2 present in two limbs.",
                "8 Sensory (0–2): 0 normal; 1 mild/moderate loss; 2 severe/total loss.",
                "9 Best language (describe, name items, read) (0–3): 0 none; 1 mild/moderate aphasia; 2 severe aphasia; 3 mute/global aphasia.",
                "10 Dysarthria (0–2): 0 normal; 1 mild/moderate; 2 severe/unintelligible or anarthric (UN if intubated/physical barrier).",
                "11 Extinction/inattention (0–2): 0 none; 1 extinction/inattention in one modality; 2 profound or >1 modality.",
            ],
            "cautions": "NIHSS can under-represent posterior circulation syndromes; document specific disabling deficits separately.",
        },

        {
            "name": "IV thrombolysis (alteplase / tenecteplase) — core eligibility & dosing",
            "item_type": "procedure",
            "steps": [
                "Core eligibility (typical): disabling ischemic stroke symptoms + treatable within 4.5 hours of last-known-well (or wake-up/unknown onset with appropriate imaging).",
                "Only blood glucose must precede IV thrombolysis; other labs/tests should not delay treatment unless anticoagulant use or concern for abnormality.",
            ],
        },

        {
            "name": "Thrombolysis contraindications (IV fibrinolytic) — typical AHA/ASA-based checklist",
            "item_type": "procedure",
            "summary": "Use your local inclusion/exclusion checklist; this is a commonly used operational list (absolute vs relative).",
            "steps": [
                "ABSOLUTE / DO NOT GIVE (typical):",
                "- Intracranial hemorrhage on CT or suspected SAH.",
                "- Extensive established infarct on CT (e.g., clear hypoattenuation >1/3 MCA territory).",
                "- Unable to maintain BP <185/110 despite treatment.",
                "- Ischemic stroke within the last 3 months.",
                "- History of intracranial hemorrhage.",
                "- Severe head trauma within the last 3 months.",
                "- Active internal bleeding (including suspected aortic dissection).",
                "- Arterial puncture at a non-compressible site within the last 7 days.",
                "- Infective endocarditis.",
                "- GI bleeding within last 21 days or structural GI malignancy.",
                "- Intracranial or spinal surgery within last 3 months.",
                "- Labs: glucose <50 mg/dL (treat first; if deficits persist after normalization, re-evaluate).",
                "- Labs (if indicated/known): INR >1.7; platelets <100,000; PT >15 sec; aPTT >40 sec.",
                "- Meds: full-dose LMWH within last 24 hours (prophylactic-dose LMWH is not an exclusion in many protocols).",
                "- Meds: DOAC ingestion within last 48 hours (assuming normal renal function) unless protocol allows drug-specific testing showing no clinically relevant activity.",
                "",
                "RELATIVE / DISCUSS WITH STROKE EXPERT (examples commonly used operationally):",
                "- Stroke too mild AND non-disabling (mild nondisabling deficits are generally not treated).",
                "- Prior IV/IA thrombolysis or thrombectomy at outside facility before arrival.",
                "- Major surgery or major trauma within 14 days (non-head).",
                "- Seizure at onset with postictal deficits and no evidence of stroke (consider imaging/clinical context).",
                "- MI within last 3 months; acute pericarditis.",
                "- Lumbar puncture within 7 days.",
                "- Past GI/GU bleeding history.",
                "- Pregnancy (case-by-case; risk/benefit).",
                "- Known intracranial lesion with higher bleeding risk (e.g., AVM, intracranial tumor; some protocols treat aneurysm >10 mm as higher risk).",
                "- Severe hyperglycemia >400 mg/dL (treat; if deficits persist after normalization, re-evaluate).",
            ],
        },

        {
            "name": "Blood pressure control (AIS reperfusion-focused)",
            "item_type": "procedure",
            "steps": [
                "If IV thrombolysis candidate: lower BP to <185/110 before bolus; maintain <180/105 for 24 hours after treatment.",
                "If mechanical thrombectomy planned and no IV lytic given: many pathways target ≤185/110 pre-procedure (double-check).",
                "If NOT a reperfusion candidate: permissive HTN is commonly allowed up to ~220/120 if no other indication to treat.",
                "If hemorrhage: BP goal < 160/110 is often recommended (double check)",
            ],
        },
    ],
},
}
