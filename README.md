# MyEvidence

A lightweight evidence manager for clinicians: pull PubMed abstracts by PMID, extract key PICO-style details, upload guideline PDFs, and keep a searchable, curated library.

---

## About the app

**MyEvidence** is designed to be:
- **Curated**: you intentionally add items to your database and keep what matters.
- **Easy to navigate**: a small set of pages with one job each (capture → review → search → synthesize).
- **Easy to read**: the database view emphasizes “what I need to know quickly” (population, intervention/comparison, outcomes/results, and the authors’ bottom line).

MyEvidence currently supports two types of sources:
1. **PubMed studies** (via PMID lookup)
2. **Guideline PDFs** (via Azure Document Intelligence → recommendation extraction)

---

## How to use the app

### Navigation (left sidebar)
Use the **Navigate** radio buttons to switch pages:
- **PMID → Abstract**
- **Guidelines (PDF Upload)**
- **DB Search**
- **DB Browse**
- **Generate meta**
- **Delete**

The sidebar also shows your current **DB path** and **Saved** count.

---

### 1) PMID → Abstract (capture a study)
**What it does:** Fetches a PubMed abstract from a PMID, then uses OpenAI to extract structured notes.

**Main controls**
- **PMID**: paste a PMID
- **Fetch**: pulls PubMed data, then runs extraction on the abstract.
- **Add to database**: saves the study to your local database.

**Right-side fields (editable before saving)**
- **Author’s conclusions**
- **Total patients (N)**
- **Study design tags**
- **Patient details** (P)
- **Intervention / comparison** (I/C)
- **Results** (O)
- **Specialty**

**Suggested workflow**
1. Enter PMID → **Fetch**  
2. Quickly skim/edit the extracted fields (especially the conclusion + results bullets)  
3. Click **Add to database**  
4. (Optional) open **Related articles (top 5)** to capture nearby evidence

---

### 2) Guidelines (PDF Upload) (capture a guideline + extract recommendations)
**What it does:** Saves a guideline PDF, extracts layout text via Azure Document Intelligence, then extracts guideline recommendations and lets you curate them.

**Main controls**
- **Upload a guideline PDF** → choose a PDF from your computer
- **Save PDF**: stores the PDF in your local database
- **Guideline metadata**:
  - **Name**
  - **Published year**
  - **Specialty**
  - **Save metadata (if changed)**
  - **Extract metadata** (uses Azure extraction to propose name/year/specialty)
- **Extract recommendations now**: runs recommendation extraction (only enabled if recommendations aren’t already stored)

**Reviewing extracted recommendations**
- Recommendations initially show up as **Unreviewed**
- For each recommendation:
  - **Keep**: marks it as *Relevant* (and saves any edits you made in the text box)
  - **Remove**: marks it as *Irrelevant*
  - **Delete**: permanently removes that recommendation entry

**Suggested workflow**
1. Upload PDF → **Save PDF**
2. Fill in metadata (or **Extract metadata**) → **Save metadata**
3. Click **Extract recommendations now**
4. Curate the unreviewed list using **Keep / Remove / Delete**

---

### 3) DB Search (find a saved study or guideline)
**What it does:** Searches across your saved papers + guidelines.

**For papers**
- Shows a clean, read-first view of:
  - P (Population)
  - I/C (Intervention/Comparison)
  - O (Outcomes/Results)
  - Author’s conclusion
  - (Optional) the original abstract in an expander

**For guidelines**
- Lets you choose what to display:
  - **Relevant**
  - **Unreviewed**
  - **Irrelevant**
  - **All**
- Unreviewed items again have **Keep / Remove / Delete** controls.

---

### 4) DB Browse (skim your library)
**What it does:** A quick “library shelf” view grouped by **Specialty → Year**.

Use it when you want to browse rather than search.

---

### 5) Generate meta (qualitative synthesis)
**What it does:** Pick multiple saved studies and/or guidelines and generate a single paragraph synthesis (or answer a focused question).

**Main controls**
- **Paper content**
  - **Send abstracts** (richer context)
  - **Send extracted data** (faster, possibly less accurate)
- **Generation mode**
  - **Synthesize**
  - **Answer focused question** (enter a question)

**Suggested workflow**
1. Filter (optional) to find sources you want
2. Check **Pick** for the relevant papers/guidelines
3. Choose content mode + generation mode
4. Click **Generate** and copy the output

---

### 6) Delete (clean up)
**What it does:** Permanently deletes saved papers or guidelines (and any extracted content).

You must check **Confirm permanent delete** before the delete button becomes active.

---

## Online version: preview / proof of concept

The online deployment is intended as a **preview** and may occasionally error. Reasons include (but aren’t limited to):
- **Multi-user behavior** (shared compute, file system quirks, DB locking/limits)
- **Streamlit updates**
- **App code updates / pushes**
- **Azure Document Intelligence changes**
- **OpenAI API changes**, model availability, rate limits, etc.

There are also quality-of-life improvements not yet implemented, for example:
- Editing guideline recommendations *after* you’ve marked them “Relevant” (today, edits are easiest during the unreviewed review step)
- Smarter specialty normalization/merging (e.g., “Critical care” vs “Intensive care” → one combined specialty)

---

## Run MyEvidence locally (no coding experience needed)

### Step 1 — Install prerequisites
1. Install **Python** (recommended: Python 3.10+)
2. Install **Git** (optional but recommended if you’re cloning a repo)

### Step 2 — Download the project
- Repo Link: https://github.com/ArjunMD/MyEvidence 
- Clone it (or download a ZIP and unzip it).
- Open a terminal and `cd` into the project folder.

### Step 3 — Create a virtual environment (recommended)
**macOS / Linux**
python3 -m venv .venv
source .venv/bin/activate

**Windows (PowerShell)**
py -m venv .venv
.\.venv\Scripts\Activate.ps1

### Step 4 — Install dependencies
pip install -r requirements.txt

### Step 5 — Add your API keys (OpenAI + Azure Document Intelligence)
Create a file at:
.streamlit/secrets.toml

Example `secrets.toml`:
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
# Optional:
OPENAI_MODEL = "gpt-5.2"

AZURE_DI_ENDPOINT = "https://YOUR_RESOURCE_NAME.cognitiveservices.azure.com/"
AZURE_DI_KEY = "YOUR_AZURE_DOCUMENT_INTELLIGENCE_KEY"

Where to get keys:
- **OpenAI key**: from your OpenAI account’s API key page
- **Azure Document Intelligence**:
  - Create an Azure **Document Intelligence** (or Cognitive Services) resource
  - Copy the **Endpoint** and **Key**

### Step 6 — Run the app
From the project folder:
streamlit run app.py

---

## Notes on storage
- By default, the app stores your library in a local SQLite DB at: `data/pmid_abstracts.db`

---

## Contact / collaboration

If you want to collaborate, improve features, or just share feedback, feel free to reach out. I’m happy to hear what would make the workflow more useful (and I’m open to working together on additions or polish).
