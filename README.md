# MyEvidence

MyEvidence is a lightweight app for building a personal, searchable evidence library from PubMed abstracts and guideline PDFs.

## What the app does

- Save PubMed abstracts by PMID. The app auto-extracts key details and presents them in a clean format.
- Upload guideline PDFs. The app extracts recommendations, organizes them into categories, and presents them clearly.
- Search and browse your database.
- Use a limited PubMed search to stay current. Add useful papers to your database, or hide papers that are not relevant.
- Answer focused questions using selected evidence. You can also save reusable sets of papers and guidelines into folders.

## Stack
- Streamlit UI
- SQLite local database (`data/papers.db`)
- OpenAI Responses API for extraction/synthesis
- Azure Document Intelligence for guideline PDF parsing

## Online version is a preview
- You can try the workflow online, but changes are not currently permanent. Only server-side updates are persistent.
- Online version also has potential for glitching due to a variety of mechanisms.
- If you have feedback, questions, or ideas, or want a local version just for you, feel free to reach out!
