"""Dashboard — visual analytics for saved abstracts and review activity."""

import re
from collections import Counter
from typing import Dict, List

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import (
    dashboard_hidden_per_journal,
    dashboard_patient_n_values,
    dashboard_recent_additions,
    dashboard_saved_per_journal,
    dashboard_saved_per_year,
    dashboard_saved_per_year_month,
    dashboard_saved_specialties,
    dashboard_study_design_distribution,
    db_count,
)

# ── colour palette ──────────────────────────────────────────────────
_PALETTE = px.colors.qualitative.Set2
_PRIMARY = "#4C78A8"
_ACCENT = "#F58518"
_PLOTLY_TEMPLATE = "plotly_white"

# Consistent journal name normalization
_JOURNAL_SHORT: Dict[str, str] = {
    "The New England journal of medicine": "NEJM",
    "Lancet (London, England)": "Lancet",
    "BMJ (Clinical research ed.)": "BMJ",
    "Critical care (London, England)": "Critical Care",
    "The Cochrane database of systematic reviews": "Cochrane",
    "Clinical infectious diseases : an official publication of the Infectious Diseases Society of America": "Clin Infect Dis",
    "Journal of clinical oncology : official journal of the American Society of Clinical Oncology": "J Clin Oncol",
    "The Lancet. Oncology": "Lancet Oncol",
    "The Lancet. Infectious diseases": "Lancet Infect Dis",
    "The Lancet. Respiratory medicine": "Lancet Respir Med",
    "The Lancet. Gastroenterology & hepatology": "Lancet Gastro Hepatol",
    "The Lancet. Psychiatry": "Lancet Psychiatry",
    "The Lancet. Haematology": "Lancet Haematol",
    "The Lancet. Rheumatology": "Lancet Rheumatol",
    "The Lancet. Diabetes & endocrinology": "Lancet Diabetes Endocrinol",
    "The Journal of clinical endocrinology and metabolism": "J Clin Endocrinol Metab",
    "Journal of the American College of Cardiology": "JACC",
    "European heart journal": "Eur Heart J",
    "Annals of internal medicine": "Ann Intern Med",
    "JAMA internal medicine": "JAMA Intern Med",
    "JAMA network open": "JAMA Netw Open",
    "JAMA neurology": "JAMA Neurol",
    "JAMA cardiology": "JAMA Cardiol",
    "JAMA surgery": "JAMA Surg",
    "JAMA psychiatry": "JAMA Psychiatry",
    "JAMA oncology": "JAMA Oncol",
    "Intensive care medicine": "Intensive Care Med",
    "Annals of emergency medicine": "Ann Emerg Med",
    "American journal of respiratory and critical care medicine": "Am J Respir Crit Care Med",
    "Journal of the American Society of Nephrology : JASN": "JASN",
    "Kidney international": "Kidney Int",
    "Journal of hepatology": "J Hepatol",
    "Annals of surgery": "Ann Surg",
    "Annals of the rheumatic diseases": "Ann Rheum Dis",
    "Journal of general internal medicine": "JGIM",
    "Journal of hospital medicine": "J Hosp Med",
    "American journal of medicine (The)": "Am J Med",
    "Nature medicine": "Nat Med",
    "Diabetes care": "Diabetes Care",
    "Journal of pain and symptom management": "J Pain Symptom Manage",
    "World psychiatry : official journal of the World Psychiatric Association (WPA)": "World Psychiatry",
}


def _short_journal(name: str) -> str:
    s = (name or "").strip()
    if not s:
        return "Unknown"
    low = s.lower()
    for long, short in _JOURNAL_SHORT.items():
        if long.lower() == low:
            return short
    # Fallback: title-case, truncate
    if len(s) > 30:
        return s[:27] + "..."
    return s


# ── specialty explosion helper ──────────────────────────────────────
def _explode_specialties(raw_rows: List[Dict]) -> Counter:
    counts: Counter = Counter()
    for row in raw_rows:
        raw = (row.get("specialty") or "").strip()
        if not raw:
            counts["Unspecified"] += 1
            continue
        parts = re.split(r"[,;\|\n]+", raw)
        for p in parts:
            s = p.strip()
            if s:
                counts[s] += 1
    return counts


