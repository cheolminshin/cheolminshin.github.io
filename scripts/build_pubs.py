import json
import re
from pathlib import Path

import bibtexparser


ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "data" / "publications.bib"
OUT = ROOT / "data" / "publications.json"


def clean_text(s: str) -> str:
    """
    Clean common BibTeX/LaTeX-ish artifacts enough for matching/rendering.
    - remove { } used for capitalization protection
    - normalize whitespace (including newlines, NBSP)
    """
    if not s:
        return ""
    s = s.replace("\u00a0", " ")          # NBSP -> normal space
    s = re.sub(r"[{}]", "", s)            # remove braces
    s = " ".join(s.split())               # collapse whitespace/newlines/tabs
    return s.strip()


def split_authors(author_field: str) -> list[str]:
    """
    Robustly split BibTeX author string.
    BibTeX separator is 'and'. People may have newlines or multiple spaces around it.
    Example:
      "Kim, Jaehyun and Shin, Cheolmin and Park, Hyungbin"
      "Kim, Jaehyun\nand Shin, Cheolmin and  Park, Hyungbin"
    """
    s = clean_text(author_field)
    if not s:
        return []
    parts = [p.strip().rstrip(",") for p in re.split(r"\s+and\s+", s) if p.strip()]
    return parts


def to_int_year(year_raw: str) -> int:
    s = clean_text(year_raw)
    if not s:
        return 0
    # Sometimes year can be "2025a" or "{2025}" etc. Try to extract first 4 digits.
    m = re.search(r"\b(\d{4})\b", s)
    if m:
        return int(m.group(1))
    try:
        return int(s)
    except ValueError:
        return 0


def make_arxiv_link(entry: dict) -> str:
    """
    Support common patterns:
      archivePrefix = {arXiv}, eprint = {2501.01234}
      arxiv = {2501.01234}  (custom)
      url already points to arxiv.org (then we just keep url for journal/link and still can output arxiv)
    """
    # Custom field first
    arxiv = clean_text(entry.get("arxiv", ""))
    if arxiv:
        return f"https://arxiv.org/abs/{arxiv}"

    eprint = clean_text(entry.get("eprint", ""))
    archive = clean_text(entry.get("archivePrefix", entry.get("archiveprefix", ""))).lower()

    if eprint and (archive == "arxiv"):
        return f"https://arxiv.org/abs/{eprint}"

    # Sometimes people store arxiv in note
    note = clean_text(entry.get("note", "")).lower()
    if eprint and "arxiv" in note:
        return f"https://arxiv.org/abs/{eprint}"

    return ""


def pick_venue(entry: dict) -> str:
    return clean_text(
        entry.get("journal")
        or entry.get("booktitle")
        or entry.get("publisher")
        or entry.get("institution")
        or ""
    )


def main():
    if not BIB.exists():
        raise FileNotFoundError(f"Missing BibTeX file: {BIB}")

    with BIB.open("r", encoding="utf-8") as f:
        db = bibtexparser.load(f)

    pubs = []
    for e in db.entries:
        title = clean_text(e.get("title", ""))
        authors = split_authors(e.get("author", ""))
        year = to_int_year(e.get("year", ""))
        venue = pick_venue(e)

        doi = clean_text(e.get("doi", ""))
        url = clean_text(e.get("url", ""))

        # Optional custom fields you might add to BibTeX
        pdf = clean_text(e.get("pdf", ""))
        code = clean_text(e.get("code", ""))

        arxiv = make_arxiv_link(e)

        pubs.append({
            "id": e.get("ID", ""),
            "type": e.get("ENTRYTYPE", ""),
            "title": title,
            "authors": authors,    # 형태 A 유지!
            "venue": venue,
            "year": year,

            # Links (형태는 너가 HTML에서 어떻게 쓰든 확장 가능)
            "url": url,            # 저널/공식 페이지 링크로 쓰기 좋음
            "doi": doi,
            "arxiv": arxiv,
            "pdf": pdf,
            "code": code,
        })

    # Sort newest first (year desc, then title)
    pubs.sort(key=lambda x: (x["year"], x["title"]), reverse=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pubs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(pubs)} items)")


if __name__ == "__main__":
    main()
