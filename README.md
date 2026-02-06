# MyEvidence

Build your own evidence shelf you'll actually use.

**MyEvidence** is an application for clinicians who like PubMed… but don’t like losing the good papers in 37 open tabs; who like guidelines... but don't like scanning 80 pages for actionalble recommendations. Save studies + guidelines into a personal database, skim them in a clean format, and generate quick syntheses when you’re trying to make a call.

This is meant to feel like a lightweight, practical tool — not a research platform.

---

## What you can do

### ✅ Save PubMed studies fast
- Paste a **PMID**
- Pull the abstract from PubMed
- Auto-extract structured notes:
  - patient count
  - study design + setting tags
  - patient details
  - intervention/comparison
  - results bullets
  - authors’ conclusion
- Save it into your local database
- I recommend keeping additions to RCTs, meta-analyses, and systematic reviews to avoid diluting level of evide

### ✅ Search PubMed cleanly
- Limited, clean search options
- Results automatically hide:
  - articles already saved in your local DB
  - articles you marked as **Don't show again**

### ✅ Turn guideline PDFs into something readable
- Upload a guideline PDF (the PDF file itself isn’t stored — only extracted text + your curated display)
- Auto-extract recommendations, categorized into sections (Labs, Imaging, Disposition, etc.)
- Edit the final display however you want

### ✅ Find stuff when you actually need it
- Use **DB Search** and **DB Browse** to search across your saved papers/guidelines and skim by year or specialty

### ✅ Answer focused questions
- Select the studies and guidelines you want to use as evidence and ask focused questions, for example:
  - What are the contradictions among these guidelines?
  - What is the overall side-effect profile of [insert medication]?
  - What is the effect size of [insert intervention]?

---

## What’s going on with each button click (and what you can edit)

### 1) PMID → Abstract
- **Fetch** pulls the PubMed abstract by PMID, plus:
  - top 5 PubMed “Related articles”
  - top 5 Semantic Scholar recommendations
- It also extracts a structured summary (editable) and suggests a specialty label.
- **Before saving:** everything is editable.
- **After saving:** it’s read-only (but easy to delete and re-add if you want to revise).

### 2) Guidelines — Upload PDF
- **Upload + Extract**:
  1) uses Azure Document Intelligence to convert the PDF into text/markdown (used for extraction)
  2) extracts metadata (name/year/specialty)
  3) extracts actionable recommendations and organizes them into clinician-friendly sections
- Only the final recommendations display is saved as **Markdown** and is fully editable.
- You can also quick-delete individual recommendations from the guideline view in **DB Search**.
- For large guideline file sizes, make sure computer doesn't go to sleep as you extract.


### 3) Generate meta (qualitative synthesis)
- Pick any mix of saved papers + guidelines and generate a single-paragraph answer to a **focused clinical question**.

### 4) Search PubMed
- Search by date range plus journal/study-type filters.
- Current journal options: **N Engl J Med**, **JAMA**, **The Lancet**.
- Current study-type options: **Clinical Trial**, **Meta analysis**, or **Both**.
- Each result has a **Don't show again** button.
- Results are always filtered to remove:
  - already-saved PMIDs
  - previously hidden PMIDs

---

## Online version = preview (expect occasional weirdness)

The online deployment is meant to let you try the workflow and vibe — but it’s not the “serious” version.

Things that can happen online:
- random errors/timeouts (shared compute + transient limits)
- database behavior can be quirky (multi-user filesystem, locking, or resets depending on hosting)
- extraction can fail intermittently (rate limits, model availability, upstream API changes)

The online demo may reset occasionally as I push updates. If you want a reliable personal library, running locally is the way to go.

If you have suggestions, please reach out — I’m actively improving this.
(Repo: https://github.com/ArjunMD/MyEvidence/)
