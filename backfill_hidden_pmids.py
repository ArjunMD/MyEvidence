"""
One-time backfill script: fetch journal, year, and pub_month from PubMed
for all hidden_pubmed_pmids rows that are missing those fields.
"""

import sqlite3
import time
import re
import xml.etree.ElementTree as ET
import requests

DB_PATH = "data/papers.db"
NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_TOOL = "streamlit-pmid-abstract"
BATCH_SIZE = 200
SLEEP_BETWEEN_BATCHES = 0.4  # seconds, stay under NCBI rate limit (3/sec without API key)

_MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def _itertext(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def _parse_month_token(raw):
    token = (raw or "").strip().lower().replace(".", "")
    if not token:
        return ""
    if re.fullmatch(r"\d{1,2}", token):
        n = int(token)
        return f"{n:02d}" if 1 <= n <= 12 else ""
    first = re.split(r"[\s\-/]+", token)[0][:3]
    return _MONTH_MAP.get(first, "")


def _parse_month_from_medline(raw):
    s = (raw or "").strip()
    if not s:
        return ""
    m = re.search(
        r"(?i)\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
        r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\b",
        s,
    )
    return _parse_month_token(m.group(1)) if m else ""


def parse_articles_from_efetch(xml_text):
    """Parse efetch XML and return dict of pmid -> {journal, year, pub_month}."""
    root = ET.fromstring(xml_text)
    results = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = _itertext(pmid_el)
        if not pmid:
            continue

        # Journal
        journal = _itertext(article.find(".//Journal/Title"))
        if not journal:
            journal = _itertext(article.find(".//Journal/ISOAbbreviation"))

        # Year
        year = _itertext(article.find(".//JournalIssue/PubDate/Year"))
        if not year:
            year = _itertext(article.find(".//ArticleDate/Year"))
        if not year:
            medline = _itertext(article.find(".//JournalIssue/PubDate/MedlineDate"))
            if medline:
                ym = re.search(r"(\d{4})", medline)
                if ym:
                    year = ym.group(1)
        if not year:
            for path in [".//DateCreated/Year", ".//DateCompleted/Year"]:
                year = _itertext(article.find(path))
                if year:
                    break

        # Month
        pub_month = ""
        for path in [
            ".//JournalIssue/PubDate/Month",
            ".//ArticleDate/Month",
            ".//DateCreated/Month",
            ".//DateCompleted/Month",
        ]:
            pub_month = _parse_month_token(_itertext(article.find(path)))
            if pub_month:
                break
        if not pub_month:
            medline = _itertext(article.find(".//JournalIssue/PubDate/MedlineDate"))
            if medline:
                pub_month = _parse_month_from_medline(medline)

        results[pmid] = {
            "journal": journal or "",
            "year": year or "",
            "pub_month": pub_month or "",
        }
    return results


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get PMIDs that need backfilling
    rows = conn.execute(
        "SELECT pmid FROM hidden_pubmed_pmids WHERE journal IS NULL OR year IS NULL OR pub_month IS NULL;"
    ).fetchall()
    pmids = [r["pmid"] for r in rows]
    total = len(pmids)
    print(f"Found {total} hidden PMIDs to backfill.")

    if not total:
        print("Nothing to do.")
        conn.close()
        return

    sess = requests.Session()
    updated = 0
    failed = 0

    for i in range(0, total, BATCH_SIZE):
        batch = pmids[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"Batch {batch_num}/{total_batches}: fetching {len(batch)} PMIDs...")

        try:
            params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "xml",
                "tool": NCBI_TOOL,
                "email": "",
            }
            r = sess.get(NCBI_EFETCH_URL, params=params, timeout=30)
            r.raise_for_status()
            articles = parse_articles_from_efetch(r.text)

            for pmid in batch:
                info = articles.get(pmid)
                if not info:
                    failed += 1
                    continue
                conn.execute(
                    """
                    UPDATE hidden_pubmed_pmids
                    SET journal = ?, year = ?, pub_month = ?
                    WHERE pmid = ?;
                    """,
                    (info["journal"] or None, info["year"] or None, info["pub_month"] or None, pmid),
                )
                updated += 1

            conn.commit()
            print(f"  -> Updated {len(articles)} articles from this batch.")

        except Exception as e:
            print(f"  -> ERROR on batch {batch_num}: {e}")
            failed += len(batch)

        if i + BATCH_SIZE < total:
            time.sleep(SLEEP_BETWEEN_BATCHES)

    conn.close()
    print(f"\nDone. Updated: {updated}, Failed/missing: {failed}, Total: {total}")


if __name__ == "__main__":
    main()
