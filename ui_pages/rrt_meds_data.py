from typing import Dict, List, Tuple

MED_POINT_FIELDS: List[Tuple[str, str]] = [
    ("dose", "Dose"),
    ("onset_peak_duration", "Onset of action / peak effect / duration"),
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
                "onset_peak_duration": "Onset about 1 minute (IV); peak about 2-4 minutes; duration often about 30-60 minutes (can be longer in older adults).",
                "mechanism": "Antimuscarinic (vagolytic): blocks cardiac muscarinic receptors, which increases SA node firing and AV nodal conduction; minimal direct contractility effect.",
                "contra": "Skip in Mobitz II (Block is under bundle of HIS) or 3rd-degree AV block with wide QRS. Contraindicated after cardiac transplant (asystole risk). Avoid doses under 0.5 mg (paradoxical bradycardia risk). Use caution in narrow-angle glaucoma, urinary or GI obstruction, marked tachycardia, severe hypertension, and heat illness.",
                "side_effects": "Tachycardia, mydriasis/blurred vision, dry mouth, urinary retention, decreased GI motility/constipation, hyperthermia, and delirium (especially in older adults).",
                "fun_fact": "The name comes from Atropa belladonna; historical accounts link belladonna eye drops to pupil dilation, including stories about Cleopatra-era beauty practices.",
            },
            {
                "name": "Epinephrine infusion",
                "item_type": "medication",
                "dose": "2-10 mcg/min IV infusion; in peri-arrest some teams start at 10 mcg/min and then down-titrate.",
                "onset_peak_duration": "Onset under 1 minute; peak effect within minutes; duration is brief and highly titratable while running.",
                "mechanism": "Alpha and beta agonist: raises heart rate, contractility, and vascular tone to improve perfusion.",
                "contra": "No absolute contraindication in peri-arrest; use caution with active tachyarrhythmias, severe hypertension, and ongoing myocardial ischemia.",
                "side_effects": "Tachycardia, arrhythmias, hypertension, anxiety/tremor, hyperglycemia, elevated lactate, and peripheral ischemia (especially with high doses or extravasation).",
                "fun_fact": "Push-dose epinephrine boluses (for example 20-40 mcg) are often used as a bridge while an infusion is being started.",
            },
            {
                "name": "Temporary pacing (transcutaneous/transvenous)",
                "item_type": "procedure",
                "summary": "Start transcutaneous pacing immediately in unstable bradycardia while preparing medications and definitive pacing backup.",
                "steps": [
                    "Set a backup rate (commonly 60-80/min), then increase mA until electrical capture is seen.",
                    "Confirm mechanical capture with pulse/BP or bedside ultrasound, not ECG alone.",
                    "If transcutaneous capture is unreliable or prolonged support is needed, escalate to transvenous pacing.",
                ],
                "cautions": "Pain and muscle contraction are common; provide analgesia/sedation when blood pressure allows. Re-check capture frequently.",
                "fun_fact": "In crashing bradycardia, electrical and medical therapies are often started in parallel because response is unpredictable.",
            },
        ],
    },
}
