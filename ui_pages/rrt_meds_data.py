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
}
