import json
from pathlib import Path
import bibtexparser

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "data" / "publications.bib"
OUT = ROOT / "data" / "publications.json"

def split_authors(author_field: str):
    parts = [a.strip() for a in (author_field or "").split(" and ") if a.strip()]
    return parts

def main():
    if not BIB.exists():
        raise FileNotFoundError(f"Missing: {BIB}")

    with BIB.open("r", encoding="utf-8") as f:
        db = bibtexparser.load(f)

    pubs = []
    for e in db.entries:
        year_raw = (e.get("year") or "").strip()
        try:
            year = int(year_raw) if year_raw else 0
        except ValueError:
            year = 0

        venue = e.get("journal") or e.get("booktitle") or e.get("publisher") or ""

        pubs.append({
            "id": e.get("ID", ""),
            "type": e.get("ENTRYTYPE", ""),
            "title": e.get("title", ""),
            "authors": split_authors(e.get("author", "")),
            "venue": venue,
            "year": year,
            "url": e.get("url", ""),
            "doi": e.get("doi", ""),
        })

    pubs.sort(key=lambda x: (x["year"], x["title"]), reverse=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pubs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(pubs)} items)")

if __name__ == "__main__":
    main()
