"""Extrage textul PDF-urilor din structura documente_noi/<document_id>/.

Un document gata de procesare are metadata.json si source.pdf in folderul lui.
Folderul _inbox este doar zona de intrare manuala si nu este procesat automat.
"""

import argparse
import json
from pathlib import Path

import fitz  # PyMuPDF

ROOT_PROIECT = Path(__file__).resolve().parent
FOLDER_DOCUMENTE = ROOT_PROIECT / "documente_noi"


def gaseste_documente():
    """Returneaza doar folderele reale de documente, nu folderele auxiliare."""
    for folder in sorted(FOLDER_DOCUMENTE.iterdir()):
        if folder.is_dir() and not folder.name.startswith("_"):
            yield folder


def citeste_metadata(folder_document):
    """Citeste metadata fara a afisa continutul documentului sau secrete."""
    cale_metadata = folder_document / "metadata.json"
    if not cale_metadata.exists():
        raise ValueError("lipseste metadata.json")

    with cale_metadata.open("r", encoding="utf-8-sig") as fisier:
        metadata = json.load(fisier)

    if not metadata.get("document_id"):
        raise ValueError("metadata.json nu contine document_id")
    return metadata


def extrage_text(cale_pdf):
    """Extrage textul tuturor paginilor unui PDF."""
    with fitz.open(cale_pdf) as document:
        pagini = len(document)
        text = "".join(pagina.get_text() + "\n" for pagina in document)
    return text, pagini


def main():
    parser = argparse.ArgumentParser(description="Extrage PDF-urile Omnia in extracted.txt")
    parser.add_argument("--force", action="store_true", help="rescrie extracted.txt daca exista deja")
    args = parser.parse_args()

    procesate = 0
    sarite = 0
    erori = 0

    for folder in gaseste_documente():
        try:
            metadata = citeste_metadata(folder)
            cale_pdf = folder / "source.pdf"
            cale_text = folder / "extracted.txt"

            if not cale_pdf.exists():
                print(f"  SARIT: {metadata['document_id']} — lipseste source.pdf")
                sarite += 1
                continue

            if cale_text.exists() and not args.force:
                print(f"  SARIT: {metadata['document_id']} — extracted.txt exista deja")
                sarite += 1
                continue

            text, pagini = extrage_text(cale_pdf)
            cale_text.write_text(text, encoding="utf-8")
            print(f"  PROCESAT: {metadata['document_id']} — {pagini} pagini, {len(text)} caractere")
            procesate += 1
        except (OSError, ValueError, json.JSONDecodeError) as eroare:
            print(f"  EROARE: {folder.name} — {eroare}")
            erori += 1

    print(f"\nGata. Procesate: {procesate}, sarite: {sarite}, erori: {erori}")


if __name__ == "__main__":
    main()
