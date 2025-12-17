import re
import json
from pathlib import Path
import bibtexparser

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "data" / "publications.bib"
OUT = ROOT / "data" / "publications.json"
AUTHOR_LINKS = ROOT / "data" / "author_links.json"

def normalize_name(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00a0", " ")          # NBSP 같은 특수 공백 제거
    s = re.sub(r"[{}]", "", s)            # { } 제거
    s = " ".join(s.split())               # 공백 여러 개/줄바꿈 정리
    s = s.strip().rstrip(",")             # 끝 쉼표 제거
    return s

def split_authors(author_field: str):
    author_field = normalize_name(author_field)
    parts = [normalize_name(x) for x in re.split(r"\s+and\s+", author_field) if x.strip()]
    return parts

def load_author_links():
    if AUTHOR_LINKS.exists():
        raw = json.loads(AUTHOR_LINKS.read_text(encoding="utf-8"))
        # 키도 정규화해서 저장
        return {normalize_name(k): v for k, v in raw.items()}
    return {}

# def split_authors(author_field: str):
#     parts = [a.strip() for a in (author_field or "").split(" and ") if a.strip()]
#     return parts

# def load_author_links():
#     if AUTHOR_LINKS.exists():
#         return json.loads(AUTHOR_LINKS.read_text(encoding="utf-8"))
#     return {}

def arxiv_url(entry: dict):
    # 표준적인 BibTeX: archivePrefix=arXiv + eprint=XXXX.XXXXX
    eprint = (entry.get("eprint") or "").strip()
    archive = (entry.get("archivePrefix") or entry.get("archiveprefix") or "").strip().lower()
    if eprint and (archive == "arxiv" or "arxiv" in (entry.get("note","").lower())):
        return f"https://arxiv.org/abs/{eprint}"
    # 커스텀 필드 arxiv={2501.01234} 도 허용
    ax = (entry.get("arxiv") or "").strip()
    if ax:
        return f"https://arxiv.org/abs/{ax}"
    return ""
def main():
    if not BIB.exists():
        raise FileNotFoundError(f"Missing: {BIB}")

    author_links = load_author_links()

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

        authors = []
        for name in split_authors(e.get("author", "")):
            authors.append({
                "name": name,
                "url": author_links.get(normalize_name(name), "")
            })

        doi = (e.get("doi") or "").strip()
        url = (e.get("url") or "").strip()
        journal_link = url or (f"https://doi.org/{doi}" if doi else "")

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