# ── study design grouping ──────────────────────────────────────────
def _group_study_designs(raw_rows: List[Dict]) -> Counter:
    counts: Counter = Counter()
    for row in raw_rows:
        raw = (row.get("study_design") or "").strip().lower()
        if not raw:
            counts["Not specified"] += 1
            continue
        if "meta-analysis" in raw and "systematic review" in raw:
            counts["Systematic review & meta-analysis"] += 1
        elif "systematic review" in raw:
            counts["Systematic review"] += 1
        elif "meta-analysis" in raw:
            counts["Meta-analysis"] += 1
        elif "randomized" in raw:
            if "double-blind" in raw or "placebo" in raw:
                counts["Double-blind RCT"] += 1
            elif "cluster" in raw:
                counts["Cluster RCT"] += 1
            else:
                counts["Randomized controlled trial"] += 1
        elif "cohort" in raw:
            counts["Cohort study"] += 1
        elif "cross-sectional" in raw:
            counts["Cross-sectional study"] += 1
        elif "case-control" in raw or "case control" in raw:
            counts["Case-control study"] += 1
        elif "case report" in raw or "case series" in raw:
            counts["Case report / series"] += 1
        elif "observational" in raw:
            counts["Observational study"] += 1
        elif "retrospective" in raw:
            counts["Retrospective study"] += 1
        elif "prospective" in raw:
            counts["Prospective study"] += 1
        elif "post hoc" in raw:
            counts["Post-hoc analysis"] += 1
        elif "network meta" in raw:
            counts["Network meta-analysis"] += 1
        elif "guideline" in raw or "consensus" in raw:
            counts["Guideline / consensus"] += 1
        else:
            counts["Other"] += 1
    return counts


