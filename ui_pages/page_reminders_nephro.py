import streamlit as st


def render() -> None:
    st.title("📝 Nephrology")

    with st.expander("BP Medications in CKD5 / ESRD", expanded=False):
        st.subheader("General Principles")
        st.markdown(
            "- **Target BP** in dialysis patients is debated; a pre-dialysis BP < 140/90 mmHg is a common goal (KDIGO). Avoid aggressive targets that cause intradialytic hypotension.\n"
            "- **Volume overload** is the #1 contributor to hypertension in ESRD — optimize dry weight and sodium restriction before escalating medications.\n"
            "- **Dialyzability** matters — drugs removed by hemodialysis may need post-HD supplemental dosing or are less effective overall.\n"
            "- **ACEi / ARBs** can still be used in ESRD but hyperkalemia risk is higher and there is no GFR to \"preserve\" — use primarily for cardiac indications (HFrEF, post-MI).\n"
            "- Avoid NSAIDs (residual renal function loss, volume retention) and excessive renin-angiotensin blockade (hyperkalemia)."
        )

        st.divider()
        st.subheader("Preferred Agents")
        st.markdown(
            "| Drug Class | Preferred Agent(s) | Dose Adjustments in ESRD | Dialyzable? | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| **Long-acting CCBs (DHP)** | **Amlodipine**, **Nifedipine XL** | No dose adjustment needed | Not significantly dialyzed | **First-line in ESRD hypertension.** Effective regardless of volume status. Not removed by HD — consistent BP control on dialysis and non-dialysis days. Peripheral edema is a side effect (can be difficult to distinguish from volume overload). |\n"
            "| **Non-DHP CCBs** | **Diltiazem ER**, **Verapamil ER** | No dose adjustment | Not significantly dialyzed | Useful if rate control also needed (AF). Avoid in HFrEF (negative inotropy). Constipation common with verapamil — problematic in ESRD patients already prone to constipation. |\n"
            "| **Beta-blockers** | **Carvedilol**, **Metoprolol succinate (XL)** | Carvedilol: no adjustment. Metoprolol: no adjustment. | Carvedilol: not dialyzed. Metoprolol: partially dialyzed (give post-HD if using tartrate). | Preferred if concomitant HFrEF, CAD, or rate control needed. Carvedilol has alpha-blocking vasodilatory properties (may help with BP). **Atenolol** is heavily dialyzed — causes rebound hypertension on non-HD days and intradialytic hypotension on HD days → generally avoid. |\n"
            "| **ACE inhibitors** | **Lisinopril**, **Ramipril** | Lisinopril: start low (2.5–5 mg). Ramipril: start low (1.25–2.5 mg). | Lisinopril: dialyzed. Ramipril: partially dialyzed. Give post-HD dose. | Use for **cardiac indications** (HFrEF, post-MI, LVH regression). Monitor K⁺ closely (q1–2 weeks initially). Fosinopril is the only ACEi with significant hepatic clearance (no dose adjustment), but less commonly used. |\n"
            "| **ARBs** | **Losartan**, **Valsartan**, **Irbesartan** | Losartan: no adjustment. Valsartan: no adjustment. | Not significantly dialyzed | Alternative to ACEi for cardiac indications. Same K⁺ monitoring needed. Not dialyzed — stable levels across HD sessions. |\n"
            "| **Alpha-1 blockers** | **Doxazosin**, **Prazosin** | No dose adjustment | Not significantly dialyzed | Useful as add-on therapy. **Doxazosin** preferred (once daily). First-dose orthostatic hypotension — start at bedtime. Also helps with BPH symptoms. |\n"
            "| **Central alpha-2 agonists** | **Clonidine** (patch or oral) | Reduce dose in severe CKD; supplemental dose post-HD if oral | Partially dialyzed (oral) | **Clonidine patch** (weekly) provides steady-state levels unaffected by HD — good option for non-adherent patients. Avoid abrupt discontinuation (rebound hypertension crisis). Sedation, dry mouth, bradycardia. |\n"
            "| **Direct vasodilators** | **Hydralazine**, **Minoxidil** | Hydralazine: reduce frequency. Minoxidil: start 2.5 mg. | Hydralazine: partially dialyzed. Minoxidil: dialyzed (give post-HD). | **Minoxidil** is extremely potent — reserved for refractory hypertension. MUST be combined with a beta-blocker (reflex tachycardia) and a loop diuretic or adequate ultrafiltration (fluid retention). Causes hirsutism. Hydralazine: lupus-like syndrome at high doses. |"
        )

        st.divider()
        st.subheader("Agents to Avoid or Use with Caution")
        st.markdown(
            "| Drug / Class | Why to Avoid in CKD5 / ESRD |\n"
            "| --- | --- |\n"
            "| **Atenolol** | Renally cleared, heavily dialyzed → large swings in levels. Causes intradialytic hypotension (HD days) and rebound hypertension (non-HD days). Use carvedilol or metoprolol succinate instead. |\n"
            "| **Sotalol** | Renally cleared, QT prolongation risk amplified in ESRD. Dialyzed — requires dose after HD. High arrhythmia risk. |\n"
            "| **Thiazide diuretics** | Ineffective when GFR < 15–20 mL/min (need adequate tubular flow). No role in anuric ESRD. Some nephrologists use **metolazone** or **chlorthalidone** in patients with residual urine output for volume management. |\n"
            "| **K⁺-sparing diuretics** (spironolactone, amiloride, triamterene) | High risk of **life-threatening hyperkalemia** in ESRD. Spironolactone may still be used with close monitoring for select HFrEF patients on dialysis (emerging evidence), but requires very careful K⁺ surveillance. |\n"
            "| **Aliskiren** (direct renin inhibitor) | Hyperkalemia risk, no proven benefit in ESRD, limited clearance data. Avoid. |\n"
            "| **Short-acting nifedipine** (sublingual/bite-and-swallow) | Precipitous BP drops, reflex tachycardia, stroke/MI risk. Banned by many institutions. Use long-acting formulations only. |"
        )

        st.divider()
        st.subheader("Intradialytic Hypertension")
        st.markdown(
            "- Paradoxical BP rise during or immediately after HD. Occurs in ~10–15% of HD patients.\n"
            "- **Mechanisms:** sympathetic activation from ultrafiltration, volume overload (inadequate UF goal), "
            "endothelin-1 release, removal of vasodilatory substances during HD, RAAS activation, erythropoietin use.\n"
            "- **Management:**\n"
            "  1. Reassess and lower dry weight (most important step)\n"
            "  2. Restrict dietary sodium (< 2 g/day)\n"
            "  3. Extend dialysis time or increase frequency\n"
            "  4. Carvedilol is often first-line pharmacotherapy\n"
            "  5. Consider holding midodrine on HD days if the patient takes it\n"
            "  6. Avoid intradialytic hypertension being treated with IV hydralazine or labetalol in a reactive pattern — focus on preventive, long-acting oral agents"
        )
