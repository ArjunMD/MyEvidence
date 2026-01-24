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

### 1) PMID → Abstract (capture a study)
**What it does:** Fetches a PubMed abstract from a PMID, then uses OpenAI to extract structured notes.

**Main controls**
- **PMID**: paste a PMID
- **Fetch**: pulls PubMed data, then runs extraction on the abstract. Extractions are editable.
- **Add to database**: saves the study to your local database.

**Suggested workflow**
1. Search a topic on PubMed. I recommend filtering by last 10 years, RCTs, systematic reviews, and/or meta-analyses to avoid dilution of levels of evidence.
2. Enter a PMID in the app → **Fetch**  
2. Quickly skim/edit the extracted fields (especially the conclusion + results bullets)  
3. Click **Add to database**  
4. (Optional) open **Related articles (top 5)** to capture nearby evidence and repeat

---
### 2) Guidelines (PDF Upload) (capture a guideline + extract recommendations)
**What it does:** Saves a guideline PDF, extracts layout text via Azure Document Intelligence, extracts guideline recommendations using OpenAI, and lets you curate them.

**Main controls**
- **Upload a guideline PDF** → choose a PDF from your computer
- **Save PDF**: stores the PDF in your local database, unless it already exists
- **Extract metadata**: These are again editable
- **Extract recommendations now**: Editable

**Reviewing extracted recommendations**
- Recommendations initially show up as **Unreviewed**
- For each recommendation:
  - **Keep**: marks it as *Relevant* (and saves any edits you made in the text box)
  - **Remove**: marks it as *Irrelevant*
  - **Delete**: permanently removes that recommendation entry

**Suggested workflow**
1. Keep recommendations that are crucial and that you would want to see when browsing a topic. "Irrelevant" are not removed. They are reviewable in different section.  
2. At this time, editing recommendations or choosing how to categorize them can only be done once, and are permanent once done (unless the whole guideline is deleted from the datagase)

---

### 3) DB Search (find a saved study or guideline)
**For papers**
- Shows a normalized formatting of PICO details:
- The original abstract and related articles are viewable in an expander

**For guidelines**
- Lets you choose what to display: Relevant, Unreviewed, Irrelevant, or All.
- Unreviewed items again have **Keep / Remove / Delete** controls.

---

### 4) DB Browse (skim your library)
**What it does:** A quick “library shelf” view grouped by **Year or Specialty**.
Use it when you want to browse rather than search. 

---

### 5) Generate meta (qualitative synthesis)
**What it does:** Pick multiple saved studies and/or guidelines and generate a single paragraph synthesis (or answer a focused question).

---

### 6) Delete (clean up)
**What it does:** Permanently deletes saved papers or guidelines (and any extracted content).

---

## Online version: preview / proof of concept

The online deployment is intended as a **preview** and may occasionally error. Reasons include (but aren’t limited to):
- **Multi-user behavior** (shared compute, file system quirks, DB locking/limits)
- **Streamlit updates**
- **App code updates / pushes**
- **Azure Document Intelligence changes**
- **OpenAI API changes**, model availability, rate limits, etc.

I am actively working on quality of life improvements, for example:
- Editing guideline recommendations *after* you’ve marked them “Relevant” (today, edits are easiest during the unreviewed review step)
- Smarter specialty normalization/merging (e.g., “Critical care” vs “Intensive care” → one combined specialty)

---

## Run MyEvidence locally (intended for those without coding/Git experience)
### Step 1 — Install prerequisites
1. Install **Python** (recommended: Python 3.10+)

### Step 2 — Download the project
- Repository Link: https://github.com/ArjunMD/MyEvidence 
- Download a ZIP and unzip it.
- Open a terminal and `cd` into the project folder. (You can google this)

### Step 3 — Create a virtual environment (recommended)
**macOS / Linux**
- In the terminal, in the project folder, type the following, then press enter: python3 -m venv .venv
- Then type the following, and press enter: source .venv/bin/activate

**Windows (PowerShell)**
- Similarly, but in powershell: py -m venv .venv
- Then .\.venv\Scripts\Activate.ps1

### Step 4 — Install dependencies
- Type then press enter: python -m pip install --upgrade pip
- Again: pip install -r requirements.txt

### Step 5 — Add your API keys (OpenAI + Azure Document Intelligence)
- Create a file within your project folder: `.streamlit/secrets.toml`
- The format is 3 lines:

OPENAI_API_KEY = ""
AZURE_DI_ENDPOINT = ""
AZURE_DI_KEY = ""

- You will then have to obtain an openAI key using OpenAI platform 
- You will have to obtain an Azure Document INtelligence Endpoint and Key as well
- You can find instructions on how to do these on google/youtube

### Step 6 - Run the app
- When ready, open a terminal, cd to the project folder, activate the virtual environment (line 2 of step 3), and then type and press enter: streamlit run app.py
- To exit the app, after closing the browser, go to the terminal and press Ctrl+C