# ── render ─────────────────────────────────────────────────────────
def render() -> None:
    st.title("Dashboard")

    # ── fetch data ──
    saved_per_journal = dashboard_saved_per_journal()
    hidden_per_journal = dashboard_hidden_per_journal()
    specialty_rows = dashboard_saved_specialties()
    study_design_rows = dashboard_study_design_distribution()
    year_data = dashboard_saved_per_year()
    year_month_data = dashboard_saved_per_year_month()
    patient_ns = dashboard_patient_n_values()
    recent_30 = dashboard_recent_additions(30)

    total_saved = sum(r["count"] for r in saved_per_journal)
    total_hidden = sum(r["count"] for r in hidden_per_journal)
    total_reviewed = total_saved + total_hidden
    save_rate = (total_saved / total_reviewed * 100) if total_reviewed else 0
    n_journals = len([r for r in saved_per_journal if r["count"] > 0])
    specialty_counts = _explode_specialties(specialty_rows)
    n_specialties = len([k for k in specialty_counts if k != "Unspecified"])

    # ════════════════════════════════════════════════════════════════
    # A. KPI METRICS
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Overview")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Papers saved", f"{total_saved:,}")
    k2.metric("Papers reviewed", f"{total_reviewed:,}")
    k3.metric("Save rate", f"{save_rate:.1f}%")
    k4.metric("Journals", str(n_journals))
    k5.metric("Specialties", str(n_specialties))

    m1, m2 = st.columns(2)
    m1.metric("Added (last 30 days)", str(recent_30))
    if patient_ns:
        median_n = sorted(patient_ns)[len(patient_ns) // 2]
        m2.metric("Median sample size (n)", f"{median_n:,}")

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # B. SAVED PAPERS BY JOURNAL (horizontal bar)
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Saved papers by journal")
    top_n = 20
    top_saved = saved_per_journal[:top_n]
    if top_saved:
        journals = [_short_journal(r["journal"]) for r in reversed(top_saved)]
        counts = [r["count"] for r in reversed(top_saved)]
        fig = go.Figure(
            go.Bar(
                x=counts,
                y=journals,
                orientation="h",
                marker_color=_PRIMARY,
                text=counts,
                textposition="outside",
            )
        )
        fig.update_layout(
            template=_PLOTLY_TEMPLATE,
            height=max(400, len(top_saved) * 28),
            margin=dict(l=10, r=40, t=10, b=10),
            xaxis_title="Papers saved",
            yaxis=dict(tickfont=dict(size=12)),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # C. SAVED vs REVIEWED PER JOURNAL (grouped bar)
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Saved vs reviewed per journal")
    st.caption("Reviewed = saved + dismissed via 'Don't show again'")

    hidden_map: Dict[str, int] = {}
    for r in hidden_per_journal:
        key = _short_journal(r["journal"])
        hidden_map[key] = hidden_map.get(key, 0) + int(r["count"])

    # Top journals by total reviewed
    journal_total_reviewed: Dict[str, int] = {}
    saved_map: Dict[str, int] = {}
    for r in saved_per_journal:
        key = _short_journal(r["journal"])
        saved_map[key] = saved_map.get(key, 0) + int(r["count"])

    all_journals = set(saved_map.keys()) | set(hidden_map.keys())
    for j in all_journals:
        journal_total_reviewed[j] = saved_map.get(j, 0) + hidden_map.get(j, 0)

    top_reviewed = sorted(journal_total_reviewed.items(), key=lambda x: x[1], reverse=True)[:15]

    if top_reviewed:
        jr_names = [t[0] for t in reversed(top_reviewed)]
        jr_saved = [saved_map.get(j, 0) for j in jr_names]
        jr_hidden = [hidden_map.get(j, 0) for j in jr_names]

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            y=jr_names, x=jr_saved, name="Saved",
            orientation="h", marker_color=_PRIMARY,
        ))
        fig2.add_trace(go.Bar(
            y=jr_names, x=jr_hidden, name="Dismissed",
            orientation="h", marker_color="#D4D4D4",
        ))
        fig2.update_layout(
            barmode="stack",
            template=_PLOTLY_TEMPLATE,
            height=max(400, len(top_reviewed) * 32),
            margin=dict(l=10, r=30, t=10, b=10),
            xaxis_title="Articles",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(tickfont=dict(size=12)),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # D. SAVE RATE BY JOURNAL (bar chart)
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Save rate by journal")
    st.caption("Among journals with at least 10 reviewed articles")

    rate_data = []
    for j in all_journals:
        s = saved_map.get(j, 0)
        t = journal_total_reviewed.get(j, 0)
        if t >= 10:
            rate_data.append({"journal": j, "rate": s / t * 100, "saved": s, "total": t})

    rate_data.sort(key=lambda x: x["rate"], reverse=True)
    top_rates = rate_data[:20]

    if top_rates:
        fig3 = go.Figure(
            go.Bar(
                x=[r["rate"] for r in reversed(top_rates)],
                y=[r["journal"] for r in reversed(top_rates)],
                orientation="h",
                marker_color=[_ACCENT if r["rate"] >= save_rate else "#93B7D6" for r in reversed(top_rates)],
                text=[f'{r["rate"]:.0f}% ({r["saved"]}/{r["total"]})' for r in reversed(top_rates)],
                textposition="outside",
            )
        )
        fig3.update_layout(
            template=_PLOTLY_TEMPLATE,
            height=max(350, len(top_rates) * 28),
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis_title="Save rate (%)",
            xaxis=dict(range=[0, max(r["rate"] for r in top_rates) * 1.3]),
            yaxis=dict(tickfont=dict(size=12)),
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # E. SPECIALTY AFFINITY (treemap)
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Specialty affinity")
    st.caption("Multi-specialty papers count toward each tagged specialty")

    if specialty_counts:
        spec_sorted = specialty_counts.most_common()
        spec_names = [s[0] for s in spec_sorted]
        spec_vals = [s[1] for s in spec_sorted]

        fig4 = go.Figure(go.Treemap(
            labels=spec_names,
            parents=[""] * len(spec_names),
            values=spec_vals,
            textinfo="label+value",
            marker=dict(
                colors=spec_vals,
                colorscale="Blues",
                showscale=False,
            ),
            hovertemplate="<b>%{label}</b><br>Papers: %{value}<extra></extra>",
        ))
        fig4.update_layout(
            template=_PLOTLY_TEMPLATE,
            height=500,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # F. STUDY DESIGN DISTRIBUTION (donut)
    # ════════════════════════════════════════════════════════════════
    col_design, col_design_table = st.columns([3, 2])

    with col_design:
        st.markdown("### Study design distribution")
        grouped_designs = _group_study_designs(study_design_rows)
        if grouped_designs:
            design_sorted = grouped_designs.most_common()
            labels = [d[0] for d in design_sorted]
            values = [d[1] for d in design_sorted]

            fig5 = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                textinfo="percent+label",
                textposition="outside",
                marker=dict(colors=_PALETTE * 5),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>",
            ))
            fig5.update_layout(
                template=_PLOTLY_TEMPLATE,
                height=450,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig5, use_container_width=True)

    with col_design_table:
        st.markdown("### Breakdown")
        if grouped_designs:
            design_sorted = grouped_designs.most_common()
            for label, count in design_sorted:
                pct = count / total_saved * 100 if total_saved else 0
                st.markdown(f"**{label}** — {count} ({pct:.1f}%)")

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # G. PUBLICATION TIMELINE (area chart by year)
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Publication timeline")

    if year_data:
        years = [r["year"] for r in year_data]
        counts_y = [r["count"] for r in year_data]
        fig6 = go.Figure(go.Scatter(
            x=years,
            y=counts_y,
            mode="lines+markers+text",
            text=counts_y,
            textposition="top center",
            fill="tozeroy",
            fillcolor="rgba(76, 120, 168, 0.15)",
            line=dict(color=_PRIMARY, width=2.5),
            marker=dict(size=8, color=_PRIMARY),
        ))
        fig6.update_layout(
            template=_PLOTLY_TEMPLATE,
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Publication year",
            yaxis_title="Papers saved",
            xaxis=dict(type="category"),
        )
        st.plotly_chart(fig6, use_container_width=True)

    # Monthly breakdown for recent years
    _MONTH_NAMES = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }
    recent_years = sorted(
        set(r["year"] for r in year_month_data if r["year"] in ("2025", "2026")),
    )
    if recent_years:
        st.markdown("#### Monthly detail (recent years)")
        fig7 = go.Figure()
        for yr in recent_years:
            monthly = [r for r in year_month_data if r["year"] == yr and r["pub_month"]]
            months_sorted = sorted(monthly, key=lambda r: r["pub_month"])
            x_labels = [_MONTH_NAMES.get(r["pub_month"], r["pub_month"]) for r in months_sorted]
            y_vals = [r["count"] for r in months_sorted]
            fig7.add_trace(go.Scatter(
                x=x_labels, y=y_vals,
                mode="lines+markers",
                name=yr,
                line=dict(width=2.5),
                marker=dict(size=7),
            ))
        fig7.update_layout(
            template=_PLOTLY_TEMPLATE,
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Month",
            yaxis_title="Papers saved",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig7, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # H. PATIENT SAMPLE SIZES (histogram)
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Patient sample sizes")

    if patient_ns:
        col_h1, col_h2 = st.columns([3, 1])

        with col_h1:
            fig8 = go.Figure(go.Histogram(
                x=patient_ns,
                nbinsx=40,
                marker_color=_PRIMARY,
                opacity=0.85,
            ))
            fig8.update_layout(
                template=_PLOTLY_TEMPLATE,
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Number of patients (n)",
                yaxis_title="Number of studies",
            )
            st.plotly_chart(fig8, use_container_width=True)

        with col_h2:
            sorted_ns = sorted(patient_ns)
            total_n = len(sorted_ns)
            q1 = sorted_ns[total_n // 4]
            median_n = sorted_ns[total_n // 2]
            q3 = sorted_ns[3 * total_n // 4]
            st.markdown("#### Summary statistics")
            st.markdown(f"**Studies with n** — {total_n}")
            st.markdown(f"**Min** — {min(sorted_ns):,}")
            st.markdown(f"**Q1** — {q1:,}")
            st.markdown(f"**Median** — {median_n:,}")
            st.markdown(f"**Q3** — {q3:,}")
            st.markdown(f"**Max** — {max(sorted_ns):,}")
            st.markdown(f"**Mean** — {sum(sorted_ns) // total_n:,}")
    else:
        st.info("No patient sample size data available.")

    st.divider()

    # ════════════════════════════════════════════════════════════════
    # I. TOP SPECIALTY-JOURNAL COMBINATIONS
    # ════════════════════════════════════════════════════════════════
    st.markdown("### Top specialty-journal combinations")

    spec_journal_counter: Counter = Counter()
    for row in specialty_rows:
        raw_spec = (row.get("specialty") or "").strip()
        if not raw_spec:
            continue
        parts = re.split(r"[,;\|\n]+", raw_spec)
        for p in parts:
            s = p.strip()
            if s:
                spec_journal_counter[s] += 1

    # Reuse saved_per_journal for journal info — fetch full records
    # Actually, we need specialty-journal pairs. Query directly.
    _render_specialty_journal_heatmap()


def _render_specialty_journal_heatmap() -> None:
    """Specialty vs journal heatmap from raw abstracts data."""
    from db import _connect_db

    with _connect_db() as conn:
        rows = conn.execute("SELECT specialty, journal FROM abstracts;").fetchall()

    pair_counter: Counter = Counter()
    for r in rows:
        raw_spec = (r["specialty"] or "").strip()
        journal = _short_journal((r["journal"] or "").strip())
        if not raw_spec:
            raw_spec = "Unspecified"
        parts = re.split(r"[,;\|\n]+", raw_spec)
        for p in parts:
            s = p.strip()
            if s:
                pair_counter[(s, journal)] += 1

    if not pair_counter:
        return

    # Top 10 specialties and top 10 journals by count
    spec_totals: Counter = Counter()
    journal_totals: Counter = Counter()
    for (s, j), c in pair_counter.items():
        spec_totals[s] += c
        journal_totals[j] += c

    top_specs = [s for s, _ in spec_totals.most_common(10)]
    top_journals = [j for j, _ in journal_totals.most_common(10)]

    z_data = []
    for spec in top_specs:
        row = [pair_counter.get((spec, j), 0) for j in top_journals]
        z_data.append(row)

    fig = go.Figure(go.Heatmap(
        z=z_data,
        x=top_journals,
        y=top_specs,
        colorscale="Blues",
        text=z_data,
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b> + <b>%{x}</b><br>Papers: %{z}<extra></extra>",
    ))
    fig.update_layout(
        template=_PLOTLY_TEMPLATE,
        height=400,
        margin=dict(l=10, r=10, t=10, b=80),
        xaxis=dict(tickangle=-45, tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=12)),
    )
    st.plotly_chart(fig, use_container_width=True)
